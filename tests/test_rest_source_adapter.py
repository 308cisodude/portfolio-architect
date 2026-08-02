"""v1.4 local REST source-adapter contract tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine import calculate_portfolio_payload_from_positions  # noqa: E402
from engine.importers import CsvSourceConfig, PROVIDER_COMDIRECT, read_positions  # noqa: E402
from engine.rest import (  # noqa: E402
    MAX_REST_POSITIONS,
    PROVIDER_LOCAL_REST_JSON,
    REST_SCHEMA_VERSION,
    parse_rest_snapshot,
)


def _snapshot_payload(*, generated_at: str = "2026-07-30T14:30:00Z") -> dict:
    return {
        "schema_version": REST_SCHEMA_VERSION,
        "generated_at": generated_at,
        "currency": "EUR",
        "positions": [
            {
                "identifier": "A1XB5U",
                "name": "ETF One",
                "market_value_eur": "1234.56",
                "isin": "IE00BJ0KDQ92",
                "instrument_type": "ETF",
            },
            {
                "identifier": "555750",
                "name": "Telekom",
                "market_value_eur": "200.00",
                "isin": "DE0005557508",
                "instrument_type": "Stock",
            },
        ],
    }


def test_rest_schema_normalises_to_canonical_positions() -> None:
    now = datetime(2026, 7, 30, 15, 0, tzinfo=timezone.utc)
    snapshot = parse_rest_snapshot(_snapshot_payload(), now=now)

    assert snapshot.generated_at == datetime(2026, 7, 30, 14, 30, tzinfo=timezone.utc)
    assert tuple(snapshot.positions) == ("A1XB5U", "555750")
    assert snapshot.positions["A1XB5U"].value_eur == Decimal("1234.56")
    assert snapshot.positions["A1XB5U"].instrument_type == "etf"
    assert snapshot.positions["555750"].instrument_type == "stock"


def test_rest_schema_rejects_ambiguous_or_duplicate_financial_data() -> None:
    now = datetime(2026, 7, 30, 15, 0, tzinfo=timezone.utc)

    numeric_value = _snapshot_payload()
    numeric_value["positions"][0]["market_value_eur"] = 1234.56
    with pytest.raises(ValueError, match="decimal string"):
        parse_rest_snapshot(numeric_value, now=now)

    noncanonical_value = _snapshot_payload()
    noncanonical_value["positions"][0]["market_value_eur"] = "1,234.56"
    with pytest.raises(ValueError, match="canonical EUR decimal"):
        parse_rest_snapshot(noncanonical_value, now=now)

    duplicate_identifier = _snapshot_payload()
    duplicate_identifier["positions"][1]["identifier"] = "A1XB5U"
    with pytest.raises(ValueError, match="duplicate instrument identifier"):
        parse_rest_snapshot(duplicate_identifier, now=now)

    duplicate_isin = _snapshot_payload()
    duplicate_isin["positions"][1]["isin"] = "IE00BJ0KDQ92"
    with pytest.raises(ValueError, match="duplicate ISIN"):
        parse_rest_snapshot(duplicate_isin, now=now)


def test_rest_schema_is_bounded_and_source_timestamped() -> None:
    now = datetime(2026, 7, 30, 15, 0, tzinfo=timezone.utc)

    wrong_currency = _snapshot_payload()
    wrong_currency["currency"] = "USD"
    with pytest.raises(ValueError, match="currency must be EUR"):
        parse_rest_snapshot(wrong_currency, now=now)

    future = _snapshot_payload(
        generated_at=(now + timedelta(minutes=6)).isoformat()
    )
    with pytest.raises(ValueError, match="too far in the future"):
        parse_rest_snapshot(future, now=now)

    naive = _snapshot_payload(generated_at="2026-07-30T14:30:00")
    with pytest.raises(ValueError, match="include a timezone"):
        parse_rest_snapshot(naive, now=now)

    too_many = _snapshot_payload()
    too_many["positions"] = [
        {
            "identifier": f"ID{index:04d}",
            "name": f"Position {index}",
            "market_value_eur": "1.00",
        }
        for index in range(MAX_REST_POSITIONS + 1)
    ]
    with pytest.raises(ValueError, match="at most"):
        parse_rest_snapshot(too_many, now=now)


def test_rest_positions_use_the_same_stable_schema_8_engine() -> None:
    positions = read_positions(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv", CsvSourceConfig(provider=PROVIDER_COMDIRECT)
    )
    payload = calculate_portfolio_payload_from_positions(
        positions,
        ROOT / "examples" / "current-plan",
        evaluated_at=datetime(2026, 7, 30, 14, 30, tzinfo=timezone.utc),
        source_provider=PROVIDER_LOCAL_REST_JSON,
        source_label="portfolio-gateway.local/api/v1/portfolio",
    )

    assert payload["schema_version"] == 8
    assert payload["summary"]["payload_schema_version"] == 8
    assert payload["summary"]["source_provider"] == PROVIDER_LOCAL_REST_JSON
    assert payload["summary"]["whole_portfolio_value_eur"] == Decimal("14053.01")
    assert len(payload["holdings"]) == 13
    assert len(payload["recommendations"]) == 7


def test_rest_transport_and_config_flow_are_fail_closed() -> None:
    transport = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    diagnostics = (COMPONENT / "diagnostics.py").read_text(encoding="utf-8")
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")

    assert "async_get_clientsession" not in transport
    assert "_PinnedLocalResolver" in transport
    assert "use_dns_cache=False" in transport
    assert "trust_env=False" in transport
    assert "DummyCookieJar" in transport
    assert '"Authorization": f"Bearer {config.api_token}"' in transport
    assert "allow_redirects=False" in transport
    assert "MAX_REST_RESPONSE_BYTES: Final = 1024 * 1024" in transport
    assert "object_pairs_hook=_json_object_without_duplicate_keys" in transport
    assert "resolve exclusively to loopback, link-local, or private addresses" in transport
    assert "response.status in {401, 403}" in transport
    assert "response.status == 429" in transport
    assert "TextSelectorType.PASSWORD" in flow
    assert "async_step_reauth_confirm" in flow
    assert "_calculate_positions_with_override" in flow
    assert "ConfigEntryAuthFailed" in coordinator
    assert "retry_after=float" in coordinator
    assert '"source_adapter": coordinator.source_adapter_diagnostics' in diagnostics
    assert "CONF_REST_API_TOKEN" not in diagnostics
    assert "PROVIDER_LOCAL_REST_JSON" in sensor


def test_rest_schema_accepts_one_bounded_investment_reserve() -> None:
    now = datetime(2026, 7, 30, 15, 0, tzinfo=timezone.utc)
    payload = _snapshot_payload()
    payload["investment_reserve"] = {
        "available_eur": "1050.00",
        "as_of": "2026-07-30T14:29:00Z",
    }
    snapshot = parse_rest_snapshot(payload, now=now)
    assert snapshot.investment_reserve_eur == Decimal("1050.00")
    assert snapshot.investment_reserve_as_of == datetime(
        2026, 7, 30, 14, 29, tzinfo=timezone.utc
    )


def test_rest_schema_rejects_ambiguous_investment_reserve() -> None:
    now = datetime(2026, 7, 30, 15, 0, tzinfo=timezone.utc)

    partial = _snapshot_payload()
    partial["investment_reserve"] = {"available_eur": "1050.00"}
    with pytest.raises(ValueError, match="unexpected schema"):
        parse_rest_snapshot(partial, now=now)

    numeric = _snapshot_payload()
    numeric["investment_reserve"] = {
        "available_eur": 1050,
        "as_of": "2026-07-30T14:29:00Z",
    }
    with pytest.raises(ValueError, match="decimal string"):
        parse_rest_snapshot(numeric, now=now)

    negative = _snapshot_payload()
    negative["investment_reserve"] = {
        "available_eur": "-1.00",
        "as_of": "2026-07-30T14:29:00Z",
    }
    with pytest.raises(ValueError, match="canonical EUR decimal"):
        parse_rest_snapshot(negative, now=now)

    naive = _snapshot_payload()
    naive["investment_reserve"] = {
        "available_eur": "1050.00",
        "as_of": "2026-07-30T14:29:00",
    }
    with pytest.raises(ValueError, match="include a timezone"):
        parse_rest_snapshot(naive, now=now)

    newer_than_snapshot = _snapshot_payload()
    newer_than_snapshot["investment_reserve"] = {
        "available_eur": "1050.00",
        "as_of": "2026-07-30T14:40:01Z",
    }
    with pytest.raises(ValueError, match="newer than the snapshot"):
        parse_rest_snapshot(newer_than_snapshot, now=now)
