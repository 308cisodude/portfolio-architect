"""Start the provider-qualified Comdirect migration shell or canonical runtime."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil

from portfolio_architect_gateway.app import AppOptions, serve_app
from portfolio_architect_gateway.comdirect_migration_app import serve_comdirect_migration_setup
from portfolio_architect_gateway.comdirect_slug_migration import (
    CUTOVER_MARKER_NAME,
    expected_legacy_hostname,
    validate_committed_migration_identity,
)
from portfolio_architect_gateway.supervisor_tls import (
    prepare_supervisor_tls,
    start_supervisor_tls_discovery_publisher,
    supervisor_app_hostname,
)

APP_UID = 65532
APP_GID = 65532
DATA_ROOT = Path("/data")
DATA = DATA_ROOT / "gateway"
WORKSPACE = DATA_ROOT / "comdirect-slug-migration-work"
DISPLAY_TITLE = "Portfolio Architect Gateway — Comdirect NEW"


def _secure_tree_for_runtime(path: Path) -> None:
    """Make only ordinary private migration/runtime files available to the service UID."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    for item in (path, *path.rglob("*")):
        if item.is_symlink():
            raise RuntimeError("Symlinks are not permitted in the gateway data directory")
        os.chown(item, APP_UID, APP_GID)
        if item.is_dir():
            os.chmod(item, 0o700)
        elif item.is_file():
            os.chmod(item, 0o600)
        else:
            raise RuntimeError("Unsupported entry in gateway data directory")


def _drop_privileges() -> None:
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


def main() -> int:
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    # Resolve the App identity while still privileged. This performs only the fixed
    # Supervisor self-info request and validates the provider-qualified hostname.
    hostname = supervisor_app_hostname(supervisor_token=token)
    # Fail closed unless Supervisor assigned exactly the provider-qualified
    # Comdirect successor shape. The derived legacy hostname is intentionally
    # unused here; computing it performs the bounded identity validation.
    expected_legacy_hostname(hostname)

    cutover = DATA / CUTOVER_MARKER_NAME
    if not cutover.is_file():
        # Pending migration state is App-private and owned by the unprivileged process.
        DATA_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chown(DATA_ROOT, APP_UID, APP_GID)
        if WORKSPACE.exists() and WORKSPACE.is_symlink():
            raise RuntimeError("Migration workspace must not be a symlink")
        WORKSPACE.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chown(WORKSPACE, APP_UID, APP_GID)
        if DATA.exists():
            _secure_tree_for_runtime(DATA)
        _drop_privileges()
        serve_comdirect_migration_setup(
            hostname=hostname,
            supervisor_token=token,
            data_root=DATA_ROOT,
            workspace_directory=WORKSPACE,
        )
        return 0

    # Supervisor options are outside /data/gateway and can be root-only. Load them
    # before setuid, after migration has explicitly committed/reconciled them.
    options = AppOptions.load()
    expected_ca_sha256 = validate_committed_migration_identity(
        DATA,
        successor_hostname=hostname,
    )
    _secure_tree_for_runtime(DATA)
    if WORKSPACE.exists():
        if WORKSPACE.is_symlink():
            raise RuntimeError("Migration workspace must not be a symlink")
        shutil.rmtree(WORKSPACE)
    _drop_privileges()

    # Migrated state contains the old hostname leaf. prepare_supervisor_tls renews
    # only that leaf for this new hostname and preserves the private CA/key.
    tls = prepare_supervisor_tls(DATA, "comdirect")
    if expected_ca_sha256 is not None and tls.ca_sha256 != expected_ca_sha256:
        raise RuntimeError("Migrated Comdirect private CA changed during leaf renewal")

    serve_app(
        options=options,
        tls_cert_file=tls.cert_file,
        tls_key_file=tls.key_file,
        gateway_endpoint_url=f"https://{tls.hostname}:8787/api/v1/portfolio",
        ready_callback=lambda _controller: start_supervisor_tls_discovery_publisher(
            tls, "comdirect"
        ),
        display_title=DISPLAY_TITLE,
        ready_when_live=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
