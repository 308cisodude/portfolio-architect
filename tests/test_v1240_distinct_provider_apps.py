"""Regression contracts for v1.26.5 distinct provider Home Assistant Apps."""
from __future__ import annotations

import json
from pathlib import Path
import yaml

ROOT=Path(__file__).parents[1]
MASTER=ROOT/"gateway"/"src"/"portfolio_architect_gateway"
APPS={
 "comdirect": ROOT/"home_assistant_app"/"portfolio_architect_gateway",
 "dkb": ROOT/"home_assistant_app"/"portfolio_architect_gateway_dkb",
 "trade_republic": ROOT/"home_assistant_app"/"portfolio_architect_gateway_trade_republic",
}
SHELL_FILES={"__init__.py","errors.py","models.py","provider.py","runtime_config.py","server.py","store.py","pending_app.py"}
TR_PROVIDER_FILES={"trade_republic_app.py","trade_republic_statement.py"}

def test_three_provider_apps_have_unique_stable_identities_and_isolated_storage():
    configs={k:yaml.safe_load((p/"config.yaml").read_text(encoding="utf-8")) for k,p in APPS.items()}
    assert configs["comdirect"]["name"]=="Portfolio Architect Gateway — Comdirect"
    assert configs["comdirect"]["slug"]=="portfolio_architect_gateway"
    assert configs["comdirect"]["stage"]=="stable"
    assert configs["dkb"]["slug"]=="portfolio_architect_gateway_dkb"
    assert configs["trade_republic"]["slug"]=="portfolio_architect_gateway_trade_republic"
    assert len({c["slug"] for c in configs.values()})==3
    assert all(c["version"]=="1.26.5" for c in configs.values())
    for key in ("dkb","trade_republic"):
        assert configs[key]["stage"]=="experimental"
        assert configs[key]["host_network"] is False
        assert configs[key]["homeassistant_api"] is False
        assert configs[key]["hassio_api"] is False
        assert configs[key]["docker_api"] is False
        assert configs[key]["ports"]["8787/tcp"] is None
        entry=(APPS[key]/"entrypoint.py").read_text(encoding="utf-8")
        assert 'DATA = Path("/data/gateway")' in entry
    assert configs["dkb"]["boot"] == "manual_only"
    assert configs["trade_republic"]["boot"] == "auto"

def test_shell_apps_share_only_audited_provider_neutral_runtime_files():
    for key in ("dkb","trade_republic"):
        src=APPS[key]/"src"/"portfolio_architect_gateway"
        expected=SHELL_FILES | (TR_PROVIDER_FILES if key == "trade_republic" else set())
        assert {p.name for p in src.glob("*.py")}==expected
        for name in SHELL_FILES:
            assert (src/name).read_bytes()==(MASTER/name).read_bytes()
        text="\n".join((src/n).read_text(encoding="utf-8") for n in expected)
        assert "ComdirectClient" not in text
        assert "api.comdirect.de" not in text

def test_comdirect_app_still_matches_complete_gateway_source():
    src=APPS["comdirect"]/"src"/"portfolio_architect_gateway"
    names={p.name for p in MASTER.glob("*.py")}
    assert {p.name for p in src.glob("*.py")}==names
    for name in names:
        assert (src/name).read_bytes()==(MASTER/name).read_bytes()

def test_pending_provider_shell_is_fail_closed_and_read_only():
    source=(MASTER/"pending_app.py").read_text(encoding="utf-8")
    assert 'raise ConfigurationError("Provider acquisition is not implemented in this release")' in source
    assert 'state.refresh(trigger="startup")' in source
    assert 'self.send_header("Allow", "GET")' in source
    for method in ("do_POST","do_PUT","do_PATCH","do_DELETE"):
        assert method in source
    for forbidden in ("submit_order", "place_order", "create_order", "transaction_history"):
        assert forbidden not in source

def test_server_state_is_provider_neutral_at_configuration_boundary():
    source=(MASTER/"server.py").read_text(encoding="utf-8")
    assert "def __init__(self, config: ServerConfig, client: PortfolioProvider)" in source
    assert "GatewayState(config.server, client)" in source
    assert "create_server(config.server, state)" in source
    assert "self._config.server." not in source

def test_release_builder_publishes_three_distinct_gateway_archives():
    build=(ROOT/"tools"/"build_release.py").read_text(encoding="utf-8")
    verify=(ROOT/"tools"/"verify_release.py").read_text(encoding="utf-8")
    for stem in ("gateway-app","gateway-dkb-app","gateway-trade-republic-app"):
        assert f"portfolio-architect-{stem}-v{{version}}.zip" in build
        assert f"portfolio-architect-{stem}-v{{release_version}}.zip" in verify

def test_provider_capability_boundaries_are_explicit():
    dkb=yaml.safe_load((APPS["dkb"]/"config.yaml").read_text(encoding="utf-8"))
    trade_republic=yaml.safe_load((APPS["trade_republic"]/"config.yaml").read_text(encoding="utf-8"))
    assert "not implemented" in dkb["description"]
    assert "statement" in trade_republic["description"].casefold()
    roadmap=(ROOT/"docs"/"ROADMAP.md").read_text(encoding="utf-8")
    assert "Trade Republic statement import" in roadmap
    assert "multiple Gateway REST aggregation" in roadmap
    assert "v1.26.5" in roadmap

def test_current_release_version_is_1260():
    manifest=json.loads((ROOT/"custom_components"/"portfolio_architect"/"manifest.json").read_text())
    assert manifest["version"]=="1.26.5"


def test_protected_workflows_build_all_provider_app_images_before_publication():
    for workflow in ("validate.yml", "release.yml"):
        source=(ROOT/".github"/"workflows"/workflow).read_text(encoding="utf-8")
        assert "Build provider App images" in source
        assert "docker build" in source
        for app in APPS.values():
            assert app.name in source
