from datetime import datetime, timezone
from decimal import Decimal

import pytest

from portfolio_architect_gateway.errors import ProtocolError
from portfolio_architect_gateway.models import (
    PortfolioSnapshot,
    Position,
    canonical_decimal,
    parse_snapshot_bytes,
    validate_snapshot,
)
from portfolio_architect_gateway.store import load_snapshot, save_snapshot


def sample_snapshot() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        generated_at=datetime(2026, 7, 30, 15, 0, tzinfo=timezone.utc),
        positions=(
            Position(
                identifier="A1XB5U",
                name="ETF One",
                market_value_eur=Decimal("1234.5600"),
                isin="IE00BJ0KDQ92",
                instrument_type="ETF",
            ),
        ),
    )


def test_snapshot_matches_v14_contract_and_round_trips() -> None:
    snapshot = validate_snapshot(sample_snapshot())
    data = snapshot.to_bytes()
    assert b'"schema_version":1' in data
    assert b'"currency":"EUR"' in data
    assert b'"market_value_eur":"1234.56"' in data
    assert parse_snapshot_bytes(data) == snapshot
    assert snapshot.etag.startswith('"sha256-')



def test_quantity_bearing_snapshot_survives_persisted_round_trip_byte_for_byte(
    tmp_path,
) -> None:
    snapshot = validate_snapshot(
        PortfolioSnapshot(
            generated_at=datetime(2026, 8, 14, 22, 24, 46, tzinfo=timezone.utc),
            positions=(
                Position(
                    identifier="A1XB5U",
                    name="ETF One",
                    market_value_eur=Decimal("1234.56"),
                    quantity=Decimal("3.750000"),
                    isin="IE00BJ0KDQ92",
                    instrument_type="ETF",
                ),
            ),
        )
    )
    original_body = snapshot.to_bytes()
    original_etag = snapshot.etag
    path = tmp_path / "portfolio.json"

    save_snapshot(path, snapshot)
    restored = load_snapshot(path)

    assert restored is not None
    assert restored.positions[0].quantity == Decimal("3.75")
    assert restored.to_bytes() == original_body
    assert restored.etag == original_etag


def test_cached_quantity_rejects_noncanonical_or_negative_values() -> None:
    import json

    for quantity in ("-1", "1e3", "NaN", 1):
        base = sample_snapshot().as_dict()
        base["positions"][0]["quantity"] = quantity
        data = json.dumps(base, separators=(",", ":"), sort_keys=True).encode("utf-8")
        with pytest.raises(ProtocolError, match="position quantity"):
            parse_snapshot_bytes(data)

def test_decimal_output_never_uses_exponent_or_grouping() -> None:
    assert canonical_decimal(Decimal("0.0001000")) == "0.0001"
    assert canonical_decimal(Decimal("1000000.00")) == "1000000"


def test_snapshot_fails_closed_on_duplicate_identity_and_zero_total() -> None:
    first = sample_snapshot().positions[0]
    with pytest.raises(ProtocolError, match="duplicate identifier"):
        validate_snapshot(
            PortfolioSnapshot(
                generated_at=sample_snapshot().generated_at,
                positions=(first, first),
            )
        )
    with pytest.raises(ProtocolError, match="positive"):
        validate_snapshot(
            PortfolioSnapshot(
                generated_at=sample_snapshot().generated_at,
                positions=(
                    Position("A1XB5U", "ETF", Decimal("0"), instrument_type="ETF"),
                ),
            )
        )


def test_cached_json_rejects_duplicate_keys() -> None:
    data = (
        b'{"schema_version":1,"schema_version":1,"generated_at":"2026-07-30T15:00:00Z",'
        b'"currency":"EUR","positions":[]}'
    )
    with pytest.raises(ProtocolError, match="valid strict"):
        parse_snapshot_bytes(data)
