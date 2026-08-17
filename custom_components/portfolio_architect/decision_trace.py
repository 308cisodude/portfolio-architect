"""Bounded plan-delta and decision-trace contracts.

The trace is derived inside Home Assistant from already validated PortfolioData.
It deliberately stores only the two most recent validated evaluations and never
stores source credentials, account identifiers, or raw broker documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, ClassVar

MAX_TRACE_POSITIONS = 32
MAX_TRACE_POLICY_FINDINGS = 256
MAX_TRACE_NAME_LENGTH = 160
MAX_TRACE_PROVIDER_LENGTH = 64
MAX_TRACE_REASON_CODES = 12
MAX_TRACE_BYTES = 512 * 1024
MATERIAL_DRIFT_DELTA_PP = 0.10
MATERIAL_MONEY_DELTA_EUR = 1.00

PLAN_CHANGE_STATES = (
    "baseline_established",
    "unchanged",
    "allocation_changed",
    "recommendation_changed",
    "execution_state_changed",
    "policy_changed",
    "source_changed",
    "multiple_changes",
)
CHANGE_CATEGORIES = (
    "allocation",
    "recommendation",
    "execution",
    "policy",
    "source",
)


class DecisionTraceError(ValueError):
    """Raised when persisted decision-trace data violates the bounded contract."""


def _bounded_text(value: Any, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise DecisionTraceError(f"{field} must be a string")
    value = value.strip()
    if not value or len(value) > maximum or any(ord(char) < 32 for char in value):
        raise DecisionTraceError(f"{field} is empty, too long, or contains control characters")
    return value


def _bounded_enum(
    value: Any,
    *,
    field: str,
    allowed: set[str] | frozenset[str] | tuple[str, ...],
) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise DecisionTraceError(f"{field} is invalid")
    return value


def _bounded_bool(value: Any, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise DecisionTraceError(f"{field} must be boolean")
    return value


def _bounded_int(value: Any, *, field: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise DecisionTraceError(f"{field} is invalid")
    return value


def _bounded_float(
    value: Any,
    *,
    field: str,
    minimum: float,
    maximum: float,
    digits: int,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DecisionTraceError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise DecisionTraceError(f"{field} is outside the supported range")
    return round(number, digits)


def _utc_datetime(value: Any, *, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and len(value) <= 64:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as err:
            raise DecisionTraceError(f"{field} is invalid") from err
    else:
        raise DecisionTraceError(f"{field} is invalid")
    if parsed.tzinfo is None:
        raise DecisionTraceError(f"{field} lacks a timezone")
    return parsed.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return _utc_datetime(value, field="evaluated_at").isoformat(timespec="seconds")


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if not encoded or len(encoded) > MAX_TRACE_BYTES:
        raise DecisionTraceError("Decision-trace document exceeds the bounded size")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class PositionDecisionSnapshot:
    """Decision-relevant state of one configured target position."""

    fund_id: str
    fund_name: str
    allocation_status: str
    deviation_pp: float
    proposed_buy_eur: float
    execution_route: str
    execution_state: str
    recommendation_reason: str
    deferred: bool
    execution_provider: str | None = None

    ALLOCATION_STATES: ClassVar[frozenset[str]] = frozenset(
        {"underweight", "on_target", "overweight"}
    )

    @classmethod
    def from_position(cls, position: Any) -> PositionDecisionSnapshot:
        return cls(
            fund_id=_bounded_text(position.fund_id, field="fund_id", maximum=64),
            fund_name=_bounded_text(
                position.name, field="fund_name", maximum=MAX_TRACE_NAME_LENGTH
            ),
            allocation_status=_bounded_enum(
                position.allocation_status,
                field="allocation_status",
                allowed=cls.ALLOCATION_STATES,
            ),
            deviation_pp=_bounded_float(
                position.deviation_pp,
                field="deviation_pp",
                minimum=-100,
                maximum=100,
                digits=4,
            ),
            proposed_buy_eur=_bounded_float(
                position.proposed_buy_eur,
                field="proposed_buy_eur",
                minimum=0,
                maximum=1_000_000_000,
                digits=2,
            ),
            execution_route=_bounded_text(
                position.execution_route, field="execution_route", maximum=64
            ),
            execution_state=_bounded_text(
                position.execution_state, field="execution_state", maximum=64
            ),
            recommendation_reason=_bounded_text(
                position.recommendation_reason,
                field="recommendation_reason",
                maximum=96,
            ),
            deferred=_bounded_bool(position.deferred, field="deferred"),
            execution_provider=(
                None
                if getattr(position, "execution_provider", None) is None
                else _bounded_text(
                    position.execution_provider,
                    field="execution_provider",
                    maximum=32,
                )
            ),
        )

    @classmethod
    def from_dict(cls, raw: Any) -> PositionDecisionSnapshot:
        legacy_expected = {
            "fund_id",
            "fund_name",
            "allocation_status",
            "deviation_pp",
            "proposed_buy_eur",
            "execution_route",
            "execution_state",
            "recommendation_reason",
            "deferred",
        }
        current_expected = legacy_expected | {"execution_provider"}
        if not isinstance(raw, dict) or frozenset(raw) not in {
            frozenset(legacy_expected),
            frozenset(current_expected),
        }:
            raise DecisionTraceError("Persisted position snapshot has invalid fields")
        return cls(
            fund_id=_bounded_text(raw["fund_id"], field="fund_id", maximum=64),
            fund_name=_bounded_text(
                raw["fund_name"], field="fund_name", maximum=MAX_TRACE_NAME_LENGTH
            ),
            allocation_status=_bounded_enum(
                raw["allocation_status"],
                field="allocation_status",
                allowed=cls.ALLOCATION_STATES,
            ),
            deviation_pp=_bounded_float(
                raw["deviation_pp"],
                field="deviation_pp",
                minimum=-100,
                maximum=100,
                digits=4,
            ),
            proposed_buy_eur=_bounded_float(
                raw["proposed_buy_eur"],
                field="proposed_buy_eur",
                minimum=0,
                maximum=1_000_000_000,
                digits=2,
            ),
            execution_route=_bounded_text(
                raw["execution_route"], field="execution_route", maximum=64
            ),
            execution_state=_bounded_text(
                raw["execution_state"], field="execution_state", maximum=64
            ),
            recommendation_reason=_bounded_text(
                raw["recommendation_reason"],
                field="recommendation_reason",
                maximum=96,
            ),
            deferred=_bounded_bool(raw["deferred"], field="deferred"),
            execution_provider=(
                None
                if raw.get("execution_provider") is None
                else _bounded_text(
                    raw["execution_provider"],
                    field="execution_provider",
                    maximum=32,
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "fund_id": self.fund_id,
            "fund_name": self.fund_name,
            "allocation_status": self.allocation_status,
            "deviation_pp": self.deviation_pp,
            "proposed_buy_eur": self.proposed_buy_eur,
            "execution_route": self.execution_route,
            "execution_state": self.execution_state,
            "recommendation_reason": self.recommendation_reason,
            "deferred": self.deferred,
            "execution_provider": self.execution_provider,
        }


@dataclass(frozen=True, slots=True)
class PolicyDecisionSnapshot:
    """Bounded policy summary and active finding states."""

    status: str
    errors: int
    warnings: int
    opportunities: int
    accepted_exceptions: int
    active_findings: tuple[tuple[str, str], ...]

    @classmethod
    def from_policy(cls, policy: Any) -> PolicyDecisionSnapshot:
        findings = tuple(
            sorted(
                (
                    _bounded_text(item.key, field="policy_finding_key", maximum=160),
                    _bounded_text(
                        item.entity_state, field="policy_finding_state", maximum=32
                    ),
                )
                for item in policy.non_pass_findings
            )
        )
        if len(findings) > MAX_TRACE_POLICY_FINDINGS:
            raise DecisionTraceError("Too many policy findings for decision trace")
        return cls(
            status=_bounded_text(policy.status, field="policy_status", maximum=32),
            errors=_bounded_int(policy.errors, field="policy_errors", minimum=0, maximum=256),
            warnings=_bounded_int(
                policy.warnings, field="policy_warnings", minimum=0, maximum=256
            ),
            opportunities=_bounded_int(
                policy.opportunities,
                field="policy_opportunities",
                minimum=0,
                maximum=256,
            ),
            accepted_exceptions=_bounded_int(
                policy.accepted_exceptions,
                field="policy_accepted_exceptions",
                minimum=0,
                maximum=256,
            ),
            active_findings=findings,
        )

    @classmethod
    def from_dict(cls, raw: Any) -> PolicyDecisionSnapshot:
        expected = {
            "status",
            "errors",
            "warnings",
            "opportunities",
            "accepted_exceptions",
            "active_findings",
        }
        if not isinstance(raw, dict) or set(raw) != expected:
            raise DecisionTraceError("Persisted policy snapshot has invalid fields")
        active = raw["active_findings"]
        if not isinstance(active, list) or len(active) > MAX_TRACE_POLICY_FINDINGS:
            raise DecisionTraceError("Persisted policy findings are invalid")
        parsed: list[tuple[str, str]] = []
        for item in active:
            if not isinstance(item, list) or len(item) != 2:
                raise DecisionTraceError("Persisted policy finding is invalid")
            parsed.append(
                (
                    _bounded_text(item[0], field="policy_finding_key", maximum=160),
                    _bounded_text(item[1], field="policy_finding_state", maximum=32),
                )
            )
        if parsed != sorted(parsed):
            raise DecisionTraceError("Persisted policy findings are not deterministic")
        if len({key for key, _ in parsed}) != len(parsed):
            raise DecisionTraceError("Persisted policy findings contain duplicates")
        return cls(
            status=_bounded_text(raw["status"], field="policy_status", maximum=32),
            errors=_bounded_int(raw["errors"], field="policy_errors", minimum=0, maximum=256),
            warnings=_bounded_int(
                raw["warnings"], field="policy_warnings", minimum=0, maximum=256
            ),
            opportunities=_bounded_int(
                raw["opportunities"],
                field="policy_opportunities",
                minimum=0,
                maximum=256,
            ),
            accepted_exceptions=_bounded_int(
                raw["accepted_exceptions"],
                field="policy_accepted_exceptions",
                minimum=0,
                maximum=256,
            ),
            active_findings=tuple(parsed),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "opportunities": self.opportunities,
            "accepted_exceptions": self.accepted_exceptions,
            "active_findings": [list(item) for item in self.active_findings],
        }


@dataclass(frozen=True, slots=True)
class EvaluationSnapshot:
    """One bounded validated Portfolio Architect evaluation."""

    evaluated_at: datetime
    source_provider: str
    source_count: int
    source_conflict_count: int
    execution_state: str
    reserve_source: str
    available_reserve_eur: float
    additional_cash_required_eur: float
    positions: tuple[PositionDecisionSnapshot, ...]
    policy: PolicyDecisionSnapshot

    @property
    def identity_sha256(self) -> str:
        return _canonical_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Any) -> EvaluationSnapshot:
        expected = {
            "evaluated_at",
            "source_provider",
            "source_count",
            "source_conflict_count",
            "execution_state",
            "reserve_source",
            "available_reserve_eur",
            "additional_cash_required_eur",
            "positions",
            "policy",
        }
        if not isinstance(raw, dict) or set(raw) != expected:
            raise DecisionTraceError("Persisted evaluation snapshot has invalid fields")
        positions_raw = raw["positions"]
        if not isinstance(positions_raw, list) or len(positions_raw) > MAX_TRACE_POSITIONS:
            raise DecisionTraceError("Persisted evaluation positions are invalid")
        positions = tuple(
            PositionDecisionSnapshot.from_dict(item) for item in positions_raw
        )
        if tuple(item.fund_id for item in positions) != tuple(
            sorted(item.fund_id for item in positions)
        ):
            raise DecisionTraceError("Persisted evaluation positions are not deterministic")
        if len({item.fund_id for item in positions}) != len(positions):
            raise DecisionTraceError("Persisted evaluation positions contain duplicates")
        return cls(
            evaluated_at=_utc_datetime(raw["evaluated_at"], field="evaluated_at"),
            source_provider=_bounded_text(
                raw["source_provider"],
                field="source_provider",
                maximum=MAX_TRACE_PROVIDER_LENGTH,
            ),
            source_count=_bounded_int(
                raw["source_count"], field="source_count", minimum=1, maximum=9
            ),
            source_conflict_count=_bounded_int(
                raw["source_conflict_count"],
                field="source_conflict_count",
                minimum=0,
                maximum=512,
            ),
            execution_state=_bounded_text(
                raw["execution_state"], field="execution_state", maximum=64
            ),
            reserve_source=_bounded_text(
                raw["reserve_source"], field="reserve_source", maximum=64
            ),
            available_reserve_eur=_bounded_float(
                raw["available_reserve_eur"],
                field="available_reserve_eur",
                minimum=0,
                maximum=1_000_000_000,
                digits=2,
            ),
            additional_cash_required_eur=_bounded_float(
                raw["additional_cash_required_eur"],
                field="additional_cash_required_eur",
                minimum=0,
                maximum=1_000_000_000,
                digits=2,
            ),
            positions=positions,
            policy=PolicyDecisionSnapshot.from_dict(raw["policy"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_at": _utc_iso(self.evaluated_at),
            "source_provider": self.source_provider,
            "source_count": self.source_count,
            "source_conflict_count": self.source_conflict_count,
            "execution_state": self.execution_state,
            "reserve_source": self.reserve_source,
            "available_reserve_eur": self.available_reserve_eur,
            "additional_cash_required_eur": self.additional_cash_required_eur,
            "positions": [item.to_dict() for item in self.positions],
            "policy": self.policy.to_dict(),
        }


def build_evaluation_snapshot(
    data: Any,
    *,
    evaluated_at: datetime,
    source_provider: str,
    source_count: int,
    source_conflict_count: int,
) -> EvaluationSnapshot:
    """Build a bounded snapshot from already validated PortfolioData."""
    positions = tuple(
        sorted(
            (
                PositionDecisionSnapshot.from_position(position)
                for position in data.positions.values()
                if position.is_target_position
            ),
            key=lambda item: item.fund_id,
        )
    )
    if not positions or len(positions) > MAX_TRACE_POSITIONS:
        raise DecisionTraceError("Decision trace requires 1 to 32 target positions")
    if len({item.fund_id for item in positions}) != len(positions):
        raise DecisionTraceError("Decision trace target positions contain duplicates")
    plan = data.monthly_plan
    return EvaluationSnapshot(
        evaluated_at=_utc_datetime(evaluated_at, field="evaluated_at"),
        source_provider=_bounded_text(
            source_provider,
            field="source_provider",
            maximum=MAX_TRACE_PROVIDER_LENGTH,
        ),
        source_count=_bounded_int(
            source_count, field="source_count", minimum=1, maximum=9
        ),
        source_conflict_count=_bounded_int(
            source_conflict_count,
            field="source_conflict_count",
            minimum=0,
            maximum=512,
        ),
        execution_state=_bounded_text(
            plan.execution_state, field="execution_state", maximum=64
        ),
        reserve_source=_bounded_text(
            plan.reserve_source, field="reserve_source", maximum=64
        ),
        available_reserve_eur=_bounded_float(
            plan.available_reserve_eur,
            field="available_reserve_eur",
            minimum=0,
            maximum=1_000_000_000,
            digits=2,
        ),
        additional_cash_required_eur=_bounded_float(
            plan.additional_investment_cash_required_eur,
            field="additional_cash_required_eur",
            minimum=0,
            maximum=1_000_000_000,
            digits=2,
        ),
        positions=positions,
        policy=PolicyDecisionSnapshot.from_policy(data.policy),
    )


@dataclass(frozen=True, slots=True)
class EvaluationHistory:
    """Exactly the previous and current validated evaluations."""

    previous: EvaluationSnapshot | None = None
    current: EvaluationSnapshot | None = None

    @classmethod
    def from_dict(cls, raw: Any) -> EvaluationHistory:
        if not isinstance(raw, dict) or set(raw) != {"previous", "current"}:
            raise DecisionTraceError("Persisted evaluation history is invalid")
        previous = (
            None
            if raw["previous"] is None
            else EvaluationSnapshot.from_dict(raw["previous"])
        )
        current = (
            None
            if raw["current"] is None
            else EvaluationSnapshot.from_dict(raw["current"])
        )
        if previous is not None and current is None:
            raise DecisionTraceError("Evaluation history lacks a current snapshot")
        return cls(previous=previous, current=current)

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous": None if self.previous is None else self.previous.to_dict(),
            "current": None if self.current is None else self.current.to_dict(),
        }


def advance_history(
    history: EvaluationHistory,
    snapshot: EvaluationSnapshot,
) -> tuple[EvaluationHistory, bool]:
    """Advance only for a distinct validated evaluation."""
    if (
        history.current is not None
        and history.current.identity_sha256 == snapshot.identity_sha256
    ):
        return history, False
    return EvaluationHistory(previous=history.current, current=snapshot), True


def _position_change(
    previous: PositionDecisionSnapshot | None,
    current: PositionDecisionSnapshot | None,
) -> dict[str, Any] | None:
    template = current or previous
    if template is None:
        return None
    categories: list[str] = []
    reasons: list[str] = []

    if previous is None:
        categories.extend(("allocation", "recommendation"))
        reasons.append("position_added")
    elif current is None:
        categories.extend(("allocation", "recommendation"))
        reasons.append("position_removed")
    else:
        if previous.allocation_status != current.allocation_status:
            categories.append("allocation")
            reasons.append("allocation_status_changed")
            if current.allocation_status == "on_target":
                reasons.append("entered_target_corridor")
            elif previous.allocation_status == "on_target":
                reasons.append("left_target_corridor")
        elif abs(current.deviation_pp - previous.deviation_pp) >= MATERIAL_DRIFT_DELTA_PP:
            categories.append("allocation")
            reasons.append("material_drift_changed")

        purchase_delta = current.proposed_buy_eur - previous.proposed_buy_eur
        if previous.proposed_buy_eur <= 0 < current.proposed_buy_eur:
            categories.append("recommendation")
            reasons.append("proposed_purchase_added")
        elif previous.proposed_buy_eur > 0 >= current.proposed_buy_eur:
            categories.append("recommendation")
            reasons.append("proposed_purchase_removed")
        elif abs(purchase_delta) >= MATERIAL_MONEY_DELTA_EUR:
            categories.append("recommendation")
            reasons.append("proposed_purchase_changed")
        if previous.recommendation_reason != current.recommendation_reason:
            categories.append("recommendation")
            reasons.append("recommendation_reason_changed")
        if previous.execution_route != current.execution_route:
            categories.append("recommendation")
            reasons.append("execution_route_changed")
        if previous.execution_provider != current.execution_provider:
            categories.append("recommendation")
            reasons.append("execution_provider_changed")
        if previous.execution_state != current.execution_state:
            categories.append("recommendation")
            reasons.append("position_execution_state_changed")
        if previous.deferred != current.deferred:
            categories.append("recommendation")
            reasons.append("deferral_state_changed")

    categories = [item for item in CHANGE_CATEGORIES if item in categories]
    reasons = list(dict.fromkeys(reasons))[:MAX_TRACE_REASON_CODES]
    if not categories:
        return None

    return {
        "fund_id": template.fund_id,
        "fund_name": template.fund_name,
        "categories": categories,
        "reason_codes": reasons,
        "previous_allocation_status": (
            None if previous is None else previous.allocation_status
        ),
        "current_allocation_status": (
            None if current is None else current.allocation_status
        ),
        "previous_deviation_pp": None if previous is None else previous.deviation_pp,
        "current_deviation_pp": None if current is None else current.deviation_pp,
        "deviation_delta_pp": (
            None
            if previous is None or current is None
            else round(current.deviation_pp - previous.deviation_pp, 4)
        ),
        "previous_proposed_buy_eur": (
            None if previous is None else previous.proposed_buy_eur
        ),
        "current_proposed_buy_eur": (
            None if current is None else current.proposed_buy_eur
        ),
        "proposed_buy_delta_eur": (
            None
            if previous is None or current is None
            else round(current.proposed_buy_eur - previous.proposed_buy_eur, 2)
        ),
        "previous_recommendation_reason": (
            None if previous is None else previous.recommendation_reason
        ),
        "current_recommendation_reason": (
            None if current is None else current.recommendation_reason
        ),
        "previous_execution_provider": (
            None if previous is None else previous.execution_provider
        ),
        "current_execution_provider": (
            None if current is None else current.execution_provider
        ),
    }


def _policy_change(
    previous: PolicyDecisionSnapshot,
    current: PolicyDecisionSnapshot,
) -> dict[str, Any] | None:
    previous_findings = dict(previous.active_findings)
    current_findings = dict(current.active_findings)
    added = sorted(key for key in current_findings if key not in previous_findings)
    removed = sorted(key for key in previous_findings if key not in current_findings)
    changed = sorted(
        key
        for key in previous_findings.keys() & current_findings.keys()
        if previous_findings[key] != current_findings[key]
    )
    if previous == current:
        return None
    return {
        "previous_status": previous.status,
        "current_status": current.status,
        "previous_errors": previous.errors,
        "current_errors": current.errors,
        "previous_warnings": previous.warnings,
        "current_warnings": current.warnings,
        "previous_opportunities": previous.opportunities,
        "current_opportunities": current.opportunities,
        "previous_accepted_exceptions": previous.accepted_exceptions,
        "current_accepted_exceptions": current.accepted_exceptions,
        "added_findings": added,
        "removed_findings": removed,
        "changed_findings": changed,
    }


@dataclass(frozen=True, slots=True)
class PlanDelta:
    """Deterministic comparison of the two persisted evaluations."""

    state: str
    attributes: dict[str, Any]


def compare_history(history: EvaluationHistory) -> PlanDelta | None:
    """Return the bounded decision trace represented by a history."""
    current = history.current
    if current is None:
        return None
    previous = history.previous
    base: dict[str, Any] = {
        "contract_version": 1,
        "previous_evaluated_at": (
            None if previous is None else _utc_iso(previous.evaluated_at)
        ),
        "current_evaluated_at": _utc_iso(current.evaluated_at),
        "material_drift_delta_pp": MATERIAL_DRIFT_DELTA_PP,
        "material_purchase_delta_eur": MATERIAL_MONEY_DELTA_EUR,
    }
    if previous is None:
        return PlanDelta(
            state="baseline_established",
            attributes={
                **base,
                "change_categories": [],
                "position_change_count": 0,
                "position_changes": [],
            },
        )

    previous_positions = {item.fund_id: item for item in previous.positions}
    current_positions = {item.fund_id: item for item in current.positions}
    position_changes = [
        change
        for fund_id in sorted(previous_positions.keys() | current_positions.keys())
        if (
            change := _position_change(
                previous_positions.get(fund_id), current_positions.get(fund_id)
            )
        )
        is not None
    ]
    categories: list[str] = []
    if any("allocation" in item["categories"] for item in position_changes):
        categories.append("allocation")
    if any("recommendation" in item["categories"] for item in position_changes):
        categories.append("recommendation")

    execution_change: dict[str, Any] | None = None
    execution_material = (
        previous.execution_state != current.execution_state
        or previous.reserve_source != current.reserve_source
        or abs(current.available_reserve_eur - previous.available_reserve_eur)
        >= MATERIAL_MONEY_DELTA_EUR
        or abs(
            current.additional_cash_required_eur
            - previous.additional_cash_required_eur
        )
        >= MATERIAL_MONEY_DELTA_EUR
    )
    if execution_material:
        categories.append("execution")
        execution_change = {
            "previous_state": previous.execution_state,
            "current_state": current.execution_state,
            "previous_reserve_source": previous.reserve_source,
            "current_reserve_source": current.reserve_source,
            "previous_available_reserve_eur": previous.available_reserve_eur,
            "current_available_reserve_eur": current.available_reserve_eur,
            "available_reserve_delta_eur": round(
                current.available_reserve_eur - previous.available_reserve_eur, 2
            ),
            "previous_additional_cash_required_eur": (
                previous.additional_cash_required_eur
            ),
            "current_additional_cash_required_eur": (
                current.additional_cash_required_eur
            ),
        }

    policy_change = _policy_change(previous.policy, current.policy)
    if policy_change is not None:
        categories.append("policy")

    source_change: dict[str, Any] | None = None
    if (
        previous.source_provider != current.source_provider
        or previous.source_count != current.source_count
        or previous.source_conflict_count != current.source_conflict_count
    ):
        categories.append("source")
        source_change = {
            "previous_provider": previous.source_provider,
            "current_provider": current.source_provider,
            "previous_source_count": previous.source_count,
            "current_source_count": current.source_count,
            "previous_conflict_count": previous.source_conflict_count,
            "current_conflict_count": current.source_conflict_count,
        }

    categories = [item for item in CHANGE_CATEGORIES if item in categories]
    if not categories:
        state = "unchanged"
    elif len(categories) > 1:
        state = "multiple_changes"
    else:
        state = {
            "allocation": "allocation_changed",
            "recommendation": "recommendation_changed",
            "execution": "execution_state_changed",
            "policy": "policy_changed",
            "source": "source_changed",
        }[categories[0]]

    attributes = {
        **base,
        "change_categories": categories,
        "position_change_count": len(position_changes),
        "allocation_change_count": sum(
            "allocation" in item["categories"] for item in position_changes
        ),
        "recommendation_change_count": sum(
            "recommendation" in item["categories"] for item in position_changes
        ),
        "position_changes": position_changes,
    }
    if execution_change is not None:
        attributes["execution_change"] = execution_change
    if policy_change is not None:
        attributes["policy_change"] = policy_change
    if source_change is not None:
        attributes["source_change"] = source_change
    _canonical_sha256(attributes)
    return PlanDelta(state=state, attributes=attributes)
