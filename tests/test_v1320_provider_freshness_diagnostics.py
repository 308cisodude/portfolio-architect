"""v1.35.2 provider freshness and diagnostics foundation regressions."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
TR_SRC = (
    ROOT
    / "home_assistant_app"
    / "portfolio_architect_gateway_trade_republic"
    / "src"
    / "portfolio_architect_gateway"
)
COMDIRECT_SRC = (
    ROOT
    / "home_assistant_app"
    / "portfolio_architect_gateway"
    / "src"
    / "portfolio_architect_gateway"
)

_freshness_spec = importlib.util.spec_from_file_location(
    "portfolio_architect_freshness_v1320", COMPONENT / "freshness.py"
)
assert _freshness_spec is not None and _freshness_spec.loader is not None
freshness = importlib.util.module_from_spec(_freshness_spec)
_freshness_spec.loader.exec_module(freshness)


def _load_tr_package():
    package_name = "portfolio_architect_gateway_tr_v1320_test"
    spec = importlib.util.spec_from_file_location(
        package_name,
        TR_SRC / "__init__.py",
        submodule_search_locations=[str(TR_SRC)],
    )
    assert spec is not None and spec.loader is not None
    package = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = package
    spec.loader.exec_module(package)
    app = __import__(f"{package_name}.trade_republic_app", fromlist=["*"])
    statement = __import__(f"{package_name}.trade_republic_statement", fromlist=["*"])
    server = __import__(f"{package_name}.server", fromlist=["*"])
    runtime = __import__(f"{package_name}.runtime_config", fromlist=["*"])
    return app, statement, server, runtime


def test_live_three_source_topology_identifies_only_dkb_csv_as_stale() -> None:
    rows = freshness.source_freshness_rows(
        (
            {
                "source_id": "comdirect",
                "provider": "comdirect",
                "label": "Comdirect",
                "generated_at": "2026-08-17T20:38:51+00:00",
            },
            {
                "source_id": "trade_republic",
                "provider": "trade_republic",
                "label": "Trade Republic",
                "generated_at": "2026-08-13T06:11:11+00:00",
            },
            {
                "source_id": "dkb_1",
                "provider": "dkb_csv",
                "label": "DKB CSV",
                "generated_at": "2026-07-31T00:00:00+00:00",
            },
        ),
        now=datetime(2026, 8, 17, 21, 6, 33, tzinfo=timezone.utc),
        threshold_hours=168,
    )
    assert [item["evidence_kind"] for item in rows] == [
        "live_api",
        "imported_statement",
        "imported_csv",
    ]
    blockers = freshness.stale_rows(rows)
    assert tuple(item["source_id"] for item in blockers) == ("dkb_1",)
    assert freshness.stale_summary(blockers) == (
        "DKB CSV · 17.9 days old · limit 7 days"
    )
    assert freshness.stale_summary(blockers, german=True) == (
        "DKB CSV · 17,9 Tage alt · Grenze 7 Tage"
    )


def test_future_or_invalid_source_timestamp_fails_observability_closed() -> None:
    rows = freshness.source_freshness_rows(
        (
            {
                "source_id": "future",
                "provider": "trade_republic",
                "label": "Future source",
                "generated_at": "2026-08-18T23:00:00+00:00",
            },
            {
                "source_id": "invalid",
                "provider": "dkb_csv",
                "label": "Invalid source",
                "generated_at": "not-a-time",
            },
        ),
        now=datetime(2026, 8, 17, 21, 0, tzinfo=timezone.utc),
        threshold_hours=168,
    )
    assert [item["timestamp_status"] for item in rows] == ["future", "invalid"]
    assert all(item["within_age_threshold"] is False for item in rows)


def test_coordinator_preserves_v132_source_evidence_and_fail_closed_actionability_surface() -> None:
    source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    assert 'if self.data is None or not self.is_data_fresh()' in source
    assert 'return "data_stale"' in source
    assert "source_freshness_evidence" in source
    assert "stale_source_summary" in source
    assert "plan_actionability_detail" in source


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_native_dashboards_surface_the_actual_freshness_blocker() -> None:
    for language, freshness_attr, plan_attr in (
        ("en", "stale_source_summary", "plan_actionability_detail"),
        ("de", "stale_source_summary_de", "plan_actionability_detail_de"),
    ):
        runtime = yaml.safe_load(
            (ROOT / "dashboard" / language / "runtime-health.yaml").read_text()
        )
        off_cards = [
            item["card"]
            for item in _walk(runtime)
            if item.get("type") == "conditional"
            and any(
                condition.get("entity") == "binary_sensor.portfolio_architect_data_fresh"
                and condition.get("state") == "off"
                for condition in item.get("conditions", [])
            )
        ]
        assert len(off_cards) == 1
        assert off_cards[0]["state_content"] == freshness_attr

        plan = yaml.safe_load(
            (ROOT / "dashboard" / language / "monthly-investment-plan.yaml").read_text()
        )
        unavailable = [
            item["card"]
            for item in _walk(plan)
            if item.get("type") == "conditional"
            and any(
                condition.get("entity") == "sensor.portfolio_architect_execution_state"
                and condition.get("state") == "unavailable"
                for condition in item.get("conditions", [])
            )
        ]
        assert len(unavailable) == 1
        assert unavailable[0]["state_content"] == plan_attr


def test_tr_persists_only_allowlisted_private_import_diagnostics(tmp_path: Path) -> None:
    app, statement, server_module, runtime = _load_tr_package()
    data = tmp_path / "gateway"
    data.mkdir()
    config = runtime.ServerConfig(
        bind="127.0.0.1",
        port=0,
        api_token_file=data / "gateway-api-token",
        snapshot_file=data / "portfolio.json",
        max_cached_snapshot_age_seconds=604800,
        tls_cert_file=None,
        tls_key_file=None,
        health_endpoint_enabled=True,
    )
    provider = statement.TradeRepublicStatementProvider(config.snapshot_file)
    state = server_module.GatewayState(config, provider)
    ingress = app.TradeRepublicIngressServer(
        ("127.0.0.1", 0),
        state=state,
        provider=provider,
        provider_name="Trade Republic",
        api_token="g" * 64,
        allowed_sources=frozenset({"127.0.0.1"}),
        require_user_header=False,
    )
    try:
        secret = "DE02120300000000202020 PRIVATE PERSON"
        public = app._public_statement_error(statement.StatementImportError(secret))
        assert secret not in public
        assert public == "Statement rejected by the bounded import parser"
        ingress.record_import_diagnostic("rejected", f"Statement rejected: {public}")
        stored = json.loads(ingress.import_diagnostic_file.read_text(encoding="utf-8"))
        assert stored["outcome"] == "rejected"
        assert secret not in repr(stored)
        assert "raw" not in repr(stored).lower()
        assert os.stat(ingress.import_diagnostic_file).st_mode & 0o777 == 0o600
        assert ingress.import_diagnostic()["message"] == (
            "Statement rejected: Statement rejected by the bounded import parser"
        )

        # Even a corrupted/tampered App-private state file must never be echoed back.
        ingress.import_diagnostic_file.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "recorded_at": "2026-08-17T21:00:00+00:00",
                    "outcome": "rejected",
                    "message": f"Statement rejected: {secret}",
                }
            ),
            encoding="utf-8",
        )
        corrupted = ingress.import_diagnostic()
        assert corrupted == {
            "outcome": "internal_error",
            "message": "Stored import diagnostic is invalid.",
            "recorded_at": "unknown",
        }
        assert secret not in repr(corrupted)
        ingress.server_close()

        reopened = app.TradeRepublicIngressServer(
            ("127.0.0.1", 0),
            state=state,
            provider=provider,
            provider_name="Trade Republic",
            api_token="g" * 64,
            allowed_sources=frozenset({"127.0.0.1"}),
            require_user_header=False,
        )
        try:
            assert reopened.import_diagnostic()["outcome"] == "internal_error"
            reopened.record_import_diagnostic(
                "accepted", "Statement accepted: 1 positions; snapshot timestamp 2026-08-17T21:00:00+00:00."
            )
            assert reopened.import_diagnostic()["outcome"] == "accepted"
            assert secret not in reopened.import_diagnostic_file.read_text(encoding="utf-8")
        finally:
            reopened.server_close()
        ingress = None
    finally:
        if ingress is not None:
            ingress.server_close()


def test_tr_does_not_fingerprint_private_pdf_and_comdirect_keeps_bounded_runtime_errors() -> None:
    tr_source = (TR_SRC / "trade_republic_app.py").read_text(encoding="utf-8")
    assert "sha256" not in tr_source.lower()
    assert "save_json_state" in tr_source
    assert "_public_statement_error" in tr_source

    server_source = (COMDIRECT_SRC / "server.py").read_text(encoding="utf-8")
    app_source = (COMDIRECT_SRC / "app.py").read_text(encoding="utf-8")
    comdirect_source = (COMDIRECT_SRC / "comdirect.py").read_text(encoding="utf-8")
    assert "Publish one sanitized refresh failure without retaining remote content" in server_source
    assert "self._last_error = error_code" in server_source
    assert '_LOGGER.warning("Portfolio refresh failed: %s", type(err).__name__)' in server_source
    assert 'self.send_header("Location", "./")' in app_source
    assert "Comdirect refresh session rejected: reason=%s" in comdirect_source
    assert "err.response" not in comdirect_source


def test_provider_diagnostics_policy_is_explicit_and_provider_specific() -> None:
    policy = (ROOT / "docs" / "PROVIDER-DIAGNOSTICS.md").read_text(encoding="utf-8")
    for phrase in (
        "classified evidence",
        "App-private",
        "raw upstream",
        "Trade Republic",
        "Comdirect",
        "DKB",
        "Ingress",
        "successful operation",
    ):
        assert phrase in policy
