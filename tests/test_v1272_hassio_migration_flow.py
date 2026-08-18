"""Regression contracts for v1.35.0 Supervisor HTTPS migration flow eligibility."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def _step(source: str, name: str, next_name: str) -> str:
    return source.split(f"async def {name}", 1)[1].split(f"async def {next_name}", 1)[0]


def test_manifest_does_not_block_hassio_discovery_for_existing_entry() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    assert "single_config_entry" not in manifest
    assert manifest["config_flow"] is True


def test_manual_user_setup_remains_fail_closed_single_instance() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    user_step = _step(source, "async_step_user", "async_step_reconfigure")
    assert "self.hass.config_entries.async_entries(DOMAIN)" in user_step
    assert 'return self.async_abort(reason="already_configured")' in user_step
    assert "await self.async_set_unique_id(INSTANCE_UNIQUE_ID)" in user_step
    assert "self._abort_if_unique_id_configured()" in user_step
    assert user_step.index("async_entries(DOMAIN)") < user_step.index("async_set_unique_id")


def test_hassio_flow_can_target_exactly_one_existing_entry_and_migrate_https() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    hassio_step = _step(source, "async_step_hassio", "async_step_hassio_confirm")
    assert "entries = self.hass.config_entries.async_entries(DOMAIN)" in hassio_step
    assert "if len(entries) != 1:" in hassio_step
    assert 'return self.async_abort(reason="tls_discovery_not_applicable")' in hassio_step
    assert "return await self._async_migrate_primary_tls(entry, discovery)" in hassio_step
    assert "return await self._async_migrate_supplemental_tls(" in hassio_step


def test_discovery_does_not_offer_duplicate_provider_scope() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    hassio_step = _step(source, "async_step_hassio", "async_step_hassio_confirm")
    assert "if source.provider_id != discovery.provider_id:" in hassio_step
    assert "if not discovery.matches_legacy_endpoint(source.endpoint_url):" in hassio_step
    assert "gateway_provider_conflicts_with_dkb_csv(" in hassio_step
    assert "raw_dkb_sources" in hassio_step


def test_verified_https_before_write_and_no_plaintext_fallback_are_unchanged() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    primary = _step(source, "_async_migrate_primary_tls", "_async_migrate_supplemental_tls")
    assert primary.index("await async_fetch_gateway_health") < primary.index("async_update_entry")
    assert 'reason="tls_validation_failed"' in primary
    rest = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    assert "ssl=False" not in rest
    assert "verify=False" not in rest
