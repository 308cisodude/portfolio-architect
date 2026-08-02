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
