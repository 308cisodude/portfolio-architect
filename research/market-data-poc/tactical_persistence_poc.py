#!/usr/bin/env python3
"""Portfolio Architect Tactical Tilt persistence PoC.

Standalone, advisory-only research tool for cadence-aware Tactical Tilt memory.
It replays *planning-cycle* observations and can also maintain an idempotent
research event log. Daily market-data refreshes are not accepted as governance
events and therefore cannot increment persistence.

Persistent weakness may suppress Tactical Tilt for a target and request a
human strategic review. Execution evidence is audit-only; recommendations create
no tactical debt. The PoC never replaces a target, sells, buys, or mutates PA.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "0.3.1"
EPS = 1e-9

# Research qualification constants. A planning-cycle observation only advances
# the persistence episode when rebound-aware Tactical Tilt weakness is material
# AND there is medium-horizon market-history support. These are deliberately
# transparent PoC hypotheses, not production policy.
MIN_STRESS_SIGNAL = 0.35
MIN_RETURN_20D = -0.03
MIN_DRAWDOWN_20D = -0.05

# Cadence-aware research thresholds. Review requires both the minimum number of
# independent PA planning-cycle observations and the minimum wall-clock span.
# This deliberately makes three weekly observations very different from three
# monthly observations, and gives quarterly/yearly observations more weight.
CADENCE_POLICY: dict[str, dict[str, int]] = {
    "weekly": {
        "watch_cycles": 4,
        "watch_elapsed_days": 21,
        "review_cycles": 9,
        "review_elapsed_days": 56,
    },
    "monthly": {
        "watch_cycles": 2,
        "watch_elapsed_days": 28,
        "review_cycles": 3,
        "review_elapsed_days": 56,
    },
    "quarterly": {
        "watch_cycles": 2,
        "watch_elapsed_days": 0,
        "review_cycles": 2,
        "review_elapsed_days": 75,
    },
    "yearly": {
        "watch_cycles": 2,
        "watch_elapsed_days": 0,
        "review_cycles": 2,
        "review_elapsed_days": 330,
    },
}


class PersistenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class CycleObservation:
    cycle_date: date
    tactical_signal: float
    return_5d: float
    return_20d: float
    drawdown_from_20d_high: float
    recovered_since_previous_cycle: bool
    selected_by_tt: bool | None
    note: str | None

    @property
    def market_history_support(self) -> bool:
        return (
            self.return_20d <= MIN_RETURN_20D + EPS
            or self.drawdown_from_20d_high <= MIN_DRAWDOWN_20D + EPS
        )

    @property
    def stress_qualified(self) -> bool:
        return self.tactical_signal + EPS >= MIN_STRESS_SIGNAL and self.market_history_support


@dataclass(frozen=True)
class TargetHistory:
    scenario_id: str
    description: str
    plan_frequency: str
    isin: str
    name: str
    observations: tuple[CycleObservation, ...]


def _finite_number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PersistenceError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise PersistenceError(f"{field} must be finite")
    return number


def _parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise PersistenceError(f"{field} must be ISO date YYYY-MM-DD") from exc


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PersistenceError(f"cannot read JSON: {path}") from exc


def load_scenarios(path: Path) -> list[TargetHistory]:
    raw = _load_json(path)
    if not isinstance(raw, dict) or raw.get("schema") != 1:
        raise PersistenceError("persistence scenario set must be schema 1")
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise PersistenceError("scenarios must be a non-empty array")

    result: list[TargetHistory] = []
    seen_ids: set[str] = set()
    for sidx, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise PersistenceError(f"scenarios[{sidx}] must be an object")
        scenario_id = str(scenario.get("id", "")).strip()
        description = str(scenario.get("description", "")).strip()
        plan_frequency = str(scenario.get("plan_frequency", "")).strip().lower()
        if not scenario_id:
            raise PersistenceError(f"scenarios[{sidx}].id is empty")
        if scenario_id in seen_ids:
            raise PersistenceError(f"duplicate scenario id: {scenario_id}")
        if plan_frequency not in CADENCE_POLICY:
            raise PersistenceError(
                f"scenarios[{sidx}].plan_frequency must be one of "
                + ", ".join(CADENCE_POLICY)
            )
        target = scenario.get("target")
        if not isinstance(target, dict):
            raise PersistenceError(f"scenarios[{sidx}].target must be an object")
        isin = str(target.get("isin", "")).strip().upper()
        name = str(target.get("name", "")).strip()
        if len(isin) != 12 or not isin.isalnum():
            raise PersistenceError(f"scenarios[{sidx}].target.isin is invalid")
        if not name:
            raise PersistenceError(f"scenarios[{sidx}].target.name is empty")
        raw_observations = scenario.get("observations")
        if not isinstance(raw_observations, list) or not raw_observations:
            raise PersistenceError(f"scenarios[{sidx}].observations must be non-empty")

        observations: list[CycleObservation] = []
        seen_dates: set[date] = set()
        previous_date: date | None = None
        for oidx, item in enumerate(raw_observations):
            if not isinstance(item, dict):
                raise PersistenceError(
                    f"scenarios[{sidx}].observations[{oidx}] must be an object"
                )
            cycle_date = _parse_date(
                item.get("cycle_date"),
                f"scenarios[{sidx}].observations[{oidx}].cycle_date",
            )
            if cycle_date in seen_dates:
                raise PersistenceError(
                    f"scenario {scenario_id} has more than one observation for {cycle_date}; "
                    "persistence advances once per PA planning cycle"
                )
            if previous_date is not None and cycle_date <= previous_date:
                raise PersistenceError(
                    f"scenario {scenario_id} observations must be strictly chronological"
                )
            tactical_signal = _finite_number(
                item.get("tactical_signal"),
                f"scenarios[{sidx}].observations[{oidx}].tactical_signal",
            )
            if tactical_signal < 0 or tactical_signal > 1:
                raise PersistenceError("tactical_signal must be between 0 and 1")
            r5 = _finite_number(
                item.get("return_5d"),
                f"scenarios[{sidx}].observations[{oidx}].return_5d",
            )
            r20 = _finite_number(
                item.get("return_20d"),
                f"scenarios[{sidx}].observations[{oidx}].return_20d",
            )
            drawdown = _finite_number(
                item.get("drawdown_from_20d_high"),
                f"scenarios[{sidx}].observations[{oidx}].drawdown_from_20d_high",
            )
            recovered = item.get("recovered_since_previous_cycle", False)
            if not isinstance(recovered, bool):
                raise PersistenceError("recovered_since_previous_cycle must be boolean")
            selected = item.get("selected_by_tt")
            if selected is not None and not isinstance(selected, bool):
                raise PersistenceError("selected_by_tt must be boolean or null")
            note_raw = item.get("note")
            note = None if note_raw is None else str(note_raw).strip() or None
            observations.append(
                CycleObservation(
                    cycle_date=cycle_date,
                    tactical_signal=tactical_signal,
                    return_5d=r5,
                    return_20d=r20,
                    drawdown_from_20d_high=drawdown,
                    recovered_since_previous_cycle=recovered,
                    selected_by_tt=selected,
                    note=note,
                )
            )
            seen_dates.add(cycle_date)
            previous_date = cycle_date

        seen_ids.add(scenario_id)
        result.append(
            TargetHistory(
                scenario_id=scenario_id,
                description=description,
                plan_frequency=plan_frequency,
                isin=isin,
                name=name,
                observations=tuple(observations),
            )
        )
    return result


def _episode_summary(observations: list[CycleObservation]) -> dict[str, Any]:
    if not observations:
        raise PersistenceError("cannot summarize empty episode")
    start = observations[0].cycle_date
    end = observations[-1].cycle_date
    selected_count = sum(obs.selected_by_tt is True for obs in observations)
    return {
        "started": start.isoformat(),
        "last_observed": end.isoformat(),
        "elapsed_days": (end - start).days,
        "stressed_planning_cycles": len(observations),
        "selected_by_tt_cycles": selected_count,
        "peak_tactical_signal": max(obs.tactical_signal for obs in observations),
        "latest_tactical_signal": observations[-1].tactical_signal,
        "worst_return_20d": min(obs.return_20d for obs in observations),
        "worst_drawdown_from_20d_high": min(
            obs.drawdown_from_20d_high for obs in observations
        ),
    }


def _governance_state(
    frequency: str, active_episode: list[CycleObservation]
) -> tuple[str, str]:
    if not active_episode:
        return "normal", "no_active_qualified_weakness_episode"
    policy = CADENCE_POLICY[frequency]
    summary = _episode_summary(active_episode)
    cycles = int(summary["stressed_planning_cycles"])
    elapsed = int(summary["elapsed_days"])

    if (
        cycles >= policy["review_cycles"]
        and elapsed >= policy["review_elapsed_days"]
    ):
        return "strategic_review_due", "cadence_adjusted_persistence_threshold_crossed"
    if (
        cycles >= policy["watch_cycles"]
        and elapsed >= policy["watch_elapsed_days"]
    ):
        return "tactical_watch", "cadence_adjusted_watch_threshold_crossed"
    return "tactical_opportunity", "qualified_weakness_below_watch_threshold"


def evaluate_history(history: TargetHistory) -> dict[str, Any]:
    """Replay one target's independent PA planning-cycle observations."""
    active_episode: list[CycleObservation] = []
    closed_episodes: list[dict[str, Any]] = []
    observation_rows: list[dict[str, Any]] = []

    def close_active(reason: str, closed_on: date) -> None:
        nonlocal active_episode
        if not active_episode:
            return
        summary = _episode_summary(active_episode)
        summary["closed_reason"] = reason
        summary["closed_on"] = closed_on.isoformat()
        closed_episodes.append(summary)
        active_episode = []

    for obs in history.observations:
        # A recovery between cycles splits episodes even if the asset has become
        # weak again by the next PA cycle. This prevents one long-lived counter
        # from spanning distinct market events.
        if obs.recovered_since_previous_cycle:
            close_active("recovered_between_planning_cycles", obs.cycle_date)

        qualified = obs.stress_qualified
        if qualified:
            active_episode.append(obs)
        else:
            close_active("weakness_not_qualified_at_planning_cycle", obs.cycle_date)

        state, reason = _governance_state(history.plan_frequency, active_episode)
        active_summary = _episode_summary(active_episode) if active_episode else None
        observation_rows.append(
            {
                "cycle_date": obs.cycle_date.isoformat(),
                "tactical_signal": obs.tactical_signal,
                "return_5d": obs.return_5d,
                "return_20d": obs.return_20d,
                "drawdown_from_20d_high": obs.drawdown_from_20d_high,
                "market_history_support": obs.market_history_support,
                "stress_qualified": qualified,
                "recovered_since_previous_cycle": obs.recovered_since_previous_cycle,
                "selected_by_tt": obs.selected_by_tt,
                "state_after_cycle": state,
                "state_reason": reason,
                "active_episode_stressed_cycles": (
                    active_summary["stressed_planning_cycles"] if active_summary else 0
                ),
                "active_episode_elapsed_days": (
                    active_summary["elapsed_days"] if active_summary else 0
                ),
                "note": obs.note,
            }
        )

    state, reason = _governance_state(history.plan_frequency, active_episode)
    active_summary = _episode_summary(active_episode) if active_episode else None
    review_due = state == "strategic_review_due"
    return {
        "scenario_id": history.scenario_id,
        "description": history.description,
        "plan_frequency": history.plan_frequency,
        "target": {"isin": history.isin, "name": history.name},
        "qualification_policy": {
            "minimum_rebound_aware_signal": MIN_STRESS_SIGNAL,
            "market_history_support": {
                "return_20d_lte": MIN_RETURN_20D,
                "or_drawdown_from_20d_high_lte": MIN_DRAWDOWN_20D,
            },
        },
        "cadence_policy": CADENCE_POLICY[history.plan_frequency],
        "final_state": state,
        "final_reason": reason,
        "tactical_bonus_allowed": not review_due,
        "tactical_bonus_multiplier": 0.0 if review_due else 1.0,
        "human_strategic_review_required": review_due,
        "automatic_target_replacement": False,
        "automatic_sell": False,
        "active_episode": active_summary,
        "closed_episode_count": len(closed_episodes),
        "closed_episodes": closed_episodes,
        "observations": observation_rows,
    }


def evaluate_scenarios(histories: list[TargetHistory]) -> dict[str, Any]:
    return {
        "prototype_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "research-only cadence-aware Tactical Tilt persistence",
        "governance_boundary": {
            "state_advances_on": "independent_PA_planning_cycles_only",
            "daily_market_refreshes_increment_state": False,
            "strategic_review_is_advisory": True,
            "human_target_authority": True,
            "automatic_target_replacement": False,
        },
        "cadence_policy": CADENCE_POLICY,
        "qualification_policy": {
            "minimum_rebound_aware_signal": MIN_STRESS_SIGNAL,
            "market_history_support": {
                "return_20d_lte": MIN_RETURN_20D,
                "or_drawdown_from_20d_high_lte": MIN_DRAWDOWN_20D,
            },
            "note": "research constants; not production policy",
        },
        "scenarios": [evaluate_history(history) for history in histories],
    }


def render_report(document: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("Portfolio Architect Tactical Tilt persistence PoC")
    lines.append(f"prototype_version: {document['prototype_version']}")
    lines.append(f"generated_at: {document['generated_at']}")
    lines.append("")
    lines.append("SCOPE")
    lines.append("  Governance state advances only on independent PA planning cycles.")
    lines.append("  Daily market refreshes may update evidence but do not increment persistence.")
    lines.append("  Strategic review is advisory; target replacement remains a human decision.")
    lines.append("")
    lines.append("STRESS QUALIFICATION (research constants)")
    q = document["qualification_policy"]
    lines.append(
        f"  rebound-aware signal >= {q['minimum_rebound_aware_signal']:.2f}"
    )
    support = q["market_history_support"]
    lines.append(
        "  AND market-history support: "
        f"20d return <= {support['return_20d_lte']:+.1%} "
        f"OR drawdown <= {support['or_drawdown_from_20d_high_lte']:+.1%}"
    )
    lines.append("")
    lines.append("CADENCE POLICY (research thresholds)")
    lines.append("  Frequency    Watch threshold      Strategic-review threshold")
    for frequency in ("weekly", "monthly", "quarterly", "yearly"):
        p = document["cadence_policy"][frequency]
        lines.append(
            f"  {frequency:<10}  {p['watch_cycles']:>2} cycles / {p['watch_elapsed_days']:>3}d"
            f"       {p['review_cycles']:>2} cycles / {p['review_elapsed_days']:>3}d"
        )
    lines.append("")
    lines.append("SCENARIO RESULTS")
    for scenario in document["scenarios"]:
        target = scenario["target"]
        active = scenario["active_episode"]
        lines.append(
            f"  {scenario['scenario_id']} [{scenario['plan_frequency']}]"
        )
        lines.append(f"    target: {target['isin']}  {target['name']}")
        if scenario.get("description"):
            lines.append(f"    description: {scenario['description']}")
        lines.append(
            f"    final_state: {scenario['final_state']}  reason={scenario['final_reason']}"
        )
        if active:
            lines.append(
                "    active_episode: "
                f"{active['stressed_planning_cycles']} stressed cycles / "
                f"{active['elapsed_days']} days / "
                f"signal latest={active['latest_tactical_signal']:.3f} "
                f"peak={active['peak_tactical_signal']:.3f}"
            )
            lines.append(
                "    evidence: "
                f"worst 20d={active['worst_return_20d']:+.2%}  "
                f"worst drawdown={active['worst_drawdown_from_20d_high']:+.2%}"
            )
        else:
            lines.append("    active_episode: none")
        lines.append(
            f"    closed_episodes: {scenario['closed_episode_count']}  "
            f"tactical_bonus_allowed={scenario['tactical_bonus_allowed']}  "
            f"human_review_required={scenario['human_strategic_review_required']}"
        )
        lines.append("")
    lines.append("INTERPRETATION")
    lines.append("  Counts are cadence-aware and wall-clock-aware; there is no universal N-cycle rule.")
    lines.append("  Recovery closes an episode so separate dips do not accumulate as one event.")
    lines.append("  Once strategic review is due, TT becomes neutral for that target.")
    lines.append("  PA may present evidence and request review, but must not replace or sell a target automatically.")
    return "\n".join(lines) + "\n"


def replay(scenarios_path: Path, output_dir: Path) -> dict[str, Any]:
    histories = load_scenarios(scenarios_path)
    document = evaluate_scenarios(histories)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "persistence.json"
    report_path = output_dir / "persistence_report.txt"
    json_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_path.write_text(render_report(document), encoding="utf-8")
    return document



@dataclass(frozen=True)
class StateCycleEvent:
    """One idempotent PA-cycle governance event for one configured target role."""

    plan_id: str
    cycle_effective_date: date
    plan_frequency: str
    target_id: str
    isin: str
    name: str
    tactical_signal: float
    return_5d: float
    return_20d: float
    drawdown_from_20d_high: float
    recovered_since_previous_cycle: bool
    selected_by_tt: bool | None
    execution_outcome: str | None
    note: str | None

    @property
    def cycle_identity(self) -> dict[str, str]:
        return {
            "plan_id": self.plan_id,
            "cycle_effective_date": self.cycle_effective_date.isoformat(),
            "plan_frequency": self.plan_frequency,
            "target_id": self.target_id,
            "isin": self.isin,
        }

    @property
    def cycle_slot(self) -> tuple[str, str, str]:
        # A configured target role can produce only one governance observation
        # for one effective PA cycle. Frequency/ISIN changes in the same slot
        # are therefore conflicts, not a second independent observation.
        return (
            self.plan_id,
            self.cycle_effective_date.isoformat(),
            self.target_id,
        )

    def to_cycle_observation(self) -> CycleObservation:
        return CycleObservation(
            cycle_date=self.cycle_effective_date,
            tactical_signal=self.tactical_signal,
            return_5d=self.return_5d,
            return_20d=self.return_20d,
            drawdown_from_20d_high=self.drawdown_from_20d_high,
            recovered_since_previous_cycle=self.recovered_since_previous_cycle,
            selected_by_tt=self.selected_by_tt,
            note=self.note,
        )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _event_governance_payload(event: StateCycleEvent) -> dict[str, Any]:
    """Fields that are allowed to advance or change governance state."""
    return {
        "cycle_identity": event.cycle_identity,
        "tactical_signal": event.tactical_signal,
        "return_5d": event.return_5d,
        "return_20d": event.return_20d,
        "drawdown_from_20d_high": event.drawdown_from_20d_high,
        "recovered_since_previous_cycle": event.recovered_since_previous_cycle,
    }


def _event_audit_payload(event: StateCycleEvent) -> dict[str, Any]:
    """Audit-only fields; none of these may influence governance state."""
    return {
        "selected_by_tt": event.selected_by_tt,
        "execution_outcome": event.execution_outcome,
        "note": event.note,
    }


def _event_to_record(event: StateCycleEvent) -> dict[str, Any]:
    return {
        **event.cycle_identity,
        "name": event.name,
        "tactical_signal": event.tactical_signal,
        "return_5d": event.return_5d,
        "return_20d": event.return_20d,
        "drawdown_from_20d_high": event.drawdown_from_20d_high,
        "recovered_since_previous_cycle": event.recovered_since_previous_cycle,
        **_event_audit_payload(event),
    }


def _event_from_record(record: dict[str, Any], field: str = "event") -> StateCycleEvent:
    if not isinstance(record, dict):
        raise PersistenceError(f"{field} must be an object")
    plan_id = str(record.get("plan_id", "")).strip()
    target_id = str(record.get("target_id", "")).strip()
    frequency = str(record.get("plan_frequency", "")).strip().lower()
    isin = str(record.get("isin", "")).strip().upper()
    name = str(record.get("name", "")).strip()
    if not plan_id:
        raise PersistenceError(f"{field}.plan_id is empty")
    if not target_id:
        raise PersistenceError(f"{field}.target_id is empty")
    if frequency not in CADENCE_POLICY:
        raise PersistenceError(
            f"{field}.plan_frequency must be one of " + ", ".join(CADENCE_POLICY)
        )
    if len(isin) != 12 or not isin.isalnum():
        raise PersistenceError(f"{field}.isin is invalid")
    if not name:
        raise PersistenceError(f"{field}.name is empty")
    cycle_date = _parse_date(record.get("cycle_effective_date"), f"{field}.cycle_effective_date")
    signal = _finite_number(record.get("tactical_signal"), f"{field}.tactical_signal")
    if signal < 0 or signal > 1:
        raise PersistenceError(f"{field}.tactical_signal must be between 0 and 1")
    r5 = _finite_number(record.get("return_5d"), f"{field}.return_5d")
    r20 = _finite_number(record.get("return_20d"), f"{field}.return_20d")
    drawdown = _finite_number(
        record.get("drawdown_from_20d_high"), f"{field}.drawdown_from_20d_high"
    )
    recovered = record.get("recovered_since_previous_cycle", False)
    if not isinstance(recovered, bool):
        raise PersistenceError(f"{field}.recovered_since_previous_cycle must be boolean")
    selected = record.get("selected_by_tt")
    if selected is not None and not isinstance(selected, bool):
        raise PersistenceError(f"{field}.selected_by_tt must be boolean or null")
    outcome = record.get("execution_outcome")
    if outcome is not None:
        outcome = str(outcome).strip().lower()
        if outcome not in {"followed", "partial", "not_followed"}:
            raise PersistenceError(
                f"{field}.execution_outcome must be followed, partial, not_followed, or null"
            )
    note_raw = record.get("note")
    note = None if note_raw is None else str(note_raw).strip() or None
    return StateCycleEvent(
        plan_id=plan_id,
        cycle_effective_date=cycle_date,
        plan_frequency=frequency,
        target_id=target_id,
        isin=isin,
        name=name,
        tactical_signal=signal,
        return_5d=r5,
        return_20d=r20,
        drawdown_from_20d_high=drawdown,
        recovered_since_previous_cycle=recovered,
        selected_by_tt=selected,
        execution_outcome=outcome,
        note=note,
    )


def load_state_events(path: Path) -> list[StateCycleEvent]:
    raw = _load_json(path)
    if not isinstance(raw, dict) or raw.get("schema") != 1:
        raise PersistenceError("persistence event set must be schema 1")
    items = raw.get("events")
    if not isinstance(items, list) or not items:
        raise PersistenceError("events must be a non-empty array")
    return [_event_from_record(item, f"events[{idx}]") for idx, item in enumerate(items)]


def empty_persistence_state() -> dict[str, Any]:
    # Deliberately an event log. Replaying the same canonical log must reconstruct
    # the same governance state after a restart. There is no tactical-debt field.
    return {"schema": 1, "prototype_version": VERSION, "events": []}


def load_persistence_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_persistence_state()
    raw = _load_json(path)
    if not isinstance(raw, dict) or raw.get("schema") != 1:
        raise PersistenceError("persistence state must be schema 1")
    items = raw.get("events")
    if not isinstance(items, list):
        raise PersistenceError("persistence state events must be an array")
    # Validate and normalize every persisted event while preserving log order.
    normalized = [_event_to_record(_event_from_record(item, f"state.events[{idx}]")) for idx, item in enumerate(items)]
    return {"schema": 1, "prototype_version": VERSION, "events": normalized}


def save_persistence_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _governance_record_payload(record: dict[str, Any]) -> dict[str, Any]:
    return _event_governance_payload(_event_from_record(record, "state event"))


def _merge_audit_value(existing: Any, incoming: Any, field: str) -> tuple[Any, bool]:
    if incoming is None or incoming == existing:
        return existing, False
    if existing is None:
        return incoming, True
    raise PersistenceError(f"conflicting audit evidence for {field}")


def apply_state_event(state: dict[str, Any], event: StateCycleEvent) -> str:
    """Apply one cycle event idempotently.

    Returns ``applied``, ``audit_enriched``, or ``duplicate_noop``. Exact replay
    never advances persistence twice. Audit-only execution evidence can be added
    later without creating another governance observation.
    """
    if state.get("schema") != 1 or not isinstance(state.get("events"), list):
        raise PersistenceError("invalid persistence state")
    records: list[dict[str, Any]] = state["events"]
    slot = event.cycle_slot
    for record in records:
        existing = _event_from_record(record, "state event")
        if existing.cycle_slot != slot:
            continue
        if _governance_record_payload(record) != _event_governance_payload(event):
            raise PersistenceError(
                "conflicting governance evidence for existing PA cycle slot; "
                "a cycle may advance persistence only once"
            )
        changed = False
        for field, incoming in _event_audit_payload(event).items():
            merged, field_changed = _merge_audit_value(record.get(field), incoming, field)
            if field_changed:
                record[field] = merged
                changed = True
        if not record.get("name") and event.name:
            record["name"] = event.name
            changed = True
        return "audit_enriched" if changed else "duplicate_noop"

    # Within one configured target role, later independent cycles must be strictly
    # chronological. Cadence or instrument replacement is permitted only on a new
    # cycle and is handled as a segment boundary during evaluation.
    prior_dates = [
        _parse_date(r["cycle_effective_date"], "state cycle_effective_date")
        for r in records
        if r.get("plan_id") == event.plan_id and r.get("target_id") == event.target_id
    ]
    if prior_dates and event.cycle_effective_date <= max(prior_dates):
        raise PersistenceError(
            "new persistence event must be later than the existing cycle for this plan/target role"
        )
    records.append(_event_to_record(event))
    return "applied"


def _state_digest(state: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(state).encode("utf-8")).hexdigest()


def _evaluate_segment(
    plan_id: str,
    target_id: str,
    events: list[StateCycleEvent],
    *,
    terminated_by: str | None,
) -> dict[str, Any]:
    first = events[0]
    history = TargetHistory(
        scenario_id=f"{plan_id}:{target_id}:{first.isin}:{first.plan_frequency}",
        description="stateful persistence segment",
        plan_frequency=first.plan_frequency,
        isin=first.isin,
        name=first.name,
        observations=tuple(event.to_cycle_observation() for event in events),
    )
    result = evaluate_history(history)
    result["plan_id"] = plan_id
    result["target_id"] = target_id
    result["started"] = events[0].cycle_effective_date.isoformat()
    result["last_cycle"] = events[-1].cycle_effective_date.isoformat()
    result["terminated_by"] = terminated_by
    result["execution_audit"] = {
        "followed": sum(e.execution_outcome == "followed" for e in events),
        "partial": sum(e.execution_outcome == "partial" for e in events),
        "not_followed": sum(e.execution_outcome == "not_followed" for e in events),
        "unknown": sum(e.execution_outcome is None for e in events),
        "governance_effect": "none",
    }
    return result


def evaluate_persistence_state(state: dict[str, Any]) -> dict[str, Any]:
    records = state.get("events")
    if state.get("schema") != 1 or not isinstance(records, list):
        raise PersistenceError("invalid persistence state")
    events = [_event_from_record(record, f"state.events[{idx}]") for idx, record in enumerate(records)]

    role_order: list[tuple[str, str]] = []
    by_role: dict[tuple[str, str], list[StateCycleEvent]] = {}
    for event in events:
        key = (event.plan_id, event.target_id)
        if key not in by_role:
            by_role[key] = []
            role_order.append(key)
        by_role[key].append(event)

    roles: list[dict[str, Any]] = []
    for plan_id, target_id in role_order:
        role_events = by_role[(plan_id, target_id)]
        segments: list[list[StateCycleEvent]] = []
        current: list[StateCycleEvent] = []
        for event in role_events:
            if current and (
                event.isin != current[-1].isin
                or event.plan_frequency != current[-1].plan_frequency
            ):
                segments.append(current)
                current = []
            current.append(event)
        if current:
            segments.append(current)

        evaluated_segments: list[dict[str, Any]] = []
        for idx, segment in enumerate(segments):
            terminated_by: str | None = None
            if idx + 1 < len(segments):
                next_segment = segments[idx + 1]
                if next_segment[0].isin != segment[-1].isin:
                    terminated_by = "target_replaced"
                else:
                    terminated_by = "plan_frequency_changed"
            evaluated_segments.append(
                _evaluate_segment(
                    plan_id,
                    target_id,
                    segment,
                    terminated_by=terminated_by,
                )
            )

        active_segment = evaluated_segments[-1]
        roles.append(
            {
                "plan_id": plan_id,
                "target_id": target_id,
                "active_target": active_segment["target"],
                "current_plan_frequency": active_segment["plan_frequency"],
                "final_state": active_segment["final_state"],
                "final_reason": active_segment["final_reason"],
                "tactical_bonus_allowed": active_segment["tactical_bonus_allowed"],
                "human_strategic_review_required": active_segment[
                    "human_strategic_review_required"
                ],
                "segment_count": len(evaluated_segments),
                "segments": evaluated_segments,
            }
        )

    return {
        "prototype_version": VERSION,
        "state_schema": 1,
        "state_sha256": _state_digest(state),
        "event_count": len(events),
        "contract": {
            "cycle_identity_fields": [
                "plan_id",
                "cycle_effective_date",
                "plan_frequency",
                "target_id",
                "isin",
            ],
            "cycle_replay_is_idempotent": True,
            "execution_evidence_affects_governance": False,
            "unexecuted_recommendation_creates_tactical_debt": False,
            "next_cycle_scoring_uses_current_authoritative_holdings": True,
            "persistence_tracks_qualified_weakness_not_recommendation_compliance": True,
            "cadence_change_reinterprets_old_cycles": False,
            "cadence_change_starts_new_governance_segment": True,
            "target_replacement_inherits_old_asset_stress": False,
            "restart_replay_must_be_deterministic": True,
        },
        "roles": roles,
    }


def render_state_report(document: dict[str, Any], action_counts: dict[str, int]) -> str:
    lines: list[str] = []
    lines.append("Portfolio Architect Tactical Tilt persistence contract PoC")
    lines.append(f"prototype_version: {document['prototype_version']}")
    lines.append(f"state_sha256: {document['state_sha256']}")
    lines.append(f"event_count: {document['event_count']}")
    lines.append("")
    lines.append("APPLY RESULT")
    for action in ("applied", "audit_enriched", "duplicate_noop"):
        lines.append(f"  {action}: {action_counts.get(action, 0)}")
    lines.append("")
    lines.append("CONTRACT")
    c = document["contract"]
    lines.append(
        "  cycle identity: " + ", ".join(c["cycle_identity_fields"])
    )
    lines.append("  exact cycle replay: idempotent")
    lines.append("  execution evidence: audit-only; governance effect = none")
    lines.append("  unexecuted recommendation: no tactical debt")
    lines.append("  next cycle: current authoritative holdings are the scoring input")
    lines.append("  cadence change: historical segment retained; new cadence starts clean")
    lines.append("  target replacement: old instrument evidence retained; replacement starts clean")
    lines.append("  restart/replay: deterministic event-log reconstruction required")
    lines.append("")
    lines.append("ROLE STATES")
    for role in document["roles"]:
        active = role["active_target"]
        lines.append(f"  {role['plan_id']} / {role['target_id']}")
        lines.append(
            f"    active: {active['isin']}  frequency={role['current_plan_frequency']}"
        )
        lines.append(
            f"    state: {role['final_state']}  tactical_bonus_allowed={role['tactical_bonus_allowed']}"
        )
        lines.append(f"    segments: {role['segment_count']}")
        for idx, segment in enumerate(role["segments"], start=1):
            lines.append(
                f"      {idx}. {segment['target']['isin']} [{segment['plan_frequency']}] "
                f"{segment['started']}..{segment['last_cycle']} -> {segment['final_state']}"
            )
            if segment["terminated_by"]:
                lines.append(f"         terminated_by: {segment['terminated_by']}")
            audit = segment["execution_audit"]
            lines.append(
                "         execution audit: "
                f"followed={audit['followed']} partial={audit['partial']} not_followed={audit['not_followed']} "
                f"unknown={audit['unknown']} governance_effect={audit['governance_effect']}"
            )
        lines.append("")
    lines.append("INTERPRETATION")
    lines.append("  Recommendations create no obligation and no tactical debt.")
    lines.append("  Not following TT does not erase or increase target stress history.")
    lines.append("  A new PA cycle always recomputes from current authoritative portfolio state.")
    lines.append("  Historical weakness evidence remains auditable across cadence changes and target replacement.")
    return "\n".join(lines) + "\n"


def state_replay(
    events_path: Path,
    state_path: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, int]]:
    state = load_persistence_state(state_path)
    events = load_state_events(events_path)
    action_counts = {"applied": 0, "audit_enriched": 0, "duplicate_noop": 0}
    for event in events:
        action = apply_state_event(state, event)
        action_counts[action] += 1
    save_persistence_state(state_path, state)

    # Restart/reload proof: the persisted event log must derive the same state.
    reloaded = load_persistence_state(state_path)
    document = evaluate_persistence_state(reloaded)
    if document != evaluate_persistence_state(state):
        raise PersistenceError("restart/replay changed derived governance state")

    # Idempotency proof: replaying the exact batch again must not change the
    # persisted governance log. Audit enrichments have already been absorbed.
    replay_copy = copy.deepcopy(reloaded)
    before = _canonical_json(replay_copy)
    for event in events:
        apply_state_event(replay_copy, event)
    if _canonical_json(replay_copy) != before:
        raise PersistenceError("replaying the same PA cycles changed persistence state")

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "persistence_contract.json"
    report_path = output_dir / "persistence_contract_report.txt"
    json_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_path.write_text(render_state_report(document, action_counts), encoding="utf-8")
    return document, action_counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    replay_parser = sub.add_parser(
        "replay", help="replay cadence-aware planning-cycle persistence scenarios"
    )
    replay_parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("examples/persistence_scenarios.json"),
        help="schema-1 scenario set",
    )
    replay_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/tactical_tilt"),
        help="output directory",
    )
    state_parser = sub.add_parser(
        "state-replay",
        help="apply idempotent PA-cycle events to a persisted research event log",
    )
    state_parser.add_argument(
        "--events",
        type=Path,
        default=Path("examples/persistence_contract_events.json"),
        help="schema-1 cycle-event set",
    )
    state_parser.add_argument(
        "--state",
        type=Path,
        default=Path("output/tactical_tilt/persistence_state.json"),
        help="persisted research state file",
    )
    state_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/tactical_tilt"),
        help="output directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "replay":
            document = replay(args.scenarios, args.output_dir)
            print(f"scenarios: {len(document['scenarios'])}")
            for scenario in document["scenarios"]:
                active = scenario["active_episode"]
                active_text = (
                    f"{active['stressed_planning_cycles']} cycles/{active['elapsed_days']}d"
                    if active
                    else "no active episode"
                )
                print(
                    f"{scenario['scenario_id']}: {scenario['final_state']} "
                    f"({active_text}) tactical_bonus_allowed={scenario['tactical_bonus_allowed']}"
                )
            print(f"report: {args.output_dir / 'persistence_report.txt'}")
            return 0
        if args.command == "state-replay":
            document, counts = state_replay(args.events, args.state, args.output_dir)
            print(
                "events: "
                f"applied={counts['applied']} audit_enriched={counts['audit_enriched']} "
                f"duplicate_noop={counts['duplicate_noop']} total_state={document['event_count']}"
            )
            for role in document["roles"]:
                print(
                    f"{role['plan_id']}/{role['target_id']}: {role['final_state']} "
                    f"segments={role['segment_count']} "
                    f"active={role['active_target']['isin']}"
                )
            print(f"state: {args.state}")
            print(f"report: {args.output_dir / 'persistence_contract_report.txt'}")
            return 0
        raise PersistenceError(f"unsupported command: {args.command}")
    except PersistenceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
