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
from typing import Any, Final
from urllib.parse import SplitResult, urlsplit, urlunsplit

from aiohttp import (
    ClientError,
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
MAX_RETRY_AFTER_SECONDS: Final = 3600
HEALTH_V2_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=2"
HEALTH_V3_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=3"
HEALTH_V4_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=4"
HEALTH_V5_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=5"
HEALTH_V6_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=6"
SNAPSHOT_SHA256_HEADER: Final = "X-Portfolio-Snapshot-SHA256"
SNAPSHOT_POSITION_COUNT_HEADER: Final = "X-Portfolio-Position-Count"

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


class PortfolioRestAuthenticationError(PortfolioRestError):
    """Raised when the local source rejects its bearer token."""


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

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> RestSourceConfig:
        """Build one strict REST source config from persisted entry data."""
        return cls(
            endpoint_url=normalise_rest_endpoint(raw.get("rest_endpoint_url")),
            api_token=normalise_rest_token(raw.get("rest_api_token")),
        )

    def as_public_dict(self) -> dict[str, Any]:
        """Return diagnostics without exposing authentication material."""
        return {
            "source_provider": "local_rest_json",
            "endpoint": self.endpoint_url,
            "authentication": "bearer",
            "token_configured": True,
            "response_limit_bytes": MAX_REST_RESPONSE_BYTES,
            "request_timeout_seconds": REST_REQUEST_TIMEOUT_SECONDS,
            "snapshot_integrity": "sha256_etag_position_count",
            "requested_health_schema_version": 6,
        }


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
    """Return the fixed health endpoint on the same validated local origin."""
    parsed = urlsplit(endpoint_url)
    return urlunsplit(SplitResult(parsed.scheme, parsed.netloc, "/healthz", "", ""))


async def async_fetch_gateway_health(
    hass: HomeAssistant,
    config: RestSourceConfig,
) -> GatewayHealth:
    """Fetch and validate the bounded authenticated gateway health document."""
    health_url = gateway_health_url(config.endpoint_url)
    resolved_endpoint = await async_validate_local_rest_endpoint(hass, health_url)
    headers = {
        "Accept": ", ".join(
            (
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
            ) as response:
                return await _async_process_health_response(response)
    except PortfolioRestError:
        raise
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
    resolved_endpoint = await async_validate_local_rest_endpoint(
        hass, config.endpoint_url
    )
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
                config.endpoint_url,
                headers=headers,
                allow_redirects=False,
                timeout=ClientTimeout(total=REST_REQUEST_TIMEOUT_SECONDS),
            ) as response:
                return await _async_process_response(response, now=now)
    except PortfolioRestError:
        raise
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
