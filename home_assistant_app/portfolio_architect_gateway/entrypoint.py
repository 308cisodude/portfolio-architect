"""Prepare private state, read Supervisor options, drop privileges, and start."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from portfolio_architect_gateway.comdirect_slug_migration import (
    FREEZE_MARKER_NAME,
    legacy_is_frozen,
)
from portfolio_architect_gateway.supervisor_tls import (
    prepare_supervisor_tls,
    start_supervisor_tls_discovery_publisher,
)

# Import the complete runtime while the interpreter still has its initial
# privileges. Home Assistant Supervisor keeps /data/options.json root-owned,
# so the immutable, non-secret options must also be loaded before setuid().
from portfolio_architect_gateway.app import AppOptions, serve_app

APP_UID = 65532
APP_GID = 65532
DATA = Path("/data/gateway")


def main() -> int:
    # Supervisor-managed App options are intentionally outside the gateway's
    # writable data directory and may be readable only by root. Parse and
    # validate them once, before privileges are dropped.
    options = AppOptions.load()

    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DATA, 0o700)
    os.chown(DATA, APP_UID, APP_GID)
    for child in DATA.iterdir():
        if child.is_symlink():
            raise RuntimeError(
                "Symlinks are not permitted in the gateway data directory"
            )
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
    print(
        "Portfolio Architect Gateway runtime initialized as uid=65532 gid=65532",
        flush=True,
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    tls = prepare_supervisor_tls(DATA, "comdirect")
    migrated_options = {
        "poll_interval_seconds": options.poll_interval_seconds,
        "max_cached_snapshot_age_seconds": options.max_cached_snapshot_age_seconds,
        "request_timeout_seconds": options.request_timeout_seconds,
        "mfa_timeout_seconds": options.mfa_timeout_seconds,
        "health_endpoint_enabled": options.health_endpoint_enabled,
        "depot_ids": list(options.depot_ids),
    }
    frozen = legacy_is_frozen(DATA / FREEZE_MARKER_NAME)
    serve_app(
        options=options,
        tls_cert_file=tls.cert_file,
        tls_key_file=tls.key_file,
        gateway_endpoint_url=f"https://{tls.hostname}:8787/api/v1/portfolio",
        ready_callback=(
            None
            if frozen
            else lambda _controller: start_supervisor_tls_discovery_publisher(
                tls, "comdirect"
            )
        ),
        legacy_migration_hostname=tls.hostname,
        legacy_migration_options=migrated_options,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
