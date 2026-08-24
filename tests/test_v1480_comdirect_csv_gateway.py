"""v1.48.0 complete Comdirect CSV acquisition and explicit arbitration."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway"
PACKAGE = APP / "src" / "portfolio_architect_gateway"
FIXTURE = ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv"
TEST_PACKAGE = "portfolio_architect_gateway_comdirect_v1480_test"


def _load_modules():
    if TEST_PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            TEST_PACKAGE,
            PACKAGE / "__init__.py",
            submodule_search_locations=[str(PACKAGE)],
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[TEST_PACKAGE] = module
        spec.loader.exec_module(module)
    return (
        importlib.import_module(f"{TEST_PACKAGE}.comdirect_csv"),
        importlib.import_module(f"{TEST_PACKAGE}.comdirect_cash_csv"),
        importlib.import_module(f"{TEST_PACKAGE}.acquisition"),
        importlib.import_module(f"{TEST_PACKAGE}.cash_policy"),
        importlib.import_module(f"{TEST_PACKAGE}.store"),
    )


def _cash_csv(balance: str = "1.165,44 EUR", *, opening: str = "1.200,00 EUR", delta: str = "-34,56") -> bytes:
    # Sanitized shape of the live-proven Comdirect Girokonto export: title/current
    # balance above the table and old balance as a footer after the transactions.
    text = (
        '\r\n'
        '"Umsätze Girokonto";"Zeitraum: 10 Tage";\r\n'
        f'"Neuer Kontostand";"{balance}";\r\n'
        '\r\n'
        '"Buchungstag";"Wertstellung (Valuta)";"Vorgang";"Buchungstext";"Umsatz in EUR";\r\n'
        f'"23.08.2026";"23.08.2026";"Übertrag / Überweisung";"Synthetic transaction";"{delta}";\r\n'
        '\r\n'
        f'"Alter Kontostand";"{opening}";\r\n'
        '\r\n'
    )
    return text.encode("cp1252")


def test_gateway_holdings_parser_preserves_established_comdirect_fixture() -> None:
    holdings, _cash, _acquisition, _policy, _store = _load_modules()
    now = datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc)
    snapshot = holdings.parse_comdirect_holdings_csv(FIXTURE.read_bytes(), now=now)
    assert snapshot.generated_at == now
    assert len(snapshot.positions) == 13
    first = snapshot.positions[0]
    assert first.identifier == "A1XB5U"
    assert first.isin == "IE00BJ0KDQ92"
    assert first.market_value_eur == Decimal("5000.00")
    assert first.instrument_type == "ETF"


def test_cash_csv_requires_explicit_closing_balance_and_never_sums_transactions() -> None:
    _holdings, cash, _acquisition, policy, _store = _load_modules()
    now = datetime(2026, 8, 24, 8, 1, tzinfo=timezone.utc)
    snapshot = cash.parse_comdirect_cash_csv(_cash_csv(), now=now)
    assert snapshot.account_balance_eur == Decimal("1165.44")
    assert snapshot.as_of == now
    investment_cash = snapshot.investment_cash(policy.InvestmentCashPolicy())
    assert investment_cash.eligible_eur == Decimal("1165.44")
    assert investment_cash.authorized_eur == Decimal("1165.44")
    without_balance = _cash_csv().replace(b'"Neuer Kontostand";"1.165,44 EUR";\r\n', b"")
    with pytest.raises(cash.ComdirectCashCsvImportError, match="explicit closing balance"):
        cash.parse_comdirect_cash_csv(without_balance, now=now)


def test_negative_static_balance_never_authorizes_credit() -> None:
    _holdings, cash, _acquisition, policy, _store = _load_modules()
    negative = _cash_csv("-42,00 EUR", opening="100,00 EUR", delta="-142,00")
    snapshot = cash.parse_comdirect_cash_csv(negative)
    investment_cash = snapshot.investment_cash(policy.InvestmentCashPolicy())
    assert investment_cash.account_balance_eur == Decimal("-42.00")
    assert investment_cash.eligible_eur == Decimal("0")
    assert investment_cash.authorized_eur == Decimal("0")


def test_cash_csv_rejects_non_reconciling_export() -> None:
    _holdings, cash, _acquisition, _policy, _store = _load_modules()
    broken = _cash_csv(delta="-34,57")
    with pytest.raises(cash.ComdirectCashCsvImportError, match="do not reconcile"):
        cash.parse_comdirect_cash_csv(broken)


class _LiveClient:
    provider_id = "comdirect"
    poll_interval_seconds = 900

    def __init__(self, snapshot, *, fail: bool = False):
        self.snapshot = snapshot
        self.fail = fail
        self.calls = 0
        self.maintenance_calls = 0

    def fetch_snapshot(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("synthetic live failure")
        return self.snapshot

    def run_session_maintenance_iteration(self):
        self.maintenance_calls += 1
        return False


def test_arbitration_never_cross_falls_back(tmp_path: Path) -> None:
    holdings, cash, acquisition, policy, _store = _load_modules()
    imported_at = datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc)
    static_holdings = holdings.parse_comdirect_holdings_csv(FIXTURE.read_bytes(), now=imported_at)
    live = _LiveClient(static_holdings, fail=True)
    policy_file = tmp_path / "policy.json"
    provider = acquisition.ComdirectAcquisitionProvider(live, tmp_path, policy_file)
    provider.persist_holdings(static_holdings)
    provider.persist_cash(cash.parse_comdirect_cash_csv(_cash_csv(), now=imported_at))

    assert provider.acquisition_mode == "live_api"
    with pytest.raises(RuntimeError, match="synthetic live failure"):
        provider.fetch_snapshot()
    assert live.calls == 1

    live.fail = False
    provider.set_mode("csv")
    calls_before = live.calls
    snapshot = provider.fetch_snapshot()
    assert live.calls == calls_before
    assert snapshot.investment_cash is not None
    assert snapshot.investment_cash.authorized_eur == Decimal("1165.44")


def test_mode_switch_requires_valid_requested_source_and_persists(tmp_path: Path) -> None:
    holdings, _cash, acquisition, _policy, _store = _load_modules()
    static_holdings = holdings.parse_comdirect_holdings_csv(FIXTURE.read_bytes())
    live = _LiveClient(static_holdings)
    provider = acquisition.ComdirectAcquisitionProvider(live, tmp_path, tmp_path / "policy.json")
    with pytest.raises(Exception, match="No Comdirect depot CSV"):
        provider.set_mode("csv")
    assert provider.acquisition_mode == "live_api"
    provider.persist_holdings(static_holdings)
    provider.set_mode("csv")
    restored = acquisition.ComdirectAcquisitionProvider(live, tmp_path, tmp_path / "policy.json")
    assert restored.acquisition_mode == "csv"


def test_comdirect_ingress_visually_separates_live_and_static_acquisition() -> None:
    source = (PACKAGE / "app.py").read_text(encoding="utf-8")
    assert "Live acquisition · Comdirect API" in source
    assert "Static acquisition · Comdirect CSV" in source
    assert "live-card" in source and "static-card" in source
    assert "Import holdings CSV" in source
    assert "Import cash CSV" in source
    assert "Activate static CSV mode" in source
    assert "never falls back" in source
    assert "Automatic API polling and OAuth session maintenance are disabled" in source


def test_health_schema_7_exposes_bounded_acquisition_mode() -> None:
    server = (PACKAGE / "server.py").read_text(encoding="utf-8")
    rest = (ROOT / "custom_components" / "portfolio_architect" / "rest_client.py").read_text(encoding="utf-8")
    assert "HEALTH_V7_MEDIA_TYPE" in server
    assert 'document["acquisition_mode"]' in server
    assert "HEALTH_V7_MEDIA_TYPE" in rest
    assert 'v7_fields = v6_fields | {"acquisition_mode"}' in rest

def test_all_provider_ingress_pages_optically_separate_live_and_static_acquisition() -> None:
    dkb = (ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb" / "src" / "portfolio_architect_gateway" / "dkb_app.py").read_text(encoding="utf-8")
    tr = (ROOT / "home_assistant_app" / "portfolio_architect_gateway_trade_republic" / "src" / "portfolio_architect_gateway" / "trade_republic_app.py").read_text(encoding="utf-8")
    for source in (dkb, tr):
        assert "static-card" in source
        assert "live-card" in source
        assert "Static acquisition" in source
        assert "Live acquisition" in source
    assert "UNAVAILABLE · RESEARCH ONLY" in dkb
    assert "authenticated DKB FinTS acquisition remains disabled" in dkb
    assert "UNAVAILABLE" in tr
    assert "No supported Trade Republic live/private API acquisition is used" in tr


def _load_freshness_module():
    path = ROOT / "custom_components" / "portfolio_architect" / "freshness.py"
    name = "portfolio_architect_v1480_freshness_test"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_comdirect_static_evidence_uses_csv_freshness_class() -> None:
    freshness = _load_freshness_module()
    assert freshness.evidence_kind("comdirect", "live_api") == "live_api"
    assert freshness.cash_evidence_kind("comdirect", "live_api") == "live_api"
    assert freshness.evidence_kind("comdirect", "csv") == "csv"
    assert freshness.cash_evidence_kind("comdirect", "csv") == "csv"
    rows = freshness.source_freshness_rows(
        (
            {
                "source_id": "primary",
                "provider": "comdirect",
                "label": "Comdirect",
                "acquisition_mode": "csv",
                "generated_at": "2026-08-24T08:00:00+00:00",
            },
        ),
        now=datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc),
        threshold_hours=1,
        threshold_hours_by_kind={"csv": 24, "live_api": 1},
    )
    assert rows[0]["evidence_kind"] == "csv"
    assert rows[0]["threshold_hours"] == 24
    assert rows[0]["within_age_threshold"] is True


def test_new_pa_setup_no_longer_offers_legacy_comdirect_csv_but_bridge_remains() -> None:
    flow = (ROOT / "custom_components" / "portfolio_architect" / "config_flow.py").read_text(
        encoding="utf-8"
    )
    new_provider_block = flow.split("_NEW_SOURCE_PROVIDERS = (", 1)[1].split(")", 1)[0]
    assert "PROVIDER_COMDIRECT" not in new_provider_block
    assert "PROVIDER_GENERIC_CSV" in new_provider_block
    assert "PROVIDER_LOCAL_REST_JSON" in new_provider_block
    assert "async_step_hassio_migrate_comdirect_csv_confirm" in flow
    migration = flow.split("async def async_step_hassio_migrate_comdirect_csv_confirm", 1)[1].split(
        "async def async_step_hassio_add_supplemental_confirm", 1
    )[0]
    assert "health.health_schema_version < 7" in migration
    assert 'health.acquisition_mode != "csv"' in migration
    assert "legacy_positions != snapshot.positions" in migration
    assert "async_update_entry" in migration
    assert "async_reload" in migration
    assert "st_mtime" not in migration
    assert "stat().st_mtime" not in migration


def test_bilingual_comdirect_migration_bridge_is_explained_fail_closed() -> None:
    import json

    for language in ("en", "de"):
        data = json.loads(
            (ROOT / "custom_components" / "portfolio_architect" / "translations" / f"{language}.json").read_text(
                encoding="utf-8"
            )
        )
        assert "hassio_migrate_comdirect_csv_confirm" in data["config"]["step"]
        assert "comdirect_gateway_migration_mismatch" in data["config"]["error"]
        assert "comdirect_gateway_migrated" in data["config"]["abort"]
