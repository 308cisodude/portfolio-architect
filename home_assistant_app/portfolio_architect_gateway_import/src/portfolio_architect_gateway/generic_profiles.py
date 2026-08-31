"""Multi-profile state and REST routing for the supported Generic Import Gateway."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
import json
import os
import re
import secrets
import shutil
import ssl
import threading
from typing import Callable, Final

from .errors import ConfigurationError, ProtocolError
from .generic_csv import (
    GenericCsvConfig,
    GenericCsvImportError,
    GenericCsvImportSummary,
    GenericCsvProvider,
    parse_generic_csv,
)
from .models import InvestmentCash, PortfolioSnapshot
from .runtime_config import ServerConfig, read_secret
from .server import GatewayRequestHandler, GatewayState
from .store import load_json_state, save_json_state

LEGACY_PROVIDER_ID: Final = "generic_csv"
MAX_GENERIC_PROFILES: Final = 8
MAX_PROFILE_NAME_LENGTH: Final = 64
REGISTRY_FILE_NAME: Final = "generic-profiles.json"
PROFILES_DIRECTORY_NAME: Final = "generic-profiles"
LEGACY_MAPPING_FILE_NAME: Final = "generic-csv-mapping.json"
LEGACY_DIAGNOSTIC_FILE_NAME: Final = "generic-import-diagnostic.json"
PROFILE_MAPPING_FILE_NAME: Final = "mapping.json"
PROFILE_DIAGNOSTIC_FILE_NAME: Final = "import-diagnostic.json"
PROFILE_SNAPSHOT_FILE_NAME: Final = "portfolio.json"
_PROVIDER_ID_RE: Final = re.compile(r"^generic_[0-9a-f]{12}$")
_PROFILE_PORTFOLIO_PATH_RE: Final = re.compile(
    r"^/api/v1/providers/([a-z][a-z0-9_]{1,31})/portfolio$"
)
_PROFILE_HEALTH_PATH_RE: Final = re.compile(
    r"^/api/v1/providers/([a-z][a-z0-9_]{1,31})/healthz$"
)
MAX_PROFILE_CASH_EUR: Final = Decimal("1000000000")


@dataclass(frozen=True, slots=True)
class GenericProfile:
    """One immutable Generic provider identity plus mutable human label."""

    provider_id: str
    provider_name: str
    created_at: datetime

    @property
    def portfolio_path(self) -> str:
        if self.provider_id == LEGACY_PROVIDER_ID:
            return "/api/v1/portfolio"
        return f"/api/v1/providers/{self.provider_id}/portfolio"

    @property
    def health_path(self) -> str:
        if self.provider_id == LEGACY_PROVIDER_ID:
            return "/healthz"
        return f"/api/v1/providers/{self.provider_id}/healthz"

    def as_dict(self) -> dict[str, str]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "created_at": self.created_at.astimezone(timezone.utc).isoformat(timespec="seconds"),
        }


@dataclass(slots=True)
class GenericProfileRuntime:
    profile: GenericProfile
    provider: GenericCsvProvider
    state: GatewayState


class GenericProfileStore:
    """Persist bounded profile metadata while retaining the legacy generic_csv identity."""

    def __init__(self, data_directory: Path, legacy_snapshot_file: Path) -> None:
        self.data_directory = Path(data_directory)
        self.legacy_snapshot_file = Path(legacy_snapshot_file)
        self.registry_file = self.data_directory / REGISTRY_FILE_NAME
        self.profiles_directory = self.data_directory / PROFILES_DIRECTORY_NAME

    def load_profiles(self) -> tuple[GenericProfile, ...]:
        try:
            raw = load_json_state(self.registry_file)
        except ProtocolError as err:
            raise ConfigurationError("Stored Generic Import profile registry is invalid") from err
        if raw is None:
            profiles: tuple[GenericProfile, ...] = ()
            if self._legacy_state_exists():
                profiles = (
                    GenericProfile(
                        provider_id=LEGACY_PROVIDER_ID,
                        provider_name="Generic Import",
                        created_at=datetime.now(timezone.utc),
                    ),
                )
            self.save_profiles(profiles)
            return profiles
        if set(raw) != {"schema_version", "profiles"} or raw.get("schema_version") != 1:
            raise ConfigurationError("Stored Generic Import profile registry is invalid")
        items = raw.get("profiles")
        if not isinstance(items, list) or len(items) > MAX_GENERIC_PROFILES:
            raise ConfigurationError("Stored Generic Import profile registry is invalid")
        profiles = tuple(_profile_from_dict(item) for item in items)
        ids = [item.provider_id for item in profiles]
        names = [item.provider_name.casefold() for item in profiles]
        if len(ids) != len(set(ids)) or len(names) != len(set(names)):
            raise ConfigurationError("Stored Generic Import profiles are not unique")
        return profiles

    def save_profiles(self, profiles: tuple[GenericProfile, ...]) -> None:
        if len(profiles) > MAX_GENERIC_PROFILES:
            raise ConfigurationError("Too many Generic Import profiles")
        save_json_state(
            self.registry_file,
            {"schema_version": 1, "profiles": [item.as_dict() for item in profiles]},
        )

    def profile_directory(self, provider_id: str) -> Path:
        _validate_profile_provider_id(provider_id)
        if provider_id == LEGACY_PROVIDER_ID:
            return self.data_directory
        return self.profiles_directory / provider_id

    def snapshot_file(self, provider_id: str) -> Path:
        if provider_id == LEGACY_PROVIDER_ID:
            return self.legacy_snapshot_file
        return self.profile_directory(provider_id) / PROFILE_SNAPSHOT_FILE_NAME

    def mapping_file(self, provider_id: str) -> Path:
        if provider_id == LEGACY_PROVIDER_ID:
            return self.data_directory / LEGACY_MAPPING_FILE_NAME
        return self.profile_directory(provider_id) / PROFILE_MAPPING_FILE_NAME

    def diagnostic_file(self, provider_id: str) -> Path:
        if provider_id == LEGACY_PROVIDER_ID:
            return self.data_directory / LEGACY_DIAGNOSTIC_FILE_NAME
        return self.profile_directory(provider_id) / PROFILE_DIAGNOSTIC_FILE_NAME

    def create_directory(self, provider_id: str) -> None:
        if provider_id == LEGACY_PROVIDER_ID:
            return
        directory = self.profile_directory(provider_id)
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        os.chmod(directory, 0o700)

    def delete_private_state(self, provider_id: str) -> None:
        if provider_id == LEGACY_PROVIDER_ID:
            for path in (
                self.snapshot_file(provider_id),
                self.mapping_file(provider_id),
                self.diagnostic_file(provider_id),
            ):
                if path.is_symlink():
                    raise ConfigurationError("Generic Import profile state contains a symlink")
                path.unlink(missing_ok=True)
            return
        directory = self.profile_directory(provider_id)
        if not directory.exists():
            return
        if directory.is_symlink() or not directory.is_dir():
            raise ConfigurationError("Generic Import profile directory is invalid")
        for child in directory.rglob("*"):
            if child.is_symlink():
                raise ConfigurationError("Generic Import profile state contains a symlink")
        shutil.rmtree(directory)

    def _legacy_state_exists(self) -> bool:
        return any(
            path.exists()
            for path in (
                self.legacy_snapshot_file,
                self.data_directory / LEGACY_MAPPING_FILE_NAME,
                self.data_directory / LEGACY_DIAGNOSTIC_FILE_NAME,
            )
        )


class GenericProfileManager:
    """Own all Generic provider profiles and their independent canonical snapshots."""

    def __init__(
        self,
        data_directory: Path,
        server_config: ServerConfig,
        *,
        discovery_changed: Callable[[tuple[GenericProfile, ...]], None] | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._store = GenericProfileStore(data_directory, server_config.snapshot_file)
        self._server_config = server_config
        self._discovery_changed = discovery_changed
        self._profiles = self._store.load_profiles()
        self._runtimes: dict[str, GenericProfileRuntime] = {
            profile.provider_id: self._build_runtime(profile) for profile in self._profiles
        }
        for runtime in self._runtimes.values():
            if runtime.provider.snapshot is not None:
                runtime.state.refresh(trigger="startup")

    def profiles(self) -> tuple[GenericProfile, ...]:
        with self._lock:
            return self._profiles

    def ready_profiles(self) -> tuple[GenericProfile, ...]:
        with self._lock:
            return tuple(
                profile
                for profile in self._profiles
                if self._runtimes[profile.provider_id].state.snapshot_view() is not None
            )

    def runtime(self, provider_id: str) -> GenericProfileRuntime | None:
        with self._lock:
            return self._runtimes.get(provider_id)

    def create_profile(self, provider_name: str) -> GenericProfile:
        name = normalise_profile_name(provider_name)
        with self._lock:
            if len(self._profiles) >= MAX_GENERIC_PROFILES:
                raise GenericCsvImportError(
                    f"Generic Import supports at most {MAX_GENERIC_PROFILES} source profiles"
                )
            if any(item.provider_name.casefold() == name.casefold() for item in self._profiles):
                raise GenericCsvImportError("A Generic Import source with this name already exists")
            provider_id = self._new_provider_id()
            profile = GenericProfile(provider_id, name, datetime.now(timezone.utc))
            self._store.create_directory(provider_id)
            updated = (*self._profiles, profile)
            try:
                self._store.save_profiles(updated)
            except Exception:
                self._store.delete_private_state(provider_id)
                raise
            self._profiles = updated
            self._runtimes[provider_id] = self._build_runtime(profile)
        self._notify_discovery()
        return profile

    def rename_profile(self, provider_id: str, provider_name: str) -> GenericProfile:
        name = normalise_profile_name(provider_name)
        with self._lock:
            current = self._require_profile(provider_id)
            if any(
                item.provider_id != provider_id and item.provider_name.casefold() == name.casefold()
                for item in self._profiles
            ):
                raise GenericCsvImportError("A Generic Import source with this name already exists")
            renamed = replace(current, provider_name=name)
            updated = tuple(renamed if item.provider_id == provider_id else item for item in self._profiles)
            self._store.save_profiles(updated)
            self._profiles = updated
            self._runtimes[provider_id] = self._build_runtime(renamed)
            if self._runtimes[provider_id].provider.snapshot is not None:
                self._runtimes[provider_id].state.refresh(trigger="startup")
        self._notify_discovery()
        return renamed

    def delete_profile(self, provider_id: str) -> None:
        with self._lock:
            self._require_profile(provider_id)
            updated = tuple(item for item in self._profiles if item.provider_id != provider_id)
            self._store.save_profiles(updated)
            self._profiles = updated
            self._runtimes.pop(provider_id, None)
            self._store.delete_private_state(provider_id)
        self._notify_discovery()

    def load_mapping(self, provider_id: str) -> GenericCsvConfig:
        self._require_profile(provider_id)
        path = self._store.mapping_file(provider_id)
        try:
            raw = load_json_state(path)
        except ProtocolError as err:
            raise GenericCsvImportError("Stored CSV mapping is invalid") from err
        if raw is None:
            return GenericCsvConfig()
        if raw.get("schema_version") != 1 or set(raw) != {"schema_version", "mapping"}:
            raise GenericCsvImportError("Stored CSV mapping is invalid")
        mapping = raw.get("mapping")
        if not isinstance(mapping, dict):
            raise GenericCsvImportError("Stored CSV mapping is invalid")
        return GenericCsvConfig.from_mapping(mapping)

    def import_holdings(
        self,
        provider_id: str,
        document: bytes,
        mapping: GenericCsvConfig,
        *,
        generated_at: datetime | None = None,
    ) -> GenericCsvImportSummary:
        with self._lock:
            runtime = self._require_runtime(provider_id)
            snapshot, summary = parse_generic_csv(
                document,
                mapping,
                generated_at=generated_at or datetime.now(timezone.utc),
            )
            previous = runtime.provider.snapshot
            if previous is not None:
                snapshot = PortfolioSnapshot(
                    generated_at=snapshot.generated_at,
                    positions=snapshot.positions,
                    investment_reserve_eur=previous.investment_reserve_eur,
                    investment_reserve_as_of=previous.investment_reserve_as_of,
                    investment_cash=previous.investment_cash,
                )
            save_json_state(
                self._store.mapping_file(provider_id),
                {"schema_version": 1, "mapping": mapping.as_dict()},
            )
            runtime.provider.replace_snapshot(snapshot)
            if not runtime.state.refresh(trigger="manual"):
                runtime.provider.replace_snapshot(previous)
                raise GenericCsvImportError("Imported CSV could not be activated")
        self._notify_discovery()
        return summary

    def set_cash(
        self,
        provider_id: str,
        amount_eur: Decimal,
        *,
        as_of: datetime | None = None,
    ) -> datetime:
        if not isinstance(amount_eur, Decimal) or not amount_eur.is_finite():
            raise GenericCsvImportError("Investment cash must be a finite EUR amount")
        if amount_eur < 0 or amount_eur > MAX_PROFILE_CASH_EUR:
            raise GenericCsvImportError("Investment cash is outside the allowed range")
        stamp = as_of or datetime.now(timezone.utc)
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise GenericCsvImportError("Cash evidence timestamp must include a timezone")
        stamp = stamp.astimezone(timezone.utc)
        with self._lock:
            runtime = self._require_runtime(provider_id)
            previous = runtime.provider.snapshot
            if previous is None:
                raise GenericCsvImportError("Import holdings before recording investment cash")
            cash = InvestmentCash(
                account_balance_eur=amount_eur,
                eligible_eur=amount_eur,
                authorized_eur=amount_eur,
                policy="all_available",
                as_of=stamp,
            )
            snapshot = PortfolioSnapshot(
                generated_at=previous.generated_at,
                positions=previous.positions,
                investment_reserve_eur=amount_eur,
                investment_reserve_as_of=stamp,
                investment_cash=cash,
            )
            runtime.provider.replace_snapshot(snapshot)
            if not runtime.state.refresh(trigger="manual"):
                runtime.provider.replace_snapshot(previous)
                raise GenericCsvImportError("Investment cash could not be activated")
        return stamp

    def clear_cash(self, provider_id: str) -> None:
        with self._lock:
            runtime = self._require_runtime(provider_id)
            previous = runtime.provider.snapshot
            if previous is None:
                raise GenericCsvImportError("No holdings snapshot is available")
            snapshot = PortfolioSnapshot(
                generated_at=previous.generated_at,
                positions=previous.positions,
            )
            runtime.provider.replace_snapshot(snapshot)
            if not runtime.state.refresh(trigger="manual"):
                runtime.provider.replace_snapshot(previous)
                raise GenericCsvImportError("Investment cash could not be cleared")

    def record_diagnostic(self, provider_id: str, outcome: str, message: str) -> None:
        self._require_profile(provider_id)
        if outcome not in {"accepted", "rejected", "internal_error"}:
            raise ValueError("Unsupported Generic Import diagnostic outcome")
        save_json_state(
            self._store.diagnostic_file(provider_id),
            {
                "schema_version": 1,
                "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "outcome": outcome,
                "message": _bounded_notice(message),
            },
        )

    def diagnostic(self, provider_id: str) -> dict[str, str] | None:
        self._require_profile(provider_id)
        try:
            raw = load_json_state(self._store.diagnostic_file(provider_id))
        except ProtocolError:
            return {
                "outcome": "internal_error",
                "message": "Stored import diagnostic is invalid.",
                "recorded_at": "unknown",
            }
        if raw is None or set(raw) != {"schema_version", "recorded_at", "outcome", "message"}:
            return None
        if raw.get("schema_version") != 1:
            return None
        outcome = raw.get("outcome")
        recorded_at = raw.get("recorded_at")
        message = raw.get("message")
        if (
            outcome not in {"accepted", "rejected", "internal_error"}
            or not isinstance(recorded_at, str)
            or not isinstance(message, str)
            or _bounded_notice(message) != message
        ):
            return None
        return {"outcome": outcome, "recorded_at": recorded_at, "message": message}

    def resolve_path(self, path: str) -> tuple[GatewayState, str] | None:
        with self._lock:
            if path == "/api/v1/portfolio":
                runtime = self._runtimes.get(LEGACY_PROVIDER_ID)
                return (runtime.state, "portfolio") if runtime is not None else None
            if path == "/healthz":
                runtime = self._runtimes.get(LEGACY_PROVIDER_ID)
                return (runtime.state, "health") if runtime is not None else None
            match = _PROFILE_PORTFOLIO_PATH_RE.fullmatch(path)
            kind = "portfolio"
            if match is None:
                match = _PROFILE_HEALTH_PATH_RE.fullmatch(path)
                kind = "health"
            if match is None:
                return None
            runtime = self._runtimes.get(match.group(1))
            return (runtime.state, kind) if runtime is not None else None

    def _new_provider_id(self) -> str:
        existing = {item.provider_id for item in self._profiles}
        for _ in range(32):
            candidate = f"generic_{secrets.token_hex(6)}"
            if candidate not in existing:
                return candidate
        raise GenericCsvImportError("Could not allocate a unique Generic provider identity")

    def _require_profile(self, provider_id: str) -> GenericProfile:
        for profile in self._profiles:
            if profile.provider_id == provider_id:
                return profile
        raise GenericCsvImportError("Generic Import source profile does not exist")

    def _require_runtime(self, provider_id: str) -> GenericProfileRuntime:
        self._require_profile(provider_id)
        runtime = self._runtimes.get(provider_id)
        if runtime is None:
            raise GenericCsvImportError("Generic Import source runtime is unavailable")
        return runtime

    def _build_runtime(self, profile: GenericProfile) -> GenericProfileRuntime:
        snapshot_file = self._store.snapshot_file(profile.provider_id)
        provider = GenericCsvProvider(
            snapshot_file,
            provider_id=profile.provider_id,
            provider_name=profile.provider_name,
        )
        config = replace(self._server_config, snapshot_file=snapshot_file)
        return GenericProfileRuntime(profile, provider, GatewayState(config, provider))

    def _notify_discovery(self) -> None:
        callback = self._discovery_changed
        if callback is not None:
            callback(self.ready_profiles())


class GenericMultiGatewayHttpServer(ThreadingHTTPServer):
    """One private-PKI origin serving multiple independent Generic providers."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        config: ServerConfig,
        manager: GenericProfileManager,
        api_token: str,
    ) -> None:
        self.profile_manager = manager
        self.api_token = api_token
        self.health_endpoint_enabled = config.health_endpoint_enabled
        super().__init__((config.bind, config.port), GenericMultiGatewayRequestHandler)
        if config.tls_cert_file and config.tls_key_file:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(
                certfile=config.tls_cert_file,
                keyfile=config.tls_key_file,
            )
            self.socket = context.wrap_socket(self.socket, server_side=True)


class GenericMultiGatewayRequestHandler(GatewayRequestHandler):
    """Route fixed authenticated provider paths to isolated Generic profile states."""

    @property
    def generic_server(self) -> GenericMultiGatewayHttpServer:
        return self.server  # type: ignore[return-value]

    @property
    def gateway_server(self) -> GenericMultiGatewayHttpServer:  # type: ignore[override]
        return self.generic_server

    @property
    def request_gateway_state(self) -> GatewayState:
        selected = getattr(self, "_selected_gateway_state", None)
        if not isinstance(selected, GatewayState):
            raise RuntimeError("Generic provider state was not selected")
        return selected

    def do_GET(self) -> None:  # noqa: N802
        if not self._headers_within_limit():
            self._send_error(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE)
            return
        if not self._authenticated():
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.send_header("WWW-Authenticate", 'Bearer realm="portfolio-architect"')
            self._security_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        resolved = self.generic_server.profile_manager.resolve_path(self.path)
        if resolved is None:
            self._send_error(HTTPStatus.NOT_FOUND)
            return
        state, kind = resolved
        self._selected_gateway_state = state
        if kind == "portfolio":
            self._serve_portfolio()
            return
        if kind == "health" and self.generic_server.health_endpoint_enabled:
            self._serve_health()
            return
        self._send_error(HTTPStatus.NOT_FOUND)


def create_generic_multi_server(
    config: ServerConfig,
    manager: GenericProfileManager,
) -> GenericMultiGatewayHttpServer:
    token = read_secret(
        config.api_token_file,
        name="gateway API token",
        minimum=32,
        maximum=512,
    )
    return GenericMultiGatewayHttpServer(config, manager, token)


def normalise_profile_name(value: str) -> str:
    if not isinstance(value, str):
        raise GenericCsvImportError("Source name is required")
    cleaned = value.strip()
    if (
        not cleaned
        or len(cleaned) > MAX_PROFILE_NAME_LENGTH
        or any(ord(char) < 32 or ord(char) == 127 for char in cleaned)
    ):
        raise GenericCsvImportError("Source name is empty, too long, or contains control characters")
    return cleaned


def _profile_from_dict(raw: object) -> GenericProfile:
    if not isinstance(raw, dict) or set(raw) != {"provider_id", "provider_name", "created_at"}:
        raise ConfigurationError("Stored Generic Import profile is invalid")
    provider_id = raw.get("provider_id")
    if not isinstance(provider_id, str):
        raise ConfigurationError("Stored Generic Import profile is invalid")
    _validate_profile_provider_id(provider_id)
    provider_name_raw = raw.get("provider_name")
    if not isinstance(provider_name_raw, str):
        raise ConfigurationError("Stored Generic Import profile is invalid")
    try:
        provider_name = normalise_profile_name(provider_name_raw)
    except GenericCsvImportError as err:
        raise ConfigurationError("Stored Generic Import profile is invalid") from err
    created_at_raw = raw.get("created_at")
    if not isinstance(created_at_raw, str) or len(created_at_raw) > 64:
        raise ConfigurationError("Stored Generic Import profile is invalid")
    try:
        created_at = datetime.fromisoformat(created_at_raw)
    except ValueError as err:
        raise ConfigurationError("Stored Generic Import profile is invalid") from err
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ConfigurationError("Stored Generic Import profile is invalid")
    return GenericProfile(provider_id, provider_name, created_at.astimezone(timezone.utc))


def _validate_profile_provider_id(provider_id: str) -> None:
    if provider_id == LEGACY_PROVIDER_ID:
        return
    if _PROVIDER_ID_RE.fullmatch(provider_id) is None:
        raise ConfigurationError("Generic Import provider identity is invalid")


def _bounded_notice(message: str) -> str:
    cleaned = str(message or "").strip()
    if not cleaned or len(cleaned) > 320 or any(ord(char) < 32 for char in cleaned):
        raise ValueError("Import diagnostic is invalid")
    return cleaned
