"""Prepare Generic Import private state, drop privileges, and start."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import signal
import threading

from portfolio_architect_gateway.generic_import_app import serve_generic_import_app
from portfolio_architect_gateway.generic_profiles import GenericProfile
from portfolio_architect_gateway.pending_app import PendingAppOptions
from portfolio_architect_gateway.provider import normalise_provider_id, normalise_provider_name
from portfolio_architect_gateway.supervisor_tls import (
    SupervisorTlsMaterial,
    delete_supervisor_tls_discovery,
    prepare_supervisor_tls,
    publish_supervisor_tls_discovery,
)

APP_UID = 65532
APP_GID = 65532
DATA = Path("/data/gateway")
LEGACY_DISCOVERY_UUID_FILE = DATA / "generic-import-discovery-uuid"
DISCOVERY_STATE_FILE = DATA / "generic-import-discoveries.json"
_DISCOVERY_UUID_RE = re.compile(r"^[0-9a-f]{32}$")
_LOGGER = logging.getLogger(__name__)


class _GenericDiscoveryLifecycle:
    """Reconcile one Supervisor discovery record per ready Generic profile."""

    def __init__(
        self,
        material: SupervisorTlsMaterial,
        state_path: Path,
        legacy_uuid_path: Path,
    ) -> None:
        self._material = material
        self._state_path = state_path
        self._legacy_uuid_path = legacy_uuid_path
        self._lock = threading.RLock()
        self._desired: dict[str, tuple[str, str]] = {}
        self._records = self._load_records()
        self._replace_on_start = set(self._records)
        self._legacy_uuid = self._read_legacy_uuid()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = threading.Thread(
            target=self._worker,
            name="portfolio-generic-discovery",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def update(self, profiles: tuple[GenericProfile, ...]) -> None:
        desired: dict[str, tuple[str, str]] = {}
        for profile in profiles:
            provider_id = normalise_provider_id(profile.provider_id)
            provider_name = normalise_provider_name(profile.provider_name)
            desired[provider_id] = (provider_name, profile.portfolio_path)
        with self._lock:
            self._desired = desired
        self._wake.set()

    def cleanup(self) -> None:
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=12.0)
        with self._lock:
            uuids = [(provider_id, item[0]) for provider_id, item in self._records.items()]
            legacy_uuid = self._legacy_uuid
        retained: dict[str, tuple[str, str, str]] = {}
        for provider_id, discovery_uuid in uuids:
            try:
                delete_supervisor_tls_discovery(discovery_uuid)
            except RuntimeError:
                with self._lock:
                    item = self._records.get(provider_id)
                if item is not None:
                    retained[provider_id] = item
                _LOGGER.warning(
                    "Generic Import could not remove one Supervisor discovery record during shutdown"
                )
        if legacy_uuid is not None:
            try:
                delete_supervisor_tls_discovery(legacy_uuid)
            except RuntimeError:
                _LOGGER.warning(
                    "Generic Import could not remove its retained legacy discovery record during shutdown"
                )
            else:
                self._remove_legacy_uuid_file()
                legacy_uuid = None
        with self._lock:
            self._records = retained
            self._legacy_uuid = legacy_uuid
            self._save_records()
        if not retained and legacy_uuid is None:
            _LOGGER.info("Generic Import removed its Supervisor discovery records during shutdown")

    def _worker(self) -> None:
        while not self._stop.is_set():
            pending = self._reconcile_once()
            self._wake.clear()
            if self._stop.is_set():
                return
            self._wake.wait(5.0 if pending else None)

    def _reconcile_once(self) -> bool:
        with self._lock:
            desired = dict(self._desired)
            records = dict(self._records)
            replace = set(self._replace_on_start)
            legacy_uuid = self._legacy_uuid

        pending = False
        if legacy_uuid is not None:
            try:
                delete_supervisor_tls_discovery(legacy_uuid)
            except RuntimeError:
                pending = True
            else:
                with self._lock:
                    if self._legacy_uuid == legacy_uuid:
                        self._legacy_uuid = None
                        self._remove_legacy_uuid_file()
                _LOGGER.info("Generic Import reconciled its pre-v1.62 Supervisor discovery record")

        for provider_id, (discovery_uuid, published_name, published_path) in records.items():
            wanted = desired.get(provider_id)
            needs_delete = (
                wanted is None
                or provider_id in replace
                or wanted != (published_name, published_path)
            )
            if not needs_delete:
                continue
            try:
                delete_supervisor_tls_discovery(discovery_uuid)
            except RuntimeError:
                pending = True
                continue
            with self._lock:
                current = self._records.get(provider_id)
                if current is not None and current[0] == discovery_uuid:
                    self._records.pop(provider_id, None)
                    self._replace_on_start.discard(provider_id)
                    self._save_records()
            _LOGGER.info("Generic Import removed one stale Supervisor discovery record")

        with self._lock:
            current_records = dict(self._records)
            desired = dict(self._desired)
        for provider_id, (provider_name, path) in desired.items():
            if provider_id in current_records:
                continue
            try:
                discovery_uuid = publish_supervisor_tls_discovery(
                    self._material,
                    provider_id,
                    path=path,
                    provider_name=provider_name,
                )
            except RuntimeError:
                pending = True
                continue
            try:
                with self._lock:
                    if self._desired.get(provider_id) != (provider_name, path):
                        raise RuntimeError("Generic Import discovery changed during publication")
                    self._records[provider_id] = (discovery_uuid, provider_name, path)
                    self._save_records()
            except Exception:
                try:
                    delete_supervisor_tls_discovery(discovery_uuid)
                except RuntimeError:
                    pass
                pending = True
                continue
            _LOGGER.info("Generic Import published one ready provider through Supervisor discovery")
        return pending

    def _load_records(self) -> dict[str, tuple[str, str, str]]:
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, UnicodeError, json.JSONDecodeError) as err:
            raise RuntimeError("Generic Import discovery state cannot be read safely") from err
        if not isinstance(raw, dict) or set(raw) != {"schema_version", "records"}:
            raise RuntimeError("Generic Import discovery state is invalid")
        if raw.get("schema_version") != 1 or not isinstance(raw.get("records"), list):
            raise RuntimeError("Generic Import discovery state is invalid")
        records: dict[str, tuple[str, str, str]] = {}
        for item in raw["records"]:
            if not isinstance(item, dict) or set(item) != {"provider_id", "provider_name", "path", "uuid"}:
                raise RuntimeError("Generic Import discovery state is invalid")
            provider_id = normalise_provider_id(item.get("provider_id"))
            provider_name = normalise_provider_name(item.get("provider_name"))
            path = item.get("path")
            discovery_uuid = item.get("uuid")
            expected_path = (
                "/api/v1/portfolio"
                if provider_id == "generic_csv"
                else f"/api/v1/providers/{provider_id}/portfolio"
            )
            if path != expected_path or not isinstance(discovery_uuid, str) or _DISCOVERY_UUID_RE.fullmatch(discovery_uuid) is None:
                raise RuntimeError("Generic Import discovery state is invalid")
            if provider_id in records:
                raise RuntimeError("Generic Import discovery state contains duplicate providers")
            records[provider_id] = (discovery_uuid, provider_name, path)
        return records

    def _save_records(self) -> None:
        records = [
            {
                "provider_id": provider_id,
                "provider_name": provider_name,
                "path": path,
                "uuid": discovery_uuid,
            }
            for provider_id, (discovery_uuid, provider_name, path) in sorted(self._records.items())
        ]
        payload = json.dumps(
            {"schema_version": 1, "records": records},
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        temporary = self._state_path.with_name(self._state_path.name + ".tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self._state_path)

    def _read_legacy_uuid(self) -> str | None:
        try:
            value = self._legacy_uuid_path.read_text(encoding="ascii").strip()
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError) as err:
            raise RuntimeError("Generic Import legacy discovery state cannot be read safely") from err
        if _DISCOVERY_UUID_RE.fullmatch(value) is None:
            raise RuntimeError("Generic Import legacy discovery state is invalid")
        return value

    def _remove_legacy_uuid_file(self) -> None:
        try:
            self._legacy_uuid_path.unlink()
        except FileNotFoundError:
            pass


def _secure_data_tree() -> None:
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    for path in [DATA, *DATA.rglob("*")]:
        if path.is_symlink():
            raise RuntimeError("Symlinks are not permitted in the gateway data directory")
        os.chown(path, APP_UID, APP_GID)
        if path.is_dir():
            os.chmod(path, 0o700)
        elif path.is_file():
            os.chmod(path, 0o600)
        else:
            raise RuntimeError("Unsupported entry in the gateway data directory")


def _raise_keyboard_interrupt(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def main() -> int:
    package_provider_id = normalise_provider_id(os.environ["PA_PROVIDER_ID"])
    if package_provider_id != "generic_csv":
        raise RuntimeError("Generic Import package identity is invalid")
    provider_name = normalise_provider_name(os.environ["PA_PROVIDER_NAME"])
    options = PendingAppOptions.load()
    _secure_data_tree()
    os.setgroups([])
    os.setgid(APP_GID)
    os.setuid(APP_UID)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    tls = prepare_supervisor_tls(DATA, package_provider_id)
    lifecycle = _GenericDiscoveryLifecycle(
        tls,
        DISCOVERY_STATE_FILE,
        LEGACY_DISCOVERY_UUID_FILE,
    )
    lifecycle.start()
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    try:
        serve_generic_import_app(
            provider_name=provider_name,
            options=options,
            tls_cert_file=tls.cert_file,
            tls_key_file=tls.key_file,
            discovery_changed=lifecycle.update,
        )
    finally:
        lifecycle.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
