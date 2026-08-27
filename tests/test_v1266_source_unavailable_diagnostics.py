"""Regression contracts for v1.26.6 unavailable-source diagnostics."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from presentation import unavailable_source_summary  # noqa: E402


def _unavailable_source_property_source() -> str:
    source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    return source.split("    def unavailable_source_ids", 1)[1].split(
        "    @property\n    def unavailable_source_count", 1
    )[0]


def test_primary_reauthentication_is_named_without_home_assistant_lkg_gate() -> None:
    """Reachable Gateway-local LKG must still identify the primary source."""
    body = _unavailable_source_property_source()
    assert "self.source_type == SOURCE_TYPE_REST_API" in body
    assert '_gateway_health_operating_mode(health) != "live"' in body
    # Gateway-local non-live state remains independently sufficient; v1.54.0 also
    # attributes a PA-local primary integrity rejection while HA LKG is active.
    assert "or primary_rejected_by_pa" in body
    assert 'missing.append(f"gateway:{provider_id or PROVIDER_LOCAL_REST_JSON}")' in body
    assert unavailable_source_summary(("gateway:comdirect",), german=False) == "Comdirect Gateway"
    assert unavailable_source_summary(("gateway:comdirect",), german=True) == "Comdirect-Gateway"


def test_non_live_supplemental_gateway_health_is_named_symmetrically() -> None:
    """The same invariant applies if an additional Gateway serves only cached data."""
    body = _unavailable_source_property_source()
    assert "self.supplemental_gateway_health.items()" in body
    assert '_gateway_health_operating_mode(health) == "live"' in body
    assert 'token = f"gateway:{provider_id}"' in body
    assert (
        unavailable_source_summary(("gateway:trade_republic",), german=False)
        == "Trade Republic Gateway"
    )


def test_existing_supplemental_error_and_file_source_collection_remains_present() -> None:
    body = _unavailable_source_property_source()
    assert "self.supplemental_gateway_health_errors" in body
    assert "self.supplemental_source_errors" in body
