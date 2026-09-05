"""v1.34.0 generic target identity and presentation-model regressions."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
import types

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(ROOT / "tests"))
from reference_portfolio import read_reference_positions
CURRENT_PLAN = ROOT / "examples" / "current-plan"

T1 = "target_11111111111111111111111111111111"
T2 = "target_22222222222222222222222222222222"
T3 = "target_33333333333333333333333333333333"


def _load_engine_package():
    package = types.ModuleType("pa_v134")
    package.__path__ = [str(COMPONENT)]
    sys.modules["pa_v134"] = package
    engine_path = COMPONENT / "engine" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "pa_v134.engine", engine_path, submodule_search_locations=[str(engine_path.parent)]
    )
    engine = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = engine
    assert spec.loader is not None
    spec.loader.exec_module(engine)
    return engine


def _load_model_and_presentation():
    package = sys.modules.get("pa_v134")
    if package is None:
        _load_engine_package()
    for name in ("model", "portfolio_presentation"):
        path = COMPONENT / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"pa_v134.{name}", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return sys.modules["pa_v134.model"], sys.modules["pa_v134.portfolio_presentation"]


def _load_plan_editor():
    if "pa_v134.engine" not in sys.modules:
        _load_engine_package()
    path = COMPONENT / "plan_editor.py"
    spec = importlib.util.spec_from_file_location("pa_v134.plan_editor", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _target(target_id: str, wkn: str, isin: str, weight: float, *, name: str | None = None):
    return {
        "target_id": target_id,
        "name": name or "Example target",
        "wkn": wkn,
        "isin": isin,
        "target_pct": weight,
        "buy_enabled": True,
    }


def _document(allocation, *, schema_version=2):
    return {
        "schema_version": schema_version,
        "portfolio": {
            "id": "generic",
            "name": "Generic plan",
            "currency": "EUR",
            "strategy": "buy_only",
            "monthly_contribution": 100,
            "allocation": allocation,
        },
        "rebalancing": {"corridor_pp": 1, "minimum_trade": 1, "rounding_step": 1},
    }


def test_current_reference_plan_is_schema2_with_opaque_target_ids() -> None:
    engine = _load_engine_package()
    targets = sys.modules["pa_v134.engine.targets"]
    target_funds = sys.modules["pa_v134.engine.rebalance"].target_funds
    document = yaml.safe_load((CURRENT_PLAN / "portfolio.yaml").read_text(encoding="utf-8"))

    assert document["schema_version"] == 2
    raw_targets = document["portfolio"]["allocation"]
    target_ids = [item["target_id"] for item in raw_targets]
    assert len(target_ids) == 7
    assert len(set(target_ids)) == 7
    assert all("target_id" in item and "id" not in item for item in raw_targets)
    assert all(targets.OPAQUE_TARGET_ID_RE.fullmatch(target_id) for target_id in target_ids)
    assert not ({"world", "emerging_markets", "world_small_cap", "healthcare", "ai_big_data", "cybersecurity", "robotics"} & set(target_ids))

    canonical = target_funds(document)
    assert [item["target_id"] for item in canonical] == [item["id"] for item in canonical]
    assert engine.__version__


def test_pa_target_id_generator_is_128_bit_opaque_and_instrument_independent() -> None:
    _load_engine_package()
    targets = sys.modules["pa_v134.engine.targets"]
    first = targets.generate_target_id()
    second = targets.generate_target_id({first})
    assert first != second
    assert targets.OPAQUE_TARGET_ID_RE.fullmatch(first)
    assert targets.OPAQUE_TARGET_ID_RE.fullmatch(second)
    assert len(bytes.fromhex(first.removeprefix("target_"))) == 16
    assert "isin" not in targets.generate_target_id.__annotations__
    source = (COMPONENT / "engine" / "targets.py").read_text(encoding="utf-8")
    assert "secrets.token_hex(TARGET_ID_RANDOM_BYTES)" in source
    assert tuple(targets.generate_target_id.__annotations__) == ("existing", "return")


def test_schema1_legacy_id_remains_supported_but_schema2_requires_opaque_target_id() -> None:
    _load_engine_package()
    target_funds = sys.modules["pa_v134.engine.rebalance"].target_funds
    legacy = _document(
        [{"id": "core", "name": "Core", "wkn": "AAAAA1", "isin": "IE0000000001", "target_pct": 100, "buy_enabled": True}],
        schema_version=1,
    )
    assert target_funds(legacy)[0]["target_id"] == "core"

    missing_explicit = dict(legacy)
    missing_explicit["schema_version"] = 2
    with pytest.raises(ValueError, match="target_id is required"):
        target_funds(missing_explicit)

    semantic_schema2 = _document([_target("core", "AAAAA1", "IE0000000001", 100)])
    with pytest.raises(ValueError, match="opaque 128-bit PA target ID"):
        target_funds(semantic_schema2)

    mismatched = _document(
        [{**_target(T1, "AAAAA1", "IE0000000001", 100), "id": "different"}]
    )
    with pytest.raises(ValueError, match="target_id and legacy id must match"):
        target_funds(mismatched)


def test_generic_target_count_and_identity_do_not_depend_on_order_name_or_instrument() -> None:
    _load_engine_package()
    target_funds = sys.modules["pa_v134.engine.rebalance"].target_funds
    original = _document([
        _target(T1, "AAAAA1", "IE0000000001", 40, name="Core one"),
        _target(T2, "AAAAA2", "IE0000000002", 35),
        _target(T3, "AAAAA3", "IE0000000003", 25),
    ])
    changed = _document([
        _target(T3, "AAAAA3", "IE0000000003", 25),
        _target(T1, "BBBBB1", "IE0000000011", 40, name="Core replacement"),
        _target(T2, "AAAAA2", "IE0000000002", 35),
    ])
    assert {item["id"] for item in target_funds(original)} == {T1, T2, T3}
    assert {item["id"] for item in target_funds(changed)} == {T1, T2, T3}
    assert next(item for item in target_funds(changed) if item["target_id"] == T1)["isin"] == "IE0000000011"

    too_many = [
        _target(f"target_{index:032x}", f"W{index:05d}", f"IE{index:010d}", 100 / 33)
        for index in range(33)
    ]
    with pytest.raises(ValueError, match="at most 32"):
        target_funds(_document(too_many))


def test_removed_target_is_not_resurrected_from_same_isin_in_active_override(tmp_path: Path) -> None:
    engine = _load_engine_package()
    editor = _load_plan_editor()
    Position = sys.modules["pa_v134.engine.models"].Position
    document = _document([_target(T1, "AAAAA1", "IE0000000001", 100, name="Old role")])
    (tmp_path / "portfolio.yaml").write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    position = Position(
        wkn="AAAAA1",
        isin="IE0000000001",
        name="Same instrument",
        instrument_type="etf",
        source_type="ETF",
        value_eur=Decimal("100"),
    )

    # Empty configured_instruments means a UI plan override exists but this old
    # YAML target role is not part of the current plan anymore.
    context = editor.load_plan_editor_context_from_positions(
        {"AAAAA1": position}, tmp_path, configured_instruments=[]
    )
    candidate = context.candidates[0]
    assert candidate.isin == "IE0000000001"
    assert candidate.to_option()["value"] == "IE0000000001"
    assert candidate.target_id is None
    fresh = sys.modules["pa_v134.engine.targets"].generate_target_id({T1})
    assert fresh != T1
    assert sys.modules["pa_v134.engine.targets"].OPAQUE_TARGET_ID_RE.fullmatch(fresh)
    assert engine.__version__


def test_plan_override_accepts_target_identity_and_rejects_duplicates() -> None:
    _load_engine_package()
    plan = sys.modules["pa_v134.engine.plan"]
    base = _document([_target(T1, "AAAAA1", "IE0000000001", 100)])
    override = {
        "enabled": True,
        "name": "Generic",
        "budget_amount_eur": 100,
        "budget_basis": "per_execution",
        "frequency": "monthly",
        "executions_per_period": 1,
        "instruments": [
            _target(T1, "AAAAA1", "IE0000000001", 50),
            _target(T2, "AAAAA2", "IE0000000002", 50),
        ],
    }
    document, _runtime = plan.apply_plan_override(base, override)
    assert [item["target_id"] for item in document["portfolio"]["allocation"]] == [T1, T2]
    assert [item["id"] for item in document["portfolio"]["allocation"]] == [T1, T2]

    override["instruments"][1]["target_id"] = T1
    with pytest.raises(ValueError, match="duplicate target_id"):
        plan.apply_plan_override(base, override)


def test_payload_parser_and_presentation_model_expose_explicit_target_identity() -> None:
    engine = _load_engine_package()
    model, presentation = _load_model_and_presentation()
    payload = engine.calculate_portfolio_payload_from_positions(
        read_reference_positions(),
        CURRENT_PLAN,
        evaluated_at=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
        source_provider="generic_csv",
        source_label="Sanitized test fixture",
    )

    assert payload["schema_version"] == 8
    assert all(item["target_id"] == item["fund_id"] for item in payload["recommendations"])
    assert payload["summary"]["missing_target_ids"] == payload["summary"]["missing_target_fund_ids"]
    assert all(item["plan_target_id"] == item["plan_fund_id"] for item in payload["holdings"])

    data = model.parse_portfolio_data(
        payload["recommendations"], payload["summary"], payload["policy_findings"], holdings=payload["holdings"]
    )
    assert all(key == position.target_id for key, position in data.positions.items())

    blocked = presentation.build_portfolio_presentation(data, plan_actionable=False, actionability_reason="data_stale")
    assert blocked["presentation_schema_version"] == 2
    assert blocked["target_count"] == 7
    assert blocked["current_plan_holding_count"] == data.allocation.current_plan_held_position_count == 6
    assert set(blocked["current_plan_holding_ids"]) == {item.position_id for item in data.holdings.values() if item.in_current_plan}
    assert blocked["outside_scope_count"] == data.allocation.outside_scope_position_count == 7
    assert blocked["target_ids"] == list(data.positions)
    assert set(blocked["outside_scope_position_ids"]) == {item.position_id for item in data.holdings.values() if not item.in_current_plan}
    assert all(item["entity_key"] == item["target_id"] for item in blocked["targets"])
    assert all("current_value_eur" not in item for item in blocked["targets"])
    assert any(item["position_id"] == "holding_ie00bywz0333" for item in blocked["outside_scope_holdings"])
    assert any(item["wkn"] == "A113FM" for item in blocked["outside_scope_holdings"])

    actionable = presentation.build_portfolio_presentation(data, plan_actionable=True, actionability_reason="actionable")
    assert actionable["plan_actionable"] is True
    assert actionable["policy"]["mandatory_controls_compliant"] is True
    assert all(item["entity_key"] == item["position_id"] for item in actionable["outside_scope_holdings"])


def test_home_assistant_identity_uses_target_id_and_native_editor_generates_it() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    editor = (COMPONENT / "plan_editor.py").read_text(encoding="utf-8")

    assert 'f"{source_key}_{fund_id}_{kind}_allocation"' in sensor
    assert 'f"{source_key}_{fund_id}_proposed_buy"' in sensor
    assert 'f"{source_key}_{fund_id}_target_position_held"' in binary
    assert "position.wkn" not in sensor[sensor.index("class PortfolioAllocationSensor"):sensor.index("_ACTIONABLE_POSITION_ATTRIBUTE_KEYS")].split("_attr_unique_id", 1)[1].split("\n", 1)[0]
    assert 'vol.Required("target_id")' not in flow
    assert "generate_target_id(used_target_ids)" in flow
    assert "_selected_isins" in flow and "_selected_wkns" not in flow
    assert 'return {"value": self.isin, "label": self.label}' in editor
    assert "_derived_id" not in editor
    assert "target_id: str | None" in editor


def test_current_state_model_has_no_target_tombstone_or_outside_scope_history_registry() -> None:
    target_source = (COMPONENT / "engine" / "targets.py").read_text(encoding="utf-8").casefold()
    presentation_source = (COMPONENT / "portfolio_presentation.py").read_text(encoding="utf-8").casefold()
    docs = (ROOT / "docs" / "TARGET-ARCHITECTURE.md").read_text(encoding="utf-8").casefold()
    assert "tombstone" not in target_source
    assert "retired target registry" not in presentation_source
    assert "non-target holdings persist only while accepted sources provide" in docs
    assert "exactly the same isin" in docs


def test_presentation_contract_is_first_class_and_dashboard_remains_native_only() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    assert "PortfolioPresentationModelSensor" in sensor
    assert 'return "presentation_model"' in sensor

    document = yaml.safe_load((CURRENT_PLAN / "portfolio.yaml").read_text(encoding="utf-8"))
    target_ids = [item["target_id"] for item in document["portfolio"]["allocation"]]
    for path in (
        ROOT / "dashboard" / "bilingual-dashboard.yaml",
        ROOT / "dashboard" / "generated" / "portfolio-architect-dashboard-en.yaml",
        ROOT / "dashboard" / "generated" / "portfolio-architect-dashboard-de.yaml",
    ):
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert "auto-entities" not in lowered
        assert "card-mod" not in lowered
        assert "custom:" not in lowered
        assert "javascript" not in lowered
        for target_id in target_ids:
            assert f"portfolio_architect_{target_id}_" not in text
        assert "portfolio_architect_presentation_target_01_" in text
        assert "type: entity-filter" in text

    bilingual = (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")
    assert "name: Exception review" in bilingual
    assert "name: Ausnahmeprüfung" in bilingual
