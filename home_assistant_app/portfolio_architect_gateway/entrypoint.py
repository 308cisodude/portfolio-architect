"""Prepare private state, read Supervisor options, drop privileges, and start."""

from __future__ import annotations

import logging
import os
from pathlib import Path

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
    serve_app(options=options)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
