"""Bounded local REST transport for Portfolio Architect."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import hashlib
import ipaddress
import json
import re
import socket
import ssl
from typing import Any, Final
from urllib.parse import SplitResult, urlsplit, urlunsplit

from aiohttp import (
    ClientConnectorCertificateError,
    ClientConnectorSSLError,
    ClientError,
    ClientSSLError,
    ClientResponse,
    ClientSession,
    ClientTimeout,
    DummyCookieJar,
    TCPConnector,
)
from aiohttp.abc import AbstractResolver, ResolveResult

from homeassistant.core import HomeAssistant

from .engine.rest import RestSnapshot, parse_rest_snapshot

MAX_REST_RESPONSE_BYTES: Final = 1024 * 1024
MAX_REST_HEALTH_RESPONSE_BYTES: Final = 16 * 1024
REST_REQUEST_TIMEOUT_SECONDS: Final = 15
MIN_REST_TOKEN_LENGTH: Final = 16
MAX_REST_TOKEN_LENGTH: Final = 512
MAX_REST_CA_CERTIFICATE_BYTES: Final = 16 * 1024
MAX_RETRY_AFTER_SECONDS: Final = 3600
HEALTH_V2_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=2"
HEALTH_V3_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=3"
HEALTH_V4_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=4"
HEALTH_V5_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=5"
HEALTH_V6_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=6"
HEALTH_V7_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=7"
HEALTH_V8_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=8"
HEALTH_V9_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=9"
HEALTH_V10_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=10"
SNAPSHOT_SHA256_HEADER: Final = "X-Portfolio-Snapshot-SHA256"
SNAPSHOT_POSITION_COUNT_HEADER: Final = "X-Portfolio-Position-Count"
TLS_DISCOVERY_SCHEMA_VERSION: Final = 1
TLS_DISCOVERY_PROFILE_SCHEMA_VERSION: Final = 2
TLS_DISCOVERY_GATEWAY_PATH: Final = "/api/v1/portfolio"
_TLS_DISCOVERY_PROFILE_PATH_RE: Final = re.compile(r"^/api/v1/providers/([a-z][a-z0-9_]{1,31})/portfolio$")
_COMDIRECT_LEGACY_APP_HOST_SUFFIX: Final = "-portfolio-architect-gateway"
_COMDIRECT_CANONICAL_APP_HOST_SUFFIX: Final = "-portfolio-architect-gateway-comdirect"

_TOKEN_RE = re.compile(r"^[\x21-\x7e]+$")
_ALLOWED_IPV4_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16")
)
_ALLOWED_IPV6_NETWORKS = tuple(
    ipaddress.ip_network(value) for value in ("fc00::/7", "fe80::/10", "::1/128")
)


class PortfolioRestError(ValueError):
    """Base error for a REST source."""


class PortfolioRestTlsError(PortfolioRestError):
    """Raised when verified HTTPS transport cannot be established."""


class PortfolioRestAuthenticationError(PortfolioRestError):
    """Raised when the local source rejects its bearer token."""


class PortfolioRestUnavailableError(PortfolioRestError):
    """Raised when a healthy transport reports no currently servable snapshot."""


class PortfolioRestRateLimitError(PortfolioRestError):
    """Raised when the source requests a bounded polling delay."""

    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True, slots=True)
class RestSourceConfig:
    """Validated local REST endpoint configuration."""

    endpoint_url: str
    api_token: str
    tls_ca_certificate: str | None = None

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> RestSourceConfig:
        """Build one strict REST source config from persisted entry data."""
        return cls(
            endpoint_url=normalise_rest_endpoint(raw.get("rest_endpoint_url")),
            api_token=normalise_rest_token(raw.get("rest_api_token")),
            tls_ca_certificate=normalise_rest_ca_certificate(
                raw.get("rest_tls_ca_certificate")
            ),
        )

    def as_public_dict(self) -> dict[str, Any]:
        """Return diagnostics without exposing authentication material."""
        return {
            "source_provider": "local_rest_json",
            "endpoint": self.endpoint_url,
            "authentication": "bearer",
            "transport_security": self.transport_security,
            "custom_ca_configured": self.tls_ca_certificate is not None,
            "tls_ca_sha256": self.tls_ca_sha256,
            "token_configured": True,
            "response_limit_bytes": MAX_REST_RESPONSE_BYTES,
            "request_timeout_seconds": REST_REQUEST_TIMEOUT_SECONDS,
            "snapshot_integrity": "sha256_etag_position_count",
            "requested_health_schema_version": 10,
        }


    @property
    def transport_security(self) -> str:
        return "verified_https" if urlsplit(self.endpoint_url).scheme == "https" else "legacy_http"

    @property
    def tls_ca_sha256(self) -> str | None:
        if self.tls_ca_certificate is None:
            return None
        return _certificate_sha256(self.tls_ca_certificate)


@dataclass(frozen=True, slots=True)
class SupplementalRestSourceConfig:
    """One persisted additional Gateway source with validated provider identity."""

    provider_id: str
    endpoint_url: str
    api_token: str
    tls_ca_certificate: str | None = None

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "SupplementalRestSourceConfig":
        provider_id = raw.get("provider_id")
        if (
            not isinstance(provider_id, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{1,31}", provider_id) is None
        ):
            raise PortfolioRestError("Supplemental Gateway provider ID is invalid")
        transport = RestSourceConfig.from_mapping(raw)
        return cls(
            provider_id=provider_id,
            endpoint_url=transport.endpoint_url,
            api_token=transport.api_token,
            tls_ca_certificate=transport.tls_ca_certificate,
        )

    @property
    def rest_config(self) -> RestSourceConfig:
        return RestSourceConfig(
            endpoint_url=self.endpoint_url,
            api_token=self.api_token,
            tls_ca_certificate=self.tls_ca_certificate,
        )

    def as_storage_dict(self) -> dict[str, str]:
        result = {
            "provider_id": self.provider_id,
            "rest_endpoint_url": self.endpoint_url,
            "rest_api_token": self.api_token,
        }
        if self.tls_ca_certificate is not None:
            result["rest_tls_ca_certificate"] = self.tls_ca_certificate
        return result

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "endpoint": self.endpoint_url,
            "authentication": "bearer",
            "token_configured": True,
            "transport_security": self.rest_config.transport_security,
            "custom_ca_configured": self.tls_ca_certificate is not None,
            "tls_ca_sha256": self.rest_config.tls_ca_sha256,
        }


@dataclass(frozen=True, slots=True)
class GatewayTlsDiscovery:
    """Strict Supervisor-distributed HTTPS trust description for one Gateway."""

    provider_id: str
    provider_name: str | None
    hostname: str
    port: int
    path: str
    ca_certificate: str
    ca_sha256: str

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "GatewayTlsDiscovery":
        schema_version = raw.get("transport_schema_version")
        if schema_version not in {TLS_DISCOVERY_SCHEMA_VERSION, TLS_DISCOVERY_PROFILE_SCHEMA_VERSION}:
            raise PortfolioRestTlsError("Gateway TLS discovery schema is unsupported")
        provider_id = raw.get("provider_id")
        if not isinstance(provider_id, str) or re.fullmatch(r"[a-z][a-z0-9_]{1,31}", provider_id) is None:
            raise PortfolioRestTlsError("Gateway TLS discovery provider ID is invalid")
        hostname = raw.get("host")
        if not isinstance(hostname, str):
            raise PortfolioRestTlsError("Gateway TLS discovery hostname is invalid")
        hostname = hostname.strip().lower().rstrip(".")
        if (
            len(hostname) > 253
            or re.fullmatch(
                r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*",
                hostname,
            )
            is None
        ):
            raise PortfolioRestTlsError("Gateway TLS discovery hostname is invalid")
        port = raw.get("port")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise PortfolioRestTlsError("Gateway TLS discovery port is invalid")
        provider_name: str | None = None
        if schema_version >= TLS_DISCOVERY_PROFILE_SCHEMA_VERSION:
            provider_name_raw = raw.get("provider_name")
            if (
                not isinstance(provider_name_raw, str)
                or not provider_name_raw.strip()
                or len(provider_name_raw.strip()) > 64
                or any(ord(char) < 32 or ord(char) == 127 for char in provider_name_raw)
            ):
                raise PortfolioRestTlsError("Gateway TLS discovery provider name is invalid")
            provider_name = provider_name_raw.strip()
        elif "provider_name" in raw:
            raise PortfolioRestTlsError("Gateway TLS discovery provider name is unexpected")
        path = raw.get("path")
        if schema_version == TLS_DISCOVERY_SCHEMA_VERSION:
            if path != TLS_DISCOVERY_GATEWAY_PATH:
                raise PortfolioRestTlsError("Gateway TLS discovery path is invalid")
        else:
            if not isinstance(path, str):
                raise PortfolioRestTlsError("Gateway TLS discovery path is invalid")
            profile_match = _TLS_DISCOVERY_PROFILE_PATH_RE.fullmatch(path)
            if path != TLS_DISCOVERY_GATEWAY_PATH and (
                profile_match is None or profile_match.group(1) != provider_id
            ):
                raise PortfolioRestTlsError("Gateway TLS discovery path is invalid")
        ca_certificate = normalise_rest_ca_certificate(raw.get("ca_certificate"))
        if ca_certificate is None:
            raise PortfolioRestTlsError("Gateway TLS discovery CA certificate is missing")
        ca_sha256 = raw.get("ca_sha256")
        actual_sha256 = _certificate_sha256(ca_certificate)
        if not isinstance(ca_sha256, str) or not secrets_compare_digest_hex(ca_sha256, actual_sha256):
            raise PortfolioRestTlsError("Gateway TLS discovery CA fingerprint is invalid")
        return cls(provider_id, provider_name, hostname, port, path, ca_certificate, actual_sha256)

    @property
    def endpoint_url(self) -> str:
        return normalise_rest_endpoint(f"https://{self.hostname}:{self.port}{self.path}")

    def matches_legacy_endpoint(self, endpoint_url: str) -> bool:
        """Return true only when discovery changes scheme/trust, not network identity."""
        existing = urlsplit(normalise_rest_endpoint(endpoint_url))
        candidate = urlsplit(self.endpoint_url)
        existing_port = existing.port or (443 if existing.scheme == "https" else 80)
        return (
            _canonical_hostname(existing.hostname or "") == self.hostname
            and existing_port == self.port
            and (existing.path or "/") == self.path
        )

    def matches_comdirect_slug_successor(self, endpoint_url: str) -> bool:
        """Match only the historical -> provider-qualified Comdirect App hostname move."""
        existing = urlsplit(normalise_rest_endpoint(endpoint_url))
        candidate = urlsplit(self.endpoint_url)
        if existing.scheme != "https" or candidate.scheme != "https":
            return False
        existing_host = _canonical_hostname(existing.hostname or "")
        if (
            not existing_host.endswith(_COMDIRECT_LEGACY_APP_HOST_SUFFIX)
            or existing_host.endswith(_COMDIRECT_CANONICAL_APP_HOST_SUFFIX)
        ):
            return False
        expected_host = (
            existing_host[: -len(_COMDIRECT_LEGACY_APP_HOST_SUFFIX)]
            + _COMDIRECT_CANONICAL_APP_HOST_SUFFIX
        )
        existing_port = existing.port or 443
        candidate_port = candidate.port or 443
        return (
            self.provider_id == "comdirect"
            and self.hostname == expected_host
            and existing_port == candidate_port
            and existing_port == self.port
            and (existing.path or "/") == self.path
        )


def secrets_compare_digest_hex(left: str, right: str) -> bool:
    """Compare one bounded lowercase SHA-256 hex value without timing-sensitive equality."""
    import hmac

    if re.fullmatch(r"[0-9a-f]{64}", left) is None:
        return False
    return hmac.compare_digest(left, right)


@dataclass(frozen=True, slots=True)
class RestFetchResult:
    """One REST request result, including validators and integrity metadata."""

    snapshot: RestSnapshot | None
    etag: str | None
    last_modified: str | None
    snapshot_sha256: str | None
    position_count: int | None
    transport_integrity_verified: bool | None


@dataclass(frozen=True, slots=True)
class ResolvedLocalAddress:
    """One validated address returned by the operating-system resolver."""

    family: socket.AddressFamily
    address: str


@dataclass(frozen=True, slots=True)
class ResolvedLocalEndpoint:
    """A local endpoint whose DNS answer is pinned for one HTTP request."""

    hostname: str
    port: int
    addresses: tuple[ResolvedLocalAddress, ...]


class _PinnedLocalResolver(AbstractResolver):
    """Resolve only the prevalidated host and port, without another DNS lookup."""

    def __init__(self, endpoint: ResolvedLocalEndpoint) -> None:
        self._endpoint = endpoint

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_INET,
    ) -> list[ResolveResult]:
        """Return the validated addresses for the exact original origin."""
        if (
            _canonical_hostname(host) != self._endpoint.hostname
            or port != self._endpoint.port
        ):
            raise OSError("Pinned local resolver refused an unexpected host or port")

        addresses = [
            address
            for address in self._endpoint.addresses
            if family in {socket.AF_UNSPEC, address.family}
        ]
        if not addresses:
            raise OSError("Pinned local resolver has no address for the requested family")
        return [
            ResolveResult(
                hostname=host,
                host=address.address,
                port=port,
                family=int(address.family),
                proto=socket.IPPROTO_TCP,
                flags=0,
            )
            for address in addresses
        ]

    async def close(self) -> None:
        """Release resolver resources; this resolver owns none."""


@asynccontextmanager
async def _async_pinned_local_session(
    endpoint: ResolvedLocalEndpoint,
) -> AsyncIterator[ClientSession]:
    """Create one request-scoped session bound to a validated DNS answer.

    A shared Home Assistant session cannot be used here because its connector
    would independently resolve the hostname after the allowlist decision. The
    dedicated connector preserves the original URL for Host/SNI and certificate
    verification while returning only the already validated addresses.
    """
    connector = TCPConnector(
        family=socket.AF_UNSPEC,
        resolver=_PinnedLocalResolver(endpoint),
        use_dns_cache=False,
        force_close=True,
        limit=1,
    )
    async with ClientSession(
        connector=connector,
        connector_owner=True,
        cookie_jar=DummyCookieJar(),
        trust_env=False,
    ) as session:
        yield session


@dataclass(frozen=True, slots=True)
class GatewayAcquisitionMethod:
    """One validated, privacy-safe Gateway acquisition method."""

    method_id: str
    state: str
    active: bool
    can_activate: bool

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.method_id,
            "state": self.state,
            "active": self.active,
            "can_activate": self.can_activate,
        }


@dataclass(frozen=True, slots=True)
class GatewayAcquisitionCapability:
    """One validated, privacy-safe capability authority declaration."""

    capability_id: str
    authoritative_method: str
    supported_methods: tuple[str, ...]
    authority_reason: str
    fallback_policy: str

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.capability_id,
            "authoritative_method": self.authoritative_method,
            "supported_methods": list(self.supported_methods),
            "authority_reason": self.authority_reason,
            "fallback_policy": self.fallback_policy,
        }


@dataclass(frozen=True, slots=True)
class GatewayHealth:
    """Validated, privacy-conscious gateway health state."""

    gateway_version: str
    status: str
    snapshot_available: bool
    snapshot_generated_at: datetime | None
    last_refresh_success: datetime | None
    reauthentication_required: bool
    last_error: str | None
    health_schema_version: int = 1
    snapshot_sha256: str | None = None
    snapshot_position_count: int | None = None
    poll_interval_seconds: int | None = None
    max_cached_snapshot_age_seconds: int | None = None
    operating_mode: str | None = None
    last_refresh_attempt: datetime | None = None
    consecutive_refresh_failures: int | None = None
    snapshot_age_seconds: int | None = None
    snapshot_expires_in_seconds: int | None = None
    refresh_in_progress: bool | None = None
    last_refresh_duration_ms: int | None = None
    last_refresh_trigger: str | None = None
    next_refresh_due_at: datetime | None = None
    manual_refresh_min_interval_seconds: int | None = None
    last_refresh_failure_at: datetime | None = None
    last_refresh_failure_class: str | None = None
    recommended_action: str | None = None
    retry_after_seconds: int | None = None
    provider_id: str | None = None
    provider_name: str | None = None
    acquisition_mode: str | None = None
    active_acquisition_method: str | None = None
    acquisition_methods: tuple[GatewayAcquisitionMethod, ...] = ()
    fallback_policy: str | None = None
    previous_acquisition_method: str | None = None
    last_acquisition_method_change_at: datetime | None = None
    last_acquisition_method_change_reason: str | None = None
    acquisition_capabilities: tuple[GatewayAcquisitionCapability, ...] = ()


def normalise_rest_endpoint(value: Any) -> str:
    """Return one canonical HTTP(S) URL without credentials, query, or fragment."""
    if not isinstance(value, str):
        raise PortfolioRestError("REST endpoint must be a URL")
    cleaned = value.strip()
    if (
        not cleaned
        or len(cleaned) > 512
        or any(ord(char) < 32 or ord(char) == 127 for char in cleaned)
    ):
        raise PortfolioRestError("REST endpoint is empty, too long, or invalid")
    try:
        parsed = urlsplit(cleaned)
        port = parsed.port
    except ValueError as err:
        raise PortfolioRestError("REST endpoint is invalid") from err
    if parsed.scheme.lower() not in {"http", "https"}:
        raise PortfolioRestError("REST endpoint must use HTTP or HTTPS")
    if not parsed.hostname:
        raise PortfolioRestError("REST endpoint must contain a host")
    if parsed.username is not None or parsed.password is not None:
        raise PortfolioRestError("REST endpoint must not contain credentials")
    if parsed.query or parsed.fragment:
        raise PortfolioRestError("REST endpoint must not contain a query or fragment")
    if port is not None and not 1 <= port <= 65535:
        raise PortfolioRestError("REST endpoint port is outside the allowed range")

    host = _canonical_hostname(parsed.hostname)
    if ":" in host:
        host_token = f"[{host}]"
    else:
        host_token = host
    netloc = host_token if port is None else f"{host_token}:{port}"
    path = parsed.path or "/"
    return urlunsplit(
        SplitResult(parsed.scheme.lower(), netloc, path, "", "")
    )


def normalise_rest_token(value: Any) -> str:
    """Validate one opaque bearer token without logging or transforming it."""
    if not isinstance(value, str):
        raise PortfolioRestError("REST API token is required")
    if value != value.strip():
        raise PortfolioRestError("REST API token must not contain surrounding whitespace")
    token = value
    if not MIN_REST_TOKEN_LENGTH <= len(token) <= MAX_REST_TOKEN_LENGTH:
        raise PortfolioRestError("REST API token length is outside the allowed range")
    if _TOKEN_RE.fullmatch(token) is None:
        raise PortfolioRestError("REST API token contains whitespace or control characters")
    return token


def normalise_rest_ca_certificate(value: Any) -> str | None:
    """Validate one public CA certificate without accepting private-key material."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise PortfolioRestError("REST TLS CA certificate must be PEM text")
    if not value or len(value.encode("utf-8")) > MAX_REST_CA_CERTIFICATE_BYTES:
        raise PortfolioRestError("REST TLS CA certificate is empty or too large")
    cleaned = value.strip() + "\n"
    if "PRIVATE KEY" in cleaned or cleaned.count("-----BEGIN CERTIFICATE-----") != 1:
        raise PortfolioRestError("REST TLS CA certificate must contain exactly one certificate")
    try:
        ssl.PEM_cert_to_DER_cert(cleaned)
        context = ssl.create_default_context(cadata=cleaned)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
    except (ValueError, ssl.SSLError) as err:
        raise PortfolioRestError("REST TLS CA certificate is invalid") from err
    return cleaned


def _certificate_sha256(pem: str) -> str:
    try:
        der = ssl.PEM_cert_to_DER_cert(pem)
    except ValueError as err:
        raise PortfolioRestError("REST TLS CA certificate is invalid") from err
    return hashlib.sha256(der).hexdigest()


def _rest_ssl_context(config: RestSourceConfig) -> ssl.SSLContext | None:
    if urlsplit(config.endpoint_url).scheme != "https":
        if config.tls_ca_certificate is not None:
            raise PortfolioRestError("A REST TLS CA certificate cannot be used with HTTP")
        return None
    try:
        if config.tls_ca_certificate is None:
            context = ssl.create_default_context()
        else:
            # Supervisor-discovered Gateway trust is deliberately private-CA-only.
            # Do not combine it with the operating-system public trust store.
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(cadata=config.tls_ca_certificate)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
    except (ValueError, ssl.SSLError) as err:
        raise PortfolioRestTlsError("Verified HTTPS trust configuration is invalid") from err
    return context


async def async_validate_local_rest_endpoint(
    hass: HomeAssistant,
    endpoint_url: str,
) -> ResolvedLocalEndpoint:
    """Resolve, validate, and return the DNS answer used by the request."""
    parsed = urlsplit(endpoint_url)
    host = parsed.hostname
    if host is None:
        raise PortfolioRestError("REST endpoint must contain a host")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addresses = await hass.async_add_executor_job(_resolve_host, host, port)
    if not addresses:
        raise PortfolioRestError("REST endpoint host could not be resolved")
    if any(not _is_allowed_local_address(address.address) for address in addresses):
        raise PortfolioRestError(
            "REST endpoint must resolve exclusively to loopback, link-local, or private addresses"
        )
    return ResolvedLocalEndpoint(
        hostname=_canonical_hostname(host),
        port=port,
        addresses=addresses,
    )


def gateway_health_url(endpoint_url: str) -> str:
    """Return the health endpoint corresponding to one validated portfolio path."""
    parsed = urlsplit(endpoint_url)
    match = _TLS_DISCOVERY_PROFILE_PATH_RE.fullmatch(parsed.path or "")
    path = (
        f"/api/v1/providers/{match.group(1)}/healthz"
        if match is not None
        else "/healthz"
    )
    return urlunsplit(SplitResult(parsed.scheme, parsed.netloc, path, "", ""))


async def async_fetch_gateway_health(
    hass: HomeAssistant,
    config: RestSourceConfig,
) -> GatewayHealth:
    """Fetch and validate the bounded authenticated gateway health document."""
    health_url = gateway_health_url(config.endpoint_url)
    resolved_endpoint = await async_validate_local_rest_endpoint(hass, health_url)
    ssl_context = await hass.async_add_executor_job(_rest_ssl_context, config)
    headers = {
        "Accept": ", ".join(
            (
                HEALTH_V10_MEDIA_TYPE,
                HEALTH_V9_MEDIA_TYPE,
                HEALTH_V8_MEDIA_TYPE,
                HEALTH_V7_MEDIA_TYPE,
                HEALTH_V6_MEDIA_TYPE,
                HEALTH_V5_MEDIA_TYPE,
                HEALTH_V4_MEDIA_TYPE,
                HEALTH_V3_MEDIA_TYPE,
                HEALTH_V2_MEDIA_TYPE,
                "application/json",
            )
        ),
        "Authorization": f"Bearer {config.api_token}",
    }
    try:
        async with _async_pinned_local_session(resolved_endpoint) as session:
            async with session.get(
                health_url,
                headers=headers,
                allow_redirects=False,
                timeout=ClientTimeout(total=REST_REQUEST_TIMEOUT_SECONDS),
                ssl=ssl_context,
            ) as response:
                return await _async_process_health_response(response)
    except PortfolioRestError:
        raise
    except (ClientConnectorCertificateError, ClientConnectorSSLError, ClientSSLError, ssl.SSLError) as err:
        raise PortfolioRestTlsError("Local gateway HTTPS certificate verification failed") from err
    except (ClientError, asyncio.TimeoutError) as err:
        raise PortfolioRestError("Local gateway health endpoint could not be reached") from err


async def _async_process_health_response(response: ClientResponse) -> GatewayHealth:
    if response.status in {401, 403}:
        raise PortfolioRestAuthenticationError(
            "Local REST source rejected the bearer token"
        )
    if response.status != 200:
        raise PortfolioRestError(
            f"Local gateway health endpoint returned HTTP status {response.status}"
        )
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json" and not content_type.endswith("+json"):
        raise PortfolioRestError("Local gateway health endpoint must return application/json")
    content_length = response.content_length
    if content_length is not None and content_length > MAX_REST_HEALTH_RESPONSE_BYTES:
        raise PortfolioRestError("Local gateway health response exceeds the 16 KiB limit")
    body = bytearray()
    async for chunk in response.content.iter_chunked(4096):
        body.extend(chunk)
        if len(body) > MAX_REST_HEALTH_RESPONSE_BYTES:
            raise PortfolioRestError("Local gateway health response exceeds the 16 KiB limit")
    try:
        payload = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_json_object_without_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as err:
        raise PortfolioRestError(
            "Local gateway health endpoint returned invalid or duplicate-key UTF-8 JSON"
        ) from err
    return _parse_gateway_health(payload)


def _parse_gateway_health(payload: Any) -> GatewayHealth:
    if not isinstance(payload, dict):
        raise PortfolioRestError("Local gateway health document must be an object")
    base_fields = {
        "gateway_version",
        "status",
        "snapshot_available",
        "snapshot_generated_at",
        "last_refresh_success",
        "reauthentication_required",
        "last_error",
    }
    v2_fields = base_fields | {
        "health_schema_version",
        "snapshot_sha256",
        "snapshot_position_count",
        "poll_interval_seconds",
        "max_cached_snapshot_age_seconds",
    }
    v3_fields = v2_fields | {
        "operating_mode",
        "last_refresh_attempt",
        "consecutive_refresh_failures",
        "snapshot_age_seconds",
        "snapshot_expires_in_seconds",
    }
    v4_fields = v3_fields | {
        "refresh_in_progress",
        "last_refresh_duration_ms",
        "last_refresh_trigger",
        "next_refresh_due_at",
        "manual_refresh_min_interval_seconds",
    }
    v5_fields = v4_fields | {
        "last_refresh_failure_at",
        "last_refresh_failure_class",
        "recommended_action",
        "retry_after_seconds",
    }
    v6_fields = v5_fields | {"provider_id"}
    v7_fields = v6_fields | {"acquisition_mode"}
    v8_fields = v7_fields | {
        "active_acquisition_method",
        "acquisition_methods",
        "fallback_policy",
        "previous_acquisition_method",
        "last_acquisition_method_change_at",
        "last_acquisition_method_change_reason",
    }
    v9_fields = v8_fields | {"acquisition_capabilities"}
    v10_fields = v9_fields | {"provider_name"}
    keys = set(payload)
    if keys == base_fields:
        health_schema_version = 1
    elif keys == v2_fields and payload.get("health_schema_version") == 2:
        health_schema_version = 2
    elif keys == v3_fields and payload.get("health_schema_version") == 3:
        health_schema_version = 3
    elif keys == v4_fields and payload.get("health_schema_version") == 4:
        health_schema_version = 4
    elif keys == v5_fields and payload.get("health_schema_version") == 5:
        health_schema_version = 5
    elif keys == v6_fields and payload.get("health_schema_version") == 6:
        health_schema_version = 6
    elif keys == v7_fields and payload.get("health_schema_version") == 7:
        health_schema_version = 7
    elif keys == v8_fields and payload.get("health_schema_version") == 8:
        health_schema_version = 8
    elif keys == v9_fields and payload.get("health_schema_version") == 9:
        health_schema_version = 9
    elif keys == v10_fields and payload.get("health_schema_version") == 10:
        health_schema_version = 10
    else:
        raise PortfolioRestError("Local gateway health document has an unexpected schema")

    version = payload["gateway_version"]
    if not isinstance(version, str) or re.fullmatch(r"[0-9A-Za-z.+-]{1,32}", version) is None:
        raise PortfolioRestError("Local gateway health version is invalid")
    status = payload["status"]
    if status not in {"ok", "degraded"}:
        raise PortfolioRestError("Local gateway health status is invalid")
    snapshot_available = payload["snapshot_available"]
    reauth = payload["reauthentication_required"]
    if not isinstance(snapshot_available, bool) or not isinstance(reauth, bool):
        raise PortfolioRestError("Local gateway health booleans are invalid")
    last_error = payload["last_error"]
    if last_error is not None and (
        not isinstance(last_error, str)
        or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", last_error) is None
    ):
        raise PortfolioRestError("Local gateway health error code is invalid")

    snapshot_sha256 = None
    snapshot_position_count = None
    poll_interval_seconds = None
    max_cached_snapshot_age_seconds = None
    operating_mode = None
    last_refresh_attempt = None
    consecutive_refresh_failures = None
    snapshot_age_seconds = None
    snapshot_expires_in_seconds = None
    refresh_in_progress = None
    last_refresh_duration_ms = None
    last_refresh_trigger = None
    next_refresh_due_at = None
    manual_refresh_min_interval_seconds = None
    last_refresh_failure_at = None
    last_refresh_failure_class = None
    recommended_action = None
    retry_after_seconds = None
    provider_id = None
    provider_name = None
    acquisition_mode = None
    active_acquisition_method = None
    acquisition_methods: tuple[GatewayAcquisitionMethod, ...] = ()
    acquisition_capabilities: tuple[GatewayAcquisitionCapability, ...] = ()
    fallback_policy = None
    previous_acquisition_method = None
    last_acquisition_method_change_at = None
    last_acquisition_method_change_reason = None
    if health_schema_version >= 2:
        snapshot_sha256 = _parse_optional_sha256(
            payload["snapshot_sha256"], "snapshot_sha256"
        )
        snapshot_position_count = _parse_optional_bounded_int(
            payload["snapshot_position_count"],
            field="snapshot_position_count",
            minimum=0,
            maximum=512,
        )
        poll_interval_seconds = _parse_optional_bounded_int(
            payload["poll_interval_seconds"],
            field="poll_interval_seconds",
            minimum=300,
            maximum=86400,
        )
        max_cached_snapshot_age_seconds = _parse_optional_bounded_int(
            payload["max_cached_snapshot_age_seconds"],
            field="max_cached_snapshot_age_seconds",
            minimum=0,
            maximum=2592000,
        )
        if snapshot_available and (
            snapshot_sha256 is None or snapshot_position_count is None
        ):
            raise PortfolioRestError(
                "Available gateway snapshot lacks integrity metadata"
            )
        if not snapshot_available and (
            snapshot_sha256 is not None or snapshot_position_count is not None
        ):
            raise PortfolioRestError(
                "Unavailable gateway snapshot must not expose integrity metadata"
            )

    if health_schema_version >= 3:
        operating_mode = payload["operating_mode"]
        if operating_mode not in {
            "live",
            "last_known_good",
            "reauthentication_required",
            "unavailable",
        }:
            raise PortfolioRestError("Local gateway operating mode is invalid")
        last_refresh_attempt = _parse_optional_health_timestamp(
            payload["last_refresh_attempt"], "last_refresh_attempt"
        )
        consecutive_refresh_failures = _parse_optional_bounded_int(
            payload["consecutive_refresh_failures"],
            field="consecutive_refresh_failures",
            minimum=0,
            maximum=1000000,
        )
        if consecutive_refresh_failures is None:
            raise PortfolioRestError(
                "Local gateway consecutive refresh failure count is missing"
            )
        snapshot_age_seconds = _parse_optional_bounded_int(
            payload["snapshot_age_seconds"],
            field="snapshot_age_seconds",
            minimum=0,
            maximum=315360000,
        )
        snapshot_expires_in_seconds = _parse_optional_bounded_int(
            payload["snapshot_expires_in_seconds"],
            field="snapshot_expires_in_seconds",
            minimum=0,
            maximum=2592000,
        )
        if snapshot_available and snapshot_age_seconds is None:
            raise PortfolioRestError("Available gateway snapshot lacks age metadata")
        if not snapshot_available and (
            snapshot_age_seconds is not None
            or snapshot_expires_in_seconds is not None
            or payload["snapshot_generated_at"] is not None
        ):
            raise PortfolioRestError(
                "Unavailable gateway snapshot age metadata is inconsistent"
            )
        if operating_mode == "live" and (
            status != "ok"
            or reauth
            or not snapshot_available
            or consecutive_refresh_failures != 0
        ):
            raise PortfolioRestError("Live gateway operating mode is inconsistent")
        if operating_mode == "last_known_good" and (
            status != "degraded" or reauth or not snapshot_available
        ):
            raise PortfolioRestError("Last-known-good gateway mode is inconsistent")
        if operating_mode == "reauthentication_required" and (
            status != "degraded" or not reauth
        ):
            raise PortfolioRestError("Gateway reauthentication mode is inconsistent")
        if operating_mode == "unavailable" and (
            status != "degraded" or snapshot_available
        ):
            raise PortfolioRestError("Unavailable gateway mode is inconsistent")

    if health_schema_version >= 4:
        refresh_in_progress = payload["refresh_in_progress"]
        if not isinstance(refresh_in_progress, bool):
            raise PortfolioRestError("Local gateway refresh state is invalid")
        last_refresh_duration_ms = _parse_optional_bounded_int(
            payload["last_refresh_duration_ms"],
            field="last_refresh_duration_ms",
            minimum=0,
            maximum=600000,
        )
        last_refresh_trigger = payload["last_refresh_trigger"]
        if last_refresh_trigger is not None and last_refresh_trigger not in {
            "startup",
            "scheduled",
            "manual",
            "bootstrap",
        }:
            raise PortfolioRestError("Local gateway refresh trigger is invalid")
        next_refresh_due_at = _parse_optional_health_timestamp(
            payload["next_refresh_due_at"], "next_refresh_due_at"
        )
        manual_refresh_min_interval_seconds = _parse_optional_bounded_int(
            payload["manual_refresh_min_interval_seconds"],
            field="manual_refresh_min_interval_seconds",
            minimum=30,
            maximum=3600,
        )
        if manual_refresh_min_interval_seconds is None:
            raise PortfolioRestError(
                "Local gateway manual refresh interval is missing"
            )
        if last_refresh_attempt is None and (
            refresh_in_progress
            or last_refresh_duration_ms is not None
            or last_refresh_trigger is not None
        ):
            raise PortfolioRestError("Local gateway refresh telemetry is inconsistent")
        if last_refresh_attempt is not None and last_refresh_trigger is None:
            raise PortfolioRestError("Local gateway refresh trigger is missing")
        if (
            last_refresh_attempt is not None
            and not refresh_in_progress
            and last_refresh_duration_ms is None
        ):
            raise PortfolioRestError("Local gateway refresh duration is missing")

    if health_schema_version >= 5:
        last_refresh_failure_at = _parse_optional_health_timestamp(
            payload["last_refresh_failure_at"], "last_refresh_failure_at"
        )
        last_refresh_failure_class = payload["last_refresh_failure_class"]
        if last_refresh_failure_class is not None and last_refresh_failure_class not in {
            "reauthentication_required",
            "authentication_error",
            "rate_limited",
            "remote_service_error",
            "remote_api_error",
            "transport_error",
            "invalid_response",
            "configuration_error",
            "gateway_error",
            "internal_error",
        }:
            raise PortfolioRestError("Local gateway refresh failure class is invalid")
        recommended_action = payload["recommended_action"]
        if recommended_action not in {
            "none",
            "reauthenticate",
            "wait",
            "check_connectivity",
            "inspect_logs",
            "fix_configuration",
        }:
            raise PortfolioRestError("Local gateway recommended action is invalid")
        retry_after_seconds = _parse_optional_bounded_int(
            payload["retry_after_seconds"],
            field="retry_after_seconds",
            minimum=0,
            maximum=86400,
        )
        if consecutive_refresh_failures == 0:
            if (
                last_refresh_failure_at is not None
                or last_refresh_failure_class is not None
                or recommended_action != "none"
                or retry_after_seconds is not None
            ):
                raise PortfolioRestError(
                    "Successful gateway refresh state retains failure diagnostics"
                )
        else:
            if (
                last_refresh_failure_at is None
                or last_refresh_failure_class is None
                or recommended_action in {None, "none"}
            ):
                raise PortfolioRestError(
                    "Failed gateway refresh state lacks recovery diagnostics"
                )
        if reauth and (
            last_refresh_failure_class != "reauthentication_required"
            or recommended_action != "reauthenticate"
        ):
            raise PortfolioRestError(
                "Gateway reauthentication diagnostics are inconsistent"
            )

    if health_schema_version >= 6:
        provider_id = payload["provider_id"]
        if (
            not isinstance(provider_id, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{1,31}", provider_id) is None
        ):
            raise PortfolioRestError("Local gateway provider ID is invalid")
    if health_schema_version >= 7:
        acquisition_mode = payload["acquisition_mode"]
        if (
            not isinstance(acquisition_mode, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{1,31}", acquisition_mode) is None
        ):
            raise PortfolioRestError("Local gateway acquisition mode is invalid")

    if health_schema_version >= 8:
        active_acquisition_method = payload["active_acquisition_method"]
        if (
            not isinstance(active_acquisition_method, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{1,31}", active_acquisition_method) is None
            or active_acquisition_method != acquisition_mode
        ):
            raise PortfolioRestError("Local gateway active acquisition method is invalid")
        raw_methods = payload["acquisition_methods"]
        if not isinstance(raw_methods, list) or not 1 <= len(raw_methods) <= 8:
            raise PortfolioRestError("Local gateway acquisition method inventory is invalid")
        parsed_methods: list[GatewayAcquisitionMethod] = []
        method_ids: set[str] = set()
        active_count = 0
        for raw_method in raw_methods:
            if not isinstance(raw_method, dict) or set(raw_method) != {
                "id", "state", "active", "can_activate"
            }:
                raise PortfolioRestError("Local gateway acquisition method entry is invalid")
            method_id = raw_method["id"]
            state = raw_method["state"]
            active = raw_method["active"]
            can_activate = raw_method["can_activate"]
            if (
                not isinstance(method_id, str)
                or re.fullmatch(r"[a-z][a-z0-9_]{1,31}", method_id) is None
                or method_id in method_ids
            ):
                raise PortfolioRestError("Local gateway acquisition method ID is invalid")
            if state not in {"ready", "not_ready", "unavailable", "research_only"}:
                raise PortfolioRestError("Local gateway acquisition method state is invalid")
            if not isinstance(active, bool) or not isinstance(can_activate, bool):
                raise PortfolioRestError("Local gateway acquisition method flags are invalid")
            if can_activate and state != "ready":
                raise PortfolioRestError("Non-ready gateway acquisition method is activatable")
            if active:
                active_count += 1
                if method_id != active_acquisition_method or state != "ready":
                    raise PortfolioRestError("Local gateway active acquisition method is inconsistent")
            method_ids.add(method_id)
            parsed_methods.append(GatewayAcquisitionMethod(method_id, state, active, can_activate))
        if active_count != 1 or active_acquisition_method not in method_ids:
            raise PortfolioRestError("Local gateway acquisition method inventory lacks one active method")
        acquisition_methods = tuple(parsed_methods)
        fallback_policy = payload["fallback_policy"]
        if fallback_policy != "none":
            raise PortfolioRestError("Local gateway acquisition fallback policy is invalid")
        previous_acquisition_method = payload["previous_acquisition_method"]
        last_acquisition_method_change_at = _parse_optional_health_timestamp(
            payload["last_acquisition_method_change_at"],
            "last_acquisition_method_change_at",
        )
        last_acquisition_method_change_reason = payload[
            "last_acquisition_method_change_reason"
        ]
        history = (
            previous_acquisition_method,
            last_acquisition_method_change_at,
            last_acquisition_method_change_reason,
        )
        if any(value is not None for value in history):
            if any(value is None for value in history):
                raise PortfolioRestError("Local gateway acquisition method history is incomplete")
            if (
                not isinstance(previous_acquisition_method, str)
                or previous_acquisition_method not in method_ids
                or previous_acquisition_method == active_acquisition_method
                or last_acquisition_method_change_reason != "operator"
            ):
                raise PortfolioRestError("Local gateway acquisition method history is invalid")

    if health_schema_version >= 9:
        raw_capabilities = payload["acquisition_capabilities"]
        if not isinstance(raw_capabilities, list) or not 1 <= len(raw_capabilities) <= 8:
            raise PortfolioRestError("Local gateway acquisition capability inventory is invalid")
        parsed_capabilities: list[GatewayAcquisitionCapability] = []
        capability_ids: set[str] = set()
        method_state = {item.method_id: item.state for item in acquisition_methods}
        for raw_capability in raw_capabilities:
            if not isinstance(raw_capability, dict) or set(raw_capability) != {
                "id",
                "authoritative_method",
                "supported_methods",
                "authority_reason",
                "fallback_policy",
            }:
                raise PortfolioRestError("Local gateway acquisition capability entry is invalid")
            capability_id = raw_capability["id"]
            authoritative_method = raw_capability["authoritative_method"]
            supported_methods = raw_capability["supported_methods"]
            authority_reason = raw_capability["authority_reason"]
            capability_fallback_policy = raw_capability["fallback_policy"]
            if (
                not isinstance(capability_id, str)
                or re.fullmatch(r"[a-z][a-z0-9_]{1,31}", capability_id) is None
                or capability_id in capability_ids
            ):
                raise PortfolioRestError("Local gateway acquisition capability ID is invalid")
            if (
                not isinstance(authoritative_method, str)
                or authoritative_method not in method_ids
                or method_state.get(authoritative_method) != "ready"
            ):
                raise PortfolioRestError("Local gateway capability authority is invalid")
            if (
                not isinstance(supported_methods, list)
                or not 1 <= len(supported_methods) <= 8
                or any(not isinstance(item, str) or item not in method_ids for item in supported_methods)
                or len(set(supported_methods)) != len(supported_methods)
                or authoritative_method not in supported_methods
            ):
                raise PortfolioRestError("Local gateway capability methods are invalid")
            if authority_reason not in {"active_method", "provider_fixed", "supplemental"}:
                raise PortfolioRestError("Local gateway capability authority reason is invalid")
            if authority_reason == "active_method" and authoritative_method != active_acquisition_method:
                raise PortfolioRestError("Local gateway active-method capability authority is inconsistent")
            if authority_reason == "supplemental" and authoritative_method == active_acquisition_method:
                raise PortfolioRestError("Local gateway supplemental capability authority is inconsistent")
            if capability_fallback_policy != "none":
                raise PortfolioRestError("Local gateway capability fallback policy is invalid")
            capability_ids.add(capability_id)
            parsed_capabilities.append(
                GatewayAcquisitionCapability(
                    capability_id=capability_id,
                    authoritative_method=authoritative_method,
                    supported_methods=tuple(supported_methods),
                    authority_reason=authority_reason,
                    fallback_policy=capability_fallback_policy,
                )
            )
        if "holdings" not in capability_ids:
            raise PortfolioRestError("Local gateway acquisition capabilities lack holdings authority")
        acquisition_capabilities = tuple(parsed_capabilities)

    if health_schema_version >= 10:
        provider_name = payload["provider_name"]
        if (
            not isinstance(provider_name, str)
            or not provider_name.strip()
            or len(provider_name.strip()) > 64
            or provider_name != provider_name.strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in provider_name)
        ):
            raise PortfolioRestError("Local gateway provider name is invalid")

    return GatewayHealth(
        gateway_version=version,
        status=status,
        snapshot_available=snapshot_available,
        snapshot_generated_at=_parse_optional_health_timestamp(
            payload["snapshot_generated_at"], "snapshot_generated_at"
        ),
        last_refresh_success=_parse_optional_health_timestamp(
            payload["last_refresh_success"], "last_refresh_success"
        ),
        reauthentication_required=reauth,
        last_error=last_error,
        health_schema_version=health_schema_version,
        snapshot_sha256=snapshot_sha256,
        snapshot_position_count=snapshot_position_count,
        poll_interval_seconds=poll_interval_seconds,
        max_cached_snapshot_age_seconds=max_cached_snapshot_age_seconds,
        operating_mode=operating_mode,
        last_refresh_attempt=last_refresh_attempt,
        consecutive_refresh_failures=consecutive_refresh_failures,
        snapshot_age_seconds=snapshot_age_seconds,
        snapshot_expires_in_seconds=snapshot_expires_in_seconds,
        refresh_in_progress=refresh_in_progress,
        last_refresh_duration_ms=last_refresh_duration_ms,
        last_refresh_trigger=last_refresh_trigger,
        next_refresh_due_at=next_refresh_due_at,
        manual_refresh_min_interval_seconds=(
            manual_refresh_min_interval_seconds
        ),
        last_refresh_failure_at=last_refresh_failure_at,
        last_refresh_failure_class=last_refresh_failure_class,
        recommended_action=recommended_action,
        retry_after_seconds=retry_after_seconds,
        provider_id=provider_id,
        provider_name=provider_name,
        acquisition_mode=acquisition_mode,
        active_acquisition_method=active_acquisition_method,
        acquisition_methods=acquisition_methods,
        fallback_policy=fallback_policy,
        previous_acquisition_method=previous_acquisition_method,
        last_acquisition_method_change_at=last_acquisition_method_change_at,
        last_acquisition_method_change_reason=last_acquisition_method_change_reason,
        acquisition_capabilities=acquisition_capabilities,
    )


def _parse_optional_sha256(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise PortfolioRestError(f"Local gateway health {field} is invalid")
    return value


def _parse_optional_bounded_int(
    value: Any, *, field: str, minimum: int, maximum: int
) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise PortfolioRestError(f"Local gateway health {field} is invalid")
    if not minimum <= value <= maximum:
        raise PortfolioRestError(f"Local gateway health {field} is invalid")
    return value

def _parse_optional_health_timestamp(value: Any, field: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        raise PortfolioRestError(f"Local gateway health {field} is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as err:
        raise PortfolioRestError(f"Local gateway health {field} is invalid") from err
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PortfolioRestError(f"Local gateway health {field} must include a timezone")
    return parsed


async def async_fetch_rest_snapshot(
    hass: HomeAssistant,
    config: RestSourceConfig,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    now: datetime | None = None,
) -> RestFetchResult:
    """Fetch and validate one bounded local REST snapshot."""
    return await _async_fetch_snapshot_url(
        hass,
        config,
        config.endpoint_url,
        etag=etag,
        last_modified=last_modified,
        now=now,
    )


async def _async_fetch_snapshot_url(
    hass: HomeAssistant,
    config: RestSourceConfig,
    snapshot_url: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    now: datetime | None = None,
) -> RestFetchResult:
    """Fetch one bounded snapshot from a fixed validated path on the configured origin."""
    resolved_endpoint = await async_validate_local_rest_endpoint(hass, snapshot_url)
    ssl_context = await hass.async_add_executor_job(_rest_ssl_context, config)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {config.api_token}",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    try:
        async with _async_pinned_local_session(resolved_endpoint) as session:
            async with session.get(
                snapshot_url,
                headers=headers,
                allow_redirects=False,
                timeout=ClientTimeout(total=REST_REQUEST_TIMEOUT_SECONDS),
                ssl=ssl_context,
            ) as response:
                return await _async_process_response(response, now=now)
    except PortfolioRestError:
        raise
    except (ClientConnectorCertificateError, ClientConnectorSSLError, ClientSSLError, ssl.SSLError) as err:
        raise PortfolioRestTlsError("Local gateway HTTPS certificate verification failed") from err
    except (ClientError, asyncio.TimeoutError) as err:
        raise PortfolioRestError("Local REST source could not be reached") from err


async def _async_process_response(
    response: ClientResponse,
    *,
    now: datetime | None,
) -> RestFetchResult:
    etag = _bounded_header(response.headers.get("ETag"), maximum=256)
    last_modified = _bounded_header(
        response.headers.get("Last-Modified"), maximum=128
    )
    if response.status == 304:
        snapshot_sha256, position_count = _parse_snapshot_integrity_headers(
            response, etag=etag
        )
        return RestFetchResult(
            snapshot=None,
            etag=etag,
            last_modified=last_modified,
            snapshot_sha256=snapshot_sha256,
            position_count=position_count,
            transport_integrity_verified=(
                True if snapshot_sha256 is not None else None
            ),
        )
    if response.status in {401, 403}:
        raise PortfolioRestAuthenticationError(
            "Local REST source rejected the bearer token"
        )
    if response.status == 429:
        raise PortfolioRestRateLimitError(
            "Local REST source requested a slower polling rate",
            retry_after=_parse_retry_after(response.headers.get("Retry-After")),
        )
    if response.status == 503:
        raise PortfolioRestUnavailableError(
            "Local REST source has no currently servable snapshot"
        )
    if response.status != 200:
        raise PortfolioRestError(
            f"Local REST source returned HTTP status {response.status}"
        )

    snapshot_sha256, position_count = _parse_snapshot_integrity_headers(
        response, etag=etag
    )
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json" and not content_type.endswith("+json"):
        raise PortfolioRestError("Local REST source must return application/json")
    content_length = response.content_length
    if content_length is not None and content_length > MAX_REST_RESPONSE_BYTES:
        raise PortfolioRestError("Local REST source response exceeds the 1 MiB limit")

    body = bytearray()
    async for chunk in response.content.iter_chunked(64 * 1024):
        body.extend(chunk)
        if len(body) > MAX_REST_RESPONSE_BYTES:
            raise PortfolioRestError("Local REST source response exceeds the 1 MiB limit")
    try:
        payload = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_json_object_without_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as err:
        raise PortfolioRestError(
            "Local REST source returned invalid or duplicate-key UTF-8 JSON"
        ) from err
    try:
        snapshot = parse_rest_snapshot(payload, now=now)
    except ValueError as err:
        raise PortfolioRestError(str(err)) from err

    verified = None
    if snapshot_sha256 is not None:
        actual_sha256 = hashlib.sha256(body).hexdigest()
        if actual_sha256 != snapshot_sha256:
            raise PortfolioRestError(
                "Local REST snapshot SHA-256 header does not match the response body"
            )
        if position_count != len(snapshot.positions):
            raise PortfolioRestError(
                "Local REST snapshot position-count header does not match the response body"
            )
        verified = True

    return RestFetchResult(
        snapshot=snapshot,
        etag=etag,
        last_modified=last_modified,
        snapshot_sha256=snapshot_sha256,
        position_count=position_count,
        transport_integrity_verified=verified,
    )


def _parse_snapshot_integrity_headers(
    response: ClientResponse, *, etag: str | None
) -> tuple[str | None, int | None]:
    digest_raw = response.headers.get(SNAPSHOT_SHA256_HEADER)
    count_raw = response.headers.get(SNAPSHOT_POSITION_COUNT_HEADER)
    if digest_raw is None and count_raw is None:
        return None, None
    if digest_raw is None or count_raw is None:
        raise PortfolioRestError(
            "Local REST source returned incomplete snapshot integrity headers"
        )
    digest = digest_raw.strip()
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise PortfolioRestError("Local REST snapshot SHA-256 header is invalid")
    if not count_raw.isdigit():
        raise PortfolioRestError("Local REST snapshot position-count header is invalid")
    count = int(count_raw)
    if not 0 <= count <= 512:
        raise PortfolioRestError("Local REST snapshot position-count header is invalid")
    if etag is not None and etag != f'"sha256-{digest}"':
        raise PortfolioRestError(
            "Local REST snapshot ETag does not match the SHA-256 header"
        )
    return digest, count


def _json_object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    """Build one JSON object while rejecting ambiguous duplicate keys."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_hostname(value: str) -> str:
    """Return the ASCII comparison form used by the pinned resolver."""
    try:
        return value.rstrip(".").encode("idna").decode("ascii").casefold()
    except UnicodeError as err:
        raise PortfolioRestError("REST endpoint host is invalid") from err


def _resolve_host(host: str, port: int) -> tuple[ResolvedLocalAddress, ...]:
    try:
        records = socket.getaddrinfo(
            host,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as err:
        raise PortfolioRestError("REST endpoint host could not be resolved") from err

    resolved: set[tuple[socket.AddressFamily, str]] = set()
    for family_raw, _type, _proto, _canonname, sockaddr in records:
        try:
            family = socket.AddressFamily(family_raw)
        except ValueError:
            continue
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        address = str(sockaddr[0])
        if (
            family == socket.AF_INET6
            and len(sockaddr) >= 4
            and sockaddr[3]
            and "%" not in address
        ):
            address = f"{address}%{sockaddr[3]}"
        resolved.add((family, address))
    return tuple(
        ResolvedLocalAddress(family=family, address=address)
        for family, address in sorted(resolved, key=lambda item: (int(item[0]), item[1]))
    )


def _is_allowed_local_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    networks = (
        _ALLOWED_IPV4_NETWORKS
        if isinstance(address, ipaddress.IPv4Address)
        else _ALLOWED_IPV6_NETWORKS
    )
    return any(address in network for network in networks)


def _parse_retry_after(value: str | None) -> int | None:
    if value is None or not value.isdigit():
        return None
    parsed = int(value)
    if parsed <= 0:
        return None
    return min(parsed, MAX_RETRY_AFTER_SECONDS)


def _bounded_header(value: str | None, *, maximum: int) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if (
        not cleaned
        or len(cleaned) > maximum
        or any(ord(char) < 32 or ord(char) == 127 for char in cleaned)
    ):
        return None
    return cleaned


__all__ = [
    "MAX_REST_HEALTH_RESPONSE_BYTES",
    "MAX_REST_RESPONSE_BYTES",
    "PortfolioRestAuthenticationError",
    "PortfolioRestError",
    "PortfolioRestRateLimitError",
    "GatewayHealth",
    "HEALTH_V3_MEDIA_TYPE",
    "HEALTH_V4_MEDIA_TYPE",
    "ResolvedLocalAddress",
    "ResolvedLocalEndpoint",
    "RestFetchResult",
    "RestSourceConfig",
    "async_fetch_gateway_health",
    "async_fetch_rest_snapshot",
    "gateway_health_url",
    "async_validate_local_rest_endpoint",
    "normalise_rest_endpoint",
    "normalise_rest_token",
]
