"""Executable regression test for v1.10.2 cache serialization."""

from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def _load_cache_payload_module():
    spec = importlib.util.spec_from_file_location(
        "portfolio_architect_cache_payload", COMPONENT / "cache_payload.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_engine_payload_with_decimals_round_trips_through_json_cache() -> None:
    sys.path.insert(0, str(COMPONENT))
    try:
        from engine.calculator import calculate_portfolio_payload_from_positions
        from engine.models import Position
        from model import parse_portfolio_data

        payload = calculate_portfolio_payload_from_positions(
            {
                "A1XB5U": Position(
                    wkn="A1XB5U",
                    isin="IE00BJ0KDQ92",
                    name="World",
                    instrument_type="etf",
                    source_type="ETF",
                    value_eur=Decimal("135.275"),
                )
            },
            ROOT / "examples" / "current-plan",
            evaluated_at=datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc),
            source_provider="local_rest_json",
            source_label="test",
        )
        assert isinstance(payload["summary"]["current_portfolio_value_eur"], Decimal)

        safe = _load_cache_payload_module().json_safe_payload(payload)
        encoded = json.dumps(
            safe,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        restored = json.loads(encoded)
        assert restored["summary"]["current_portfolio_value_eur"] == "135.275"

        data = parse_portfolio_data(
            restored["recommendations"],
            restored["summary"],
            restored["policy_findings"],
            restored["holdings"],
        )
        assert data.allocation.portfolio_value_eur == 135.275
    finally:
        sys.path.remove(str(COMPONENT))


def test_cache_serializer_rejects_nonfinite_and_unsupported_values() -> None:
    serializer = _load_cache_payload_module().json_safe_payload
    for invalid in (Decimal("NaN"), float("inf"), object()):
        try:
            serializer(invalid)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"Expected rejection for {type(invalid).__name__}")
