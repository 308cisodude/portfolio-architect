"""Regression coverage for the v1.24.1 provider-shell startup hotfix."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[1]
SHELLS = (
    ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb",
    ROOT / "home_assistant_app" / "portfolio_architect_gateway_trade_republic",
)


def test_shell_runtime_imports_without_comdirect_config_module(tmp_path: Path) -> None:
    """The isolated shell package must import exactly as shipped in its container."""
    for app in SHELLS:
        source = app / "src"
        package = source / "portfolio_architect_gateway"
        assert not (package / "config.py").exists()

        env = os.environ.copy()
        env["PYTHONPATH"] = str(source)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import portfolio_architect_gateway.pending_app; "
                    "import portfolio_architect_gateway.server"
                ),
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, result.stderr


def test_server_comdirect_configuration_import_is_type_check_only() -> None:
    source = (
        ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "server.py"
    ).read_text(encoding="utf-8")
    assert "if TYPE_CHECKING:" in source
    assert "from .config import GatewayConfig" in source
    assert source.index("if TYPE_CHECKING:") < source.index("from .config import GatewayConfig")


def test_shell_dockerfiles_import_real_startup_module_during_build() -> None:
    for app in SHELLS:
        dockerfile = (app / "Dockerfile").read_text(encoding="utf-8")
        assert "import portfolio_architect_gateway.pending_app" in dockerfile
