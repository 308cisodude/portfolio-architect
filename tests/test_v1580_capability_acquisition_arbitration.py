"""v1.61.2 capability-level acquisition arbitration contracts."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
GATEWAY_SRC = ROOT / "gateway" / "src"
if str(GATEWAY_SRC) not in sys.path:
    sys.path.insert(0, str(GATEWAY_SRC))

from portfolio_architect_gateway.acquisition_control import (  # noqa: E402
    AUTHORITY_ACTIVE_METHOD,
    CAPABILITY_CASH,
    CAPABILITY_HOLDINGS,
    METHOD_READY,
    METHOD_RESEARCH_ONLY,
    AcquisitionControl,
    AcquisitionMethod,
    capability,
)
from portfolio_architect_gateway.errors import ConfigurationError  # noqa: E402


def test_v1580_versions_and_health_schema9_are_aligned() -> None:
    assert json.loads((COMPONENT / "manifest.json").read_text())["version"] == "1.61.2"
    assert 'VERSION: Final = "1.61.2"' in (COMPONENT / "const.py").read_text()
    for slug in (
        "portfolio_architect_gateway_comdirect",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
        "portfolio_architect_gateway_import",
    ):
        cfg = yaml.safe_load((ROOT / "home_assistant_app" / slug / "config.yaml").read_text())
        assert cfg["version"] == "1.61.2"
    rest = (COMPONENT / "rest_client.py").read_text()
    server = (GATEWAY_SRC / "portfolio_architect_gateway/server.py").read_text()
    assert "HEALTH_V9_MEDIA_TYPE" in rest
    assert '"requested_health_schema_version": 9' in rest
    assert "HEALTH_V9_MEDIA_TYPE" in server
    assert '"health_schema_version": min(version, 9)' in server
    assert "include_capabilities=version >= 9" in server


def test_capability_authority_is_bounded_explicit_and_never_automatic_fallback() -> None:
    control = AcquisitionControl(
        active_method="live_api",
        methods=(
            AcquisitionMethod("live_api", METHOD_READY, True, True),
            AcquisitionMethod("csv", METHOD_READY, False, True),
        ),
        capabilities=(
            capability(CAPABILITY_HOLDINGS, "live_api", "live_api", "csv"),
            capability(CAPABILITY_CASH, "live_api", "live_api", "csv"),
        ),
    )
    health8 = control.as_health_fields(include_capabilities=False)
    health9 = control.as_health_fields(include_capabilities=True)
    assert "acquisition_capabilities" not in health8
    assert health9["acquisition_capabilities"][0]["authoritative_method"] == "live_api"
    assert all(item["fallback_policy"] == "none" for item in health9["acquisition_capabilities"])

    with pytest.raises(ConfigurationError, match="authority method must be ready"):
        AcquisitionControl(
            active_method="csv",
            methods=(
                AcquisitionMethod("csv", METHOD_READY, True, True),
                AcquisitionMethod("fints", METHOD_RESEARCH_ONLY, False, False),
            ),
            capabilities=(
                capability(
                    CAPABILITY_HOLDINGS,
                    "fints",
                    "csv",
                    "fints",
                    authority_reason=AUTHORITY_ACTIVE_METHOD,
                ),
            ),
        )


def test_official_provider_authorities_match_v157_live_baseline_and_fail_closed() -> None:
    comdirect = (GATEWAY_SRC / "portfolio_architect_gateway/acquisition.py").read_text()
    dkb = (ROOT / "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway/dkb_csv.py").read_text()
    tr = (ROOT / "home_assistant_app/portfolio_architect_gateway_trade_republic/src/portfolio_architect_gateway/trade_republic_statement.py").read_text()
    generic = (ROOT / "home_assistant_app/portfolio_architect_gateway_import/src/portfolio_architect_gateway/generic_csv.py").read_text()
    assert "CAPABILITY_HOLDINGS" in comdirect and "CAPABILITY_CASH" in comdirect
    assert "MODE_LIVE_API, MODE_CSV" in comdirect
    assert "AUTHORITY_ACTIVE_METHOD" in comdirect
    assert 'authoritative_method="csv"' not in comdirect
    assert 'AcquisitionMethod("fints", METHOD_RESEARCH_ONLY, False, False)' in dkb
    assert 'CAPABILITY_HOLDINGS,\n                    "csv"' in dkb
    assert 'CAPABILITY_CASH,\n                    "csv"' in dkb
    assert 'AcquisitionMethod("live_api", METHOD_UNAVAILABLE, False, False)' in tr
    assert 'CAPABILITY_HOLDINGS,\n                    "pdf"' in tr
    assert 'CAPABILITY_CASH,\n                    "pdf"' in tr
    assert 'single_method_control("csv", cash=False)' in generic


def test_pa_exposes_capability_authority_read_only_and_release_scope_stays_bounded() -> None:
    rest = (COMPONENT / "rest_client.py").read_text()
    sensor = (COMPONENT / "sensor.py").read_text()
    diagnostics = (COMPONENT / "diagnostics.py").read_text()
    notes = (ROOT / "docs/RELEASE-NOTES.md").read_text().lower() if (ROOT / "docs/RELEASE-NOTES.md").exists() else ""
    assert "GatewayAcquisitionCapability" in rest
    assert '"acquisition_capabilities"' in rest
    assert '"acquisition_capabilities"' in sensor
    assert '"acquisition_capabilities"' in diagnostics
    assert "set_acquisition" not in rest
    if notes:
        assert "no silent fallback" in notes
        assert "authenticated dkb fints" in notes and "remains disabled" in notes
        assert "no trading" in notes
