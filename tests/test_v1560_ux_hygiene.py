"""v1.56.0 UX, discovery-lifecycle, and presentation hygiene contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "home_assistant_app"
DKB = APPS / "portfolio_architect_gateway_dkb"
GENERIC = APPS / "portfolio_architect_gateway_import"


def test_v156_version_alignment_and_security_non_goals() -> None:
    manifest = json.loads((ROOT / "custom_components/portfolio_architect/manifest.json").read_text())
    assert manifest["version"] == "1.56.0"
    for slug in (
        "portfolio_architect_gateway",
        "portfolio_architect_gateway_comdirect",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
        "portfolio_architect_gateway_import",
    ):
        assert yaml.safe_load((APPS / slug / "config.yaml").read_text())["version"] == "1.56.0"
    dkb_source = (DKB / "src/portfolio_architect_gateway/dkb_app.py").read_text()
    assert "Authenticated FinTS acquisition is not enabled" in dkb_source
    assert "cannot replace or fall back from CSV evidence" in dkb_source


def test_dkb_probe_time_is_server_rendered_for_berlin_and_utc() -> None:
    source = (DKB / "src/portfolio_architect_gateway/dkb_app.py").read_text()
    dockerfile = (DKB / "Dockerfile").read_text()
    assert 'BERLIN_TIMEZONE: Final = ZoneInfo("Europe/Berlin")' in source
    assert "Intl.DateTimeFormat" not in source
    assert "probe-time.js" not in source
    assert "Last probe sent · Europe/Berlin" in source
    assert "Authoritative server-side dispatch timestamp · UTC" in source
    assert "apk add --no-cache openssl tzdata" in dockerfile

    env = os.environ.copy()
    env["PYTHONPATH"] = str(DKB / "src")
    code = """
from portfolio_architect_gateway.dkb_app import _probe_timestamp_display
summer, summer_utc = _probe_timestamp_display('2026-08-28T14:16:38+00:00')
winter, winter_utc = _probe_timestamp_display('2026-01-28T14:16:38+00:00')
assert summer == '2026-08-28T16:16:38+02:00 (CEST)'
assert summer_utc == '2026-08-28T14:16:38+00:00'
assert winter == '2026-01-28T15:16:38+01:00 (CET)'
assert winter_utc == '2026-01-28T14:16:38+00:00'
"""
    subprocess.run([sys.executable, "-c", code], check=True, env=env, cwd=ROOT)


def test_generic_import_hides_token_low_and_tracks_exact_discovery_uuid(tmp_path: Path) -> None:
    ui = (GENERIC / "src/portfolio_architect_gateway/generic_import_app.py").read_text()
    entrypoint = (GENERIC / "entrypoint.py").read_text()
    assert ui.index("Import mapped CSV") < ui.index("Sensitive connection material") < ui.index("Bearer token")
    assert "<details><summary>Show bearer token</summary>" in ui
    assert 'DISCOVERY_UUID_FILE = DATA / "generic-import-discovery-uuid"' in entrypoint
    assert "delete_supervisor_tls_discovery" in entrypoint
    assert "skipping duplicate discovery publication" in entrypoint
    assert "signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)" in entrypoint
    assert "on_published=lifecycle.record_published" in entrypoint
    assert "stop_event=lifecycle.stop_event" in entrypoint

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(GENERIC), str(GENERIC / "src")))
    state_file = tmp_path / "discovery-uuid"
    code = f"""
from pathlib import Path
import entrypoint as module
calls=[]
module.delete_supervisor_tls_discovery=lambda value: calls.append(value)
path=Path({str(state_file)!r})
lifecycle=module._GenericDiscoveryLifecycle(path)
uuid='a'*32
lifecycle.record_published(uuid)
assert path.read_text(encoding='ascii').strip()==uuid
assert oct(path.stat().st_mode & 0o777)=='0o600'
assert lifecycle.reconcile_before_publish() is True
assert calls==[uuid]
assert not path.exists()
lifecycle.record_published(uuid)
lifecycle.cleanup()
assert calls==[uuid, uuid]
assert not path.exists()
"""
    subprocess.run([sys.executable, "-c", code], check=True, env=env, cwd=ROOT)


def test_supervisor_discovery_delete_is_exact_and_bounded() -> None:
    source = (ROOT / "gateway/src/portfolio_architect_gateway/supervisor_tls.py").read_text()
    assert 'f"/discovery/{discovery_uuid}"' in source
    assert 're.fullmatch(r"[0-9a-f]{32}", discovery_uuid)' in source
    assert '"DELETE"' in source
    assert "Supervisor discovery identifier is invalid" in source


def test_comdirect_display_identity_is_canonical_without_new_marker() -> None:
    legacy = yaml.safe_load((APPS / "portfolio_architect_gateway/config.yaml").read_text())
    canonical = yaml.safe_load((APPS / "portfolio_architect_gateway_comdirect/config.yaml").read_text())
    assert legacy["slug"] == "portfolio_architect_gateway"
    assert canonical["slug"] == "portfolio_architect_gateway_comdirect"
    assert legacy["name"] == "Portfolio Architect Gateway — Comdirect LEGACY"
    assert legacy["stage"] == "deprecated"
    assert canonical["name"] == "Portfolio Architect Gateway — Comdirect"
    assert canonical["panel_title"] == "Portfolio Gateway — Comdirect"
    assert "NEW" not in canonical["name"]
    assert "NEW" not in canonical["panel_title"]


def test_runtime_health_dashboard_has_one_incident_and_one_lkg_presentation() -> None:
    for lang in ("en", "de"):
        doc = yaml.safe_load((ROOT / f"dashboard/{lang}/runtime-health.yaml").read_text())
        cards = [item.get("card", item) for item in doc["cards"]]
        incident = [c for c in cards if c.get("entity") == "binary_sensor.portfolio_architect_gateway_attention_required"]
        lkg = [c for c in cards if c.get("entity") == "binary_sensor.portfolio_architect_gateway_using_last_known_good_snapshot"]
        assert len(incident) == 1
        assert len(lkg) == 1
        assert incident[0]["state_content"] == (
            ["attention_reason", "recommended_action"]
            if lang == "en"
            else ["attention_reason_de", "recommended_action_de"]
        )
        assert lkg[0]["state_content"] == ["snapshot_age_seconds", "snapshot_expires_in_seconds"]
        entities = [c.get("entity") for c in cards]
        assert "binary_sensor.portfolio_architect_gateway_reauthentication_required" not in entities
        assert "sensor.portfolio_architect_gateway_attention_reason" not in entities
        assert "sensor.portfolio_architect_gateway_recommended_action" not in entities


def test_routine_ingress_polling_logs_are_debug_only() -> None:
    sources = {
        ROOT / "gateway/src/portfolio_architect_gateway/app.py": "Ingress request completed",
        ROOT / "gateway/src/portfolio_architect_gateway/pending_app.py": "Provider shell Ingress request completed",
        DKB / "src/portfolio_architect_gateway/dkb_app.py": "DKB Gateway Ingress request completed",
    }
    for path, message in sources.items():
        source = path.read_text()
        assert f'_LOGGER.debug("{message}")' in source
        assert f'_LOGGER.info("{message}")' not in source


def test_sbom_records_dkb_timezone_runtime_dependency() -> None:
    sbom = json.loads((ROOT / "SBOM.spdx.json").read_text())
    assert sbom["name"] == "Portfolio Architect v1.56.0 SBOM"
    tzdata = next(pkg for pkg in sbom["packages"] if pkg["SPDXID"] == "SPDXRef-Package-Tzdata")
    assert tzdata["versionInfo"] == "build-resolved"
    assert any(ref["referenceLocator"] == "pkg:apk/alpine/tzdata" for ref in tzdata["externalRefs"])


def test_legacy_comdirect_final_release_warns_before_v157_withdrawal() -> None:
    legacy_ui = (APPS / "portfolio_architect_gateway/src/portfolio_architect_gateway/app.py").read_text()
    legacy_docs = (APPS / "portfolio_architect_gateway/DOCS.md").read_text()
    release_notes = (ROOT / "docs/RELEASE-NOTES.md").read_text()
    roadmap = (ROOT / "docs/ROADMAP.md").read_text()
    assert "Final legacy release." in legacy_ui
    assert "scheduled to be withdrawn from the App repository in v1.57.0" in legacy_ui
    assert "final published release" in legacy_docs
    assert "stage: deprecated" in legacy_docs
    assert "active App repository is scheduled to withdraw `portfolio_architect_gateway` in v1.57.0" in release_notes
    assert "Historical Comdirect App withdrawal (v1.57.0)" in roadmap
