"""v1.55.1 live-acceptance hotfix regression contracts."""

from __future__ import annotations

import ast
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


class _StripAnnotations(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef):  # noqa: N802
        node = copy.deepcopy(node)
        node.returns = None
        for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            arg.annotation = None
        if node.args.vararg is not None:
            node.args.vararg.annotation = None
        if node.args.kwarg is not None:
            node.args.kwarg.annotation = None
        return self.generic_visit(node)


def _extract_function(name: str):
    tree = ast.parse((COMPONENT / "coordinator.py").read_text(encoding="utf-8"))
    functions = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(functions) == 1
    function = _StripAnnotations().visit(functions[0])
    ast.fix_missing_locations(function)
    namespace = {"datetime": datetime}
    module = ast.Module(body=[function], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, "<v1531-coordinator-helper>", "exec"), namespace)
    return namespace[name]


def _health(**overrides):
    values = {
        "health_schema_version": 8,
        "active_acquisition_method": "csv",
        "previous_acquisition_method": "live_api",
        "last_acquisition_method_change_at": datetime(2026, 8, 25, 13, 0, 0, tzinfo=timezone.utc),
        "last_acquisition_method_change_reason": "operator",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_explicit_schema8_method_switch_opens_one_new_evidence_timeline() -> None:
    allowed = _extract_function("_explicit_acquisition_transition_allows_older_snapshot")
    accepted_at = datetime(2026, 8, 25, 12, 30, 0, tzinfo=timezone.utc)

    assert allowed(_health(), accepted_mode="live_api", accepted_generated_at=accepted_at)
    assert not allowed(
        _health(active_acquisition_method="live_api", previous_acquisition_method="csv"),
        accepted_mode="live_api",
        accepted_generated_at=accepted_at,
    )
    assert not allowed(
        _health(health_schema_version=7),
        accepted_mode="live_api",
        accepted_generated_at=accepted_at,
    )
    assert not allowed(
        _health(last_acquisition_method_change_reason="automatic"),
        accepted_mode="live_api",
        accepted_generated_at=accepted_at,
    )
    assert not allowed(
        _health(last_acquisition_method_change_at=accepted_at - timedelta(seconds=1)),
        accepted_mode="live_api",
        accepted_generated_at=accepted_at,
    )


def test_last_accepted_acquisition_mode_is_taken_from_source_summary() -> None:
    mode = _extract_function("_source_summary_acquisition_mode")
    summaries = (
        {"provider": "comdirect", "acquisition_mode": "live_api"},
        {"provider": "trade_republic", "acquisition_mode": "pdf"},
    )
    assert mode(summaries, "comdirect") == "live_api"
    assert mode(summaries, "trade_republic") == "pdf"
    assert mode(summaries, "dkb") is None


def test_primary_pa_integrity_rejection_is_attributed_to_primary_gateway() -> None:
    source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    body = source.split("    def unavailable_source_ids", 1)[1].split(
        "    @property\n    def unavailable_source_count", 1
    )[0]
    assert "primary_rejected_by_pa" in body
    assert "self._using_home_assistant_last_known_good" in body
    assert "self.rest_snapshot_integrity_error is not None" in body
    assert 'missing.append(f"gateway:{provider_id or PROVIDER_LOCAL_REST_JSON}")' in body


def test_supplemental_snapshot_unavailability_is_not_integrity_failure() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    rest = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    assert "class PortfolioRestUnavailableError" in rest
    assert "response.status == 503" in rest
    assert "raise PortfolioRestUnavailableError" in rest
    function = coordinator.split("async def _async_fetch_supplemental_rest_snapshots", 1)[1].split(
        "\n\nclass SupplementalPortfolioSourceError", 1
    )[0]
    assert 'if not health.snapshot_available:' in function
    assert 'errors[config.provider_id] = "snapshot_unavailable"' in function
    assert "except PortfolioRestUnavailableError:" in function
    assert 'failure == "integrity_error"' in coordinator


def test_static_gateway_retention_is_pa_freshness_owned() -> None:
    server = (ROOT / "gateway/src/portfolio_architect_gateway/server.py").read_text(encoding="utf-8")
    assert 'STATIC_ACQUISITION_METHODS = frozenset({"csv", "pdf"})' in server
    assert "def _effective_max_cached_snapshot_age_seconds" in server
    assert "if active_method in STATIC_ACQUISITION_METHODS:" in server
    assert "return 0" in server
    for app in (
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
        "portfolio_architect_gateway_import",
    ):
        text = (ROOT / "home_assistant_app" / app / "config.yaml").read_text(encoding="utf-8")
        # v1.55.1 removes the obsolete static user-facing option; v1.53.1's
        # server-side ownership rule remains the reason this is safe.
        assert "max_cached_snapshot_age_seconds" not in text


def test_v1531_does_not_change_gateway_health_or_portfolio_wire_schema() -> None:
    server = (ROOT / "gateway/src/portfolio_architect_gateway/server.py").read_text(encoding="utf-8")
    rest = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    assert '"health_schema_version": min(version, 9)' in server
    assert '"requested_health_schema_version": 9' in rest
    assert json.loads((COMPONENT / "manifest.json").read_text())["version"] == "1.59.0"
