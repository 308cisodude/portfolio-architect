"""Strict TOML configuration and file-based secret loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import ipaddress
import os
import re
import stat
import tomllib
from typing import Any, Final
from urllib.parse import urlsplit

from .errors import ConfigurationError

MAX_CONFIG_BYTES: Final = 64 * 1024
MAX_SECRET_BYTES: Final = 4096
_SECRET_RE = re.compile(r"^[^\x00-\x1f\x7f]+$")


def _expect_table(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Missing [{name}] table")
    return value


def _string(table: dict[str, Any], key: str, *, default: str | None = None) -> str:
    value = table.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{key} must be a non-empty string")
    cleaned = value.strip()
    if len(cleaned) > 4096 or any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise ConfigurationError(f"{key} is too long or contains control characters")
    return cleaned


def _optional_string(table: dict[str, Any], key: str) -> str | None:
    value = table.get(key)
    if value in (None, ""):
        return None
    return _string(table, key)


def _integer(
    table: dict[str, Any],
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer")
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{key} must be between {minimum} and {maximum}")
    return value


def _boolean(table: dict[str, Any], key: str, *, default: bool) -> bool:
    value = table.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be true or false")
    return value


def _path(table: dict[str, Any], key: str, *, default: str | None = None) -> Path:
    value = _string(table, key, default=default)
    path = Path(value)
    if not path.is_absolute():
        raise ConfigurationError(f"{key} must be an absolute path")
    return path


def _optional_path(table: dict[str, Any], key: str) -> Path | None:
    value = _optional_string(table, key)
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        raise ConfigurationError(f"{key} must be an absolute path")
    return path


@dataclass(frozen=True, slots=True)
class ServerConfig:
    """Local HTTP server configuration."""

    bind: str
    port: int
    api_token_file: Path
    snapshot_file: Path
    max_cached_snapshot_age_seconds: int
    tls_cert_file: Path | None
    tls_key_file: Path | None
    health_endpoint_enabled: bool


@dataclass(frozen=True, slots=True)
class ComdirectConfig:
    """Comdirect client and refresh configuration."""

    base_url: str
    client_id_file: Path
    client_secret_file: Path
    username_file: Path
    password_file: Path
    session_file: Path
    investment_account_file: Path
    investment_cash_policy_file: Path
    poll_interval_seconds: int
    request_timeout_seconds: int
    mfa_timeout_seconds: int
    depot_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    """Complete validated gateway configuration."""

    server: ServerConfig
    comdirect: ComdirectConfig

    @classmethod
    def load(cls, path: Path) -> "GatewayConfig":
        try:
            size = path.stat().st_size
        except OSError as err:
            raise ConfigurationError(f"Cannot access configuration file: {path}") from err
        if size > MAX_CONFIG_BYTES:
            raise ConfigurationError("Configuration file exceeds the 64 KiB limit")
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as err:
            raise ConfigurationError("Configuration file is unreadable or invalid TOML") from err
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise ConfigurationError("schema_version must be integer 1")

        server_raw = _expect_table(raw, "server")
        comdirect_raw = _expect_table(raw, "comdirect")

        bind = _string(server_raw, "bind", default="0.0.0.0")
        _validate_bind_address(bind)
        tls_cert = _optional_path(server_raw, "tls_cert_file")
        tls_key = _optional_path(server_raw, "tls_key_file")
        if (tls_cert is None) != (tls_key is None):
            raise ConfigurationError("tls_cert_file and tls_key_file must be configured together")

        base_url = _validate_comdirect_base_url(
            _string(comdirect_raw, "base_url", default="https://api.comdirect.de")
        )
        depot_ids_raw = comdirect_raw.get("depot_ids", [])
        if not isinstance(depot_ids_raw, list) or len(depot_ids_raw) > 32:
            raise ConfigurationError("depot_ids must be an array with at most 32 items")
        depot_ids: list[str] = []
        for value in depot_ids_raw:
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > 64:
                raise ConfigurationError("Every depot_ids item must be a short non-empty string")
            cleaned = value.strip()
            if any(ord(ch) < 33 or ord(ch) > 126 for ch in cleaned):
                raise ConfigurationError("depot_ids contains an invalid item")
            if cleaned in depot_ids:
                raise ConfigurationError("depot_ids contains a duplicate")
            depot_ids.append(cleaned)

        return cls(
            server=ServerConfig(
                bind=bind,
                port=_integer(server_raw, "port", default=8787, minimum=1, maximum=65535),
                api_token_file=_path(server_raw, "api_token_file"),
                snapshot_file=_path(server_raw, "snapshot_file", default="/data/portfolio.json"),
                max_cached_snapshot_age_seconds=_integer(
                    server_raw,
                    "max_cached_snapshot_age_seconds",
                    default=604800,
                    minimum=0,
                    maximum=2592000,
                ),
                tls_cert_file=tls_cert,
                tls_key_file=tls_key,
                health_endpoint_enabled=_boolean(
                    server_raw, "health_endpoint_enabled", default=True
                ),
            ),
            comdirect=ComdirectConfig(
                base_url=base_url,
                client_id_file=_path(comdirect_raw, "client_id_file"),
                client_secret_file=_path(comdirect_raw, "client_secret_file"),
                username_file=_path(comdirect_raw, "username_file"),
                password_file=_path(comdirect_raw, "password_file"),
                session_file=_path(
                    comdirect_raw, "session_file", default="/data/comdirect-session.json"
                ),
                investment_account_file=_path(
                    comdirect_raw, "investment_account_file", default="/data/investment-account.json"
                ),
                investment_cash_policy_file=_path(
                    comdirect_raw, "investment_cash_policy_file", default="/data/investment-cash-policy.json"
                ),
                poll_interval_seconds=_integer(
                    comdirect_raw,
                    "poll_interval_seconds",
                    default=900,
                    minimum=300,
                    maximum=86400,
                ),
                request_timeout_seconds=_integer(
                    comdirect_raw,
                    "request_timeout_seconds",
                    default=20,
                    minimum=5,
                    maximum=60,
                ),
                mfa_timeout_seconds=_integer(
                    comdirect_raw,
                    "mfa_timeout_seconds",
                    default=180,
                    minimum=30,
                    maximum=600,
                ),
                depot_ids=tuple(depot_ids),
            ),
        )


def _validate_bind_address(value: str) -> None:
    if value in {"localhost", "0.0.0.0", "::"}:
        return
    try:
        ipaddress.ip_address(value)
    except ValueError as err:
        raise ConfigurationError("server.bind must be an IP address, localhost, 0.0.0.0, or ::") from err


def _validate_comdirect_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.comdirect.de"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        raise ConfigurationError(
            "comdirect.base_url must be exactly the HTTPS api.comdirect.de origin"
        )
    path = parsed.path.rstrip("/")
    if path:
        raise ConfigurationError("comdirect.base_url must not contain a path")
    return "https://api.comdirect.de"


def normalise_secret(value: str, *, name: str, minimum: int = 1, maximum: int = 4096) -> str:
    """Validate one in-memory secret without logging or transforming it."""
    if not isinstance(value, str):
        raise ConfigurationError(f"Secret for {name} must be text")
    if not minimum <= len(value) <= maximum or _SECRET_RE.fullmatch(value) is None:
        raise ConfigurationError(f"Secret for {name} has an invalid length or characters")
    return value


def read_secret(path: Path, *, name: str, minimum: int = 1, maximum: int = 4096) -> str:
    """Read one bounded secret and reject group/world-readable regular files."""
    try:
        st = path.stat()
    except OSError as err:
        raise ConfigurationError(f"Cannot access secret file for {name}: {path}") from err
    if st.st_size > MAX_SECRET_BYTES:
        raise ConfigurationError(f"Secret file for {name} is too large")
    if stat.S_ISREG(st.st_mode):
        broad = st.st_mode & (stat.S_IRWXG | stat.S_IRWXO)
        writable = st.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        docker_secret = path.is_relative_to(Path("/run/secrets"))
        if writable or (broad and not docker_secret):
            raise ConfigurationError(
                f"Secret file for {name} has unsafe group or other permissions"
            )
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as err:
        raise ConfigurationError(f"Cannot read secret file for {name}") from err
    if value.endswith("\n"):
        value = value[:-1]
    if value.endswith("\r"):
        value = value[:-1]
    return normalise_secret(value, name=name, minimum=minimum, maximum=maximum)


def validate_runtime_files(config: GatewayConfig, *, bootstrap: bool) -> None:
    """Validate local paths without creating or logging secret material."""
    read_secret(config.server.api_token_file, name="gateway API token", minimum=32, maximum=512)
    read_secret(config.comdirect.client_id_file, name="Comdirect client ID", maximum=512)
    read_secret(config.comdirect.client_secret_file, name="Comdirect client secret", maximum=1024)
    if bootstrap:
        read_secret(config.comdirect.username_file, name="Comdirect username", maximum=256)
        read_secret(config.comdirect.password_file, name="Comdirect password", maximum=512)
    for target in (config.server.snapshot_file, config.comdirect.session_file):
        parent = target.parent
        if not parent.exists() or not parent.is_dir():
            raise ConfigurationError(f"Required data directory does not exist: {parent}")
        if not os.access(parent, os.W_OK):
            raise ConfigurationError(f"Required data directory is not writable: {parent}")
    for optional in (config.server.tls_cert_file, config.server.tls_key_file):
        if optional is not None and not optional.is_file():
            raise ConfigurationError(f"Configured TLS file does not exist: {optional}")
