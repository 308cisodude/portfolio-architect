"""Prepare Generic Import private state, drop privileges, and start."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import signal
import threading

from portfolio_architect_gateway.generic_import_app import serve_generic_import_app
from portfolio_architect_gateway.pending_app import PendingAppOptions
from portfolio_architect_gateway.provider import normalise_provider_id
from portfolio_architect_gateway.supervisor_tls import (
    delete_supervisor_tls_discovery,
    prepare_supervisor_tls,
    start_supervisor_tls_discovery_publisher,
)

APP_UID = 65532
APP_GID = 65532
DATA = Path("/data/gateway")
DISCOVERY_UUID_FILE = DATA / "generic-import-discovery-uuid"
_DISCOVERY_UUID_RE = re.compile(r"^[0-9a-f]{32}$")
_LOGGER = logging.getLogger(__name__)


class _GenericDiscoveryLifecycle:
    """Track the exact Supervisor discovery record owned by Generic Import."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self.stop_event = threading.Event()
        self.publisher: threading.Thread | None = None

    def reconcile_before_publish(self) -> bool:
        discovery_uuid = self._read_uuid()
        if discovery_uuid is None:
            return True
        try:
            delete_supervisor_tls_discovery(discovery_uuid)
        except RuntimeError:
            _LOGGER.warning(
                "Generic Import retained discovery cleanup is temporarily unavailable; "
                "skipping duplicate discovery publication"
            )
            return False
        self._remove_uuid_file()
        _LOGGER.info("Generic Import reconciled its retained Supervisor discovery record")
        return True

    def record_published(self, discovery_uuid: str) -> None:
        if _DISCOVERY_UUID_RE.fullmatch(discovery_uuid) is None:
            raise RuntimeError("Generic Import discovery identifier is invalid")
        temporary = self._path.with_name(self._path.name + ".tmp")
        temporary.write_text(discovery_uuid + "\n", encoding="ascii")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self._path)

    def cleanup(self) -> None:
        self.stop_event.set()
        if self.publisher is not None:
            self.publisher.join(timeout=12.0)
        discovery_uuid = self._read_uuid()
        if discovery_uuid is None:
            return
        try:
            delete_supervisor_tls_discovery(discovery_uuid)
        except RuntimeError:
            _LOGGER.warning(
                "Generic Import could not remove its Supervisor discovery record during shutdown; "
                "the exact identifier is retained for the next startup"
            )
            return
        self._remove_uuid_file()
        _LOGGER.info("Generic Import removed its Supervisor discovery record during shutdown")

    def _read_uuid(self) -> str | None:
        try:
            value = self._path.read_text(encoding="ascii").strip()
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError) as err:
            raise RuntimeError("Generic Import discovery state cannot be read safely") from err
        if _DISCOVERY_UUID_RE.fullmatch(value) is None:
            raise RuntimeError("Generic Import discovery state is invalid")
        return value

    def _remove_uuid_file(self) -> None:
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass


def _raise_keyboard_interrupt(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def main() -> int:
    provider_id = normalise_provider_id(os.environ["PA_PROVIDER_ID"])
    if provider_id != "generic_csv":
        raise RuntimeError("Generic Import provider identity is invalid")
    provider_name = os.environ["PA_PROVIDER_NAME"].strip()
    if not provider_name or len(provider_name) > 64:
        raise RuntimeError("Provider display name is invalid")
    options = PendingAppOptions.load()
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DATA, 0o700)
    os.chown(DATA, APP_UID, APP_GID)
    for child in DATA.iterdir():
        if child.is_symlink():
            raise RuntimeError("Symlinks are not permitted in the gateway data directory")
        os.chown(child, APP_UID, APP_GID)
        if child.is_file():
            os.chmod(child, 0o600)
        elif child.is_dir() and child.name == "tls":
            os.chmod(child, 0o700)
            for tls_child in child.iterdir():
                if tls_child.is_symlink() or not tls_child.is_file():
                    raise RuntimeError("Invalid entry in gateway TLS directory")
                os.chown(tls_child, APP_UID, APP_GID)
                os.chmod(tls_child, 0o600)
    os.setgroups([])
    os.setgid(APP_GID)
    os.setuid(APP_UID)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    tls = prepare_supervisor_tls(DATA, provider_id)
    lifecycle = _GenericDiscoveryLifecycle(DISCOVERY_UUID_FILE)
    can_publish = lifecycle.reconcile_before_publish()
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)

    def _ready() -> None:
        if not can_publish:
            return
        lifecycle.publisher = start_supervisor_tls_discovery_publisher(
            tls,
            provider_id,
            on_published=lifecycle.record_published,
            stop_event=lifecycle.stop_event,
        )

    try:
        serve_generic_import_app(
            provider_name=provider_name,
            options=options,
            tls_cert_file=tls.cert_file,
            tls_key_file=tls.key_file,
            ready_callback=_ready,
        )
    finally:
        lifecycle.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
