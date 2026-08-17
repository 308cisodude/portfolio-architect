"""Regression coverage for the v1.31.2 provider-shell startup hotfix."""
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
        import_statement = (
            "import portfolio_architect_gateway.dkb_app; "
            "import portfolio_architect_gateway.server"
            if app.name == "portfolio_architect_gateway_dkb"
            else "import portfolio_architect_gateway.trade_republic_app; import portfolio_architect_gateway.server"
        )
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                import_statement,
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
    dkb = (SHELLS[0] / "Dockerfile").read_text(encoding="utf-8")
    trade_republic = (SHELLS[1] / "Dockerfile").read_text(encoding="utf-8")
    assert "import portfolio_architect_gateway.dkb_app" in dkb
    assert "import portfolio_architect_gateway.trade_republic_app" in trade_republic


def test_provider_shell_smoke_env_matches_home_assistant_app_metadata() -> None:
    """CI must launch shells with the same provider environment Supervisor supplies."""
    import importlib.util
    import yaml

    helper_path = ROOT / "tools" / "provider_shell_env.py"
    spec = importlib.util.spec_from_file_location("provider_shell_env", helper_path)
    assert spec is not None and spec.loader is not None
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)

    expected = {
        "portfolio_architect_gateway_dkb": ("dkb", "DKB"),
        "portfolio_architect_gateway_trade_republic": ("trade_republic", "Trade Republic"),
    }
    for app_name, values in expected.items():
        config_path = ROOT / "home_assistant_app" / app_name / "config.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert (
            config["environment"]["PA_PROVIDER_ID"],
            config["environment"]["PA_PROVIDER_NAME"],
        ) == values
        assert helper.load_environment(config_path) == values


def test_provider_shell_smoke_workflows_supply_supervisor_environment() -> None:
    for workflow_name in ("validate.yml", "release.yml"):
        workflow = (ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
        assert 'python tools/provider_shell_env.py "home_assistant_app/${app}/config.yaml"' in workflow
        assert '--env "PA_PROVIDER_ID=${provider_env[0]}"' in workflow
        assert '--env "PA_PROVIDER_NAME=${provider_env[1]}"' in workflow
