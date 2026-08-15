"""Prepare isolated provider-shell state, drop privileges, and start."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from portfolio_architect_gateway.supervisor_tls import (
    prepare_supervisor_tls,
    start_supervisor_tls_discovery_publisher,
)

from portfolio_architect_gateway.pending_app import PendingAppOptions, serve_pending_app
from portfolio_architect_gateway.provider import normalise_provider_id

APP_UID = 65532
APP_GID = 65532
DATA = Path("/data/gateway")


def main() -> int:
    provider_id = normalise_provider_id(os.environ["PA_PROVIDER_ID"])
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
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    tls = prepare_supervisor_tls(DATA, provider_id)
    serve_pending_app(
        provider_id=provider_id,
        provider_name=provider_name,
        options=options,
        tls_cert_file=tls.cert_file,
        tls_key_file=tls.key_file,
        ready_callback=lambda: start_supervisor_tls_discovery_publisher(tls, provider_id),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
