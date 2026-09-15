#!/usr/bin/env python3
"""Portfolio Architect Tactical Tilt PoC.

Standalone, advisory-only research tool. It consumes an allocation snapshot and
an already-generated Market Data PoC ``market_context.json`` and compares a
strategic allocation-only baseline with several bounded Tactical Tilt models.

It does not call external APIs, modify Portfolio Architect, or place trades.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "0.3.1"
DEFAULT_TILT_BUDGET_PCT = 10.0
DEFAULT_TIE_BAND_PCT = 10.0
DEFAULT_MAX_MARKET_AGE_DAYS = 4
DEFAULT_CALIBRATION_SWEEP_PCTS = (0.0, 25.0, 50.0, 75.0, 100.0, 125.0, 150.0, 175.0, 200.0)
REFERENCE_TACTICAL_BONUS_CEILING_PCT = 150.0
DEFAULT_SURFACE_GAP_PCTS = (2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0)
DEFAULT_SURFACE_SIGNAL_ADVANTAGES = (0.10, 0.25, 0.50, 0.75, 1.00)
EPS = 1e-9


class TiltError(RuntimeError):
    pass


@dataclass(frozen=True)
class AllocationTarget:
    isin: str
    name: str
    target_pct: float
    current_value_eur: float
    buy_enabled: bool
    planner_eligible: bool


@dataclass(frozen=True)
class Candidate:
    target: AllocationTarget
    current_pct: float
    desired_value_eur: float
    deficit_eur: float


def _json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _finite_number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TiltError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise TiltError(f"{field} must be finite")
    return number


def load_allocation(path: Path) -> tuple[float, list[AllocationTarget], dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TiltError(f"cannot read allocation state: {path}") from exc
    if not isinstance(raw, dict) or raw.get("schema") != 1:
        raise TiltError("allocation state must be schema 1")
    contribution = _finite_number(raw.get("contribution_eur"), "contribution_eur")
    if contribution <= 0:
        raise TiltError("contribution_eur must be > 0")
    items = raw.get("targets")
    if not isinstance(items, list) or not items:
        raise TiltError("allocation targets must be a non-empty array")

    seen: set[str] = set()
    targets: list[AllocationTarget] = []
    target_sum = 0.0
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise TiltError(f"targets[{idx}] must be an object")
        isin = str(item.get("isin", "")).strip().upper()
        name = str(item.get("name", "")).strip()
        if len(isin) != 12 or not isin.isalnum():
            raise TiltError(f"targets[{idx}].isin is invalid")
        if isin in seen:
            raise TiltError(f"duplicate target ISIN: {isin}")
        if not name:
            raise TiltError(f"targets[{idx}].name is empty")
        target_pct = _finite_number(item.get("target_pct"), f"targets[{idx}].target_pct")
        current_value = _finite_number(
            item.get("current_value_eur"), f"targets[{idx}].current_value_eur"
        )
        if target_pct < 0 or target_pct > 100:
            raise TiltError(f"targets[{idx}].target_pct must be between 0 and 100")
        if current_value < 0:
            raise TiltError(f"targets[{idx}].current_value_eur must be >= 0")
        buy_enabled = item.get("buy_enabled", True)
        planner_eligible = item.get("planner_eligible", True)
        if not isinstance(buy_enabled, bool) or not isinstance(planner_eligible, bool):
            raise TiltError(f"targets[{idx}] eligibility flags must be booleans")
        seen.add(isin)
        target_sum += target_pct
        targets.append(
            AllocationTarget(
                isin=isin,
                name=name,
                target_pct=target_pct,
                current_value_eur=current_value,
                buy_enabled=buy_enabled,
                planner_eligible=planner_eligible,
            )
        )
    if abs(target_sum - 100.0) > 0.001:
        raise TiltError(f"target percentages must sum to 100; got {target_sum:.6f}")
    return contribution, targets, raw


def build_candidates(
    contribution_eur: float, targets: list[AllocationTarget]
) -> tuple[float, float, list[Candidate], list[dict[str, Any]]]:
    current_total = sum(t.current_value_eur for t in targets)
    if current_total <= 0:
        raise TiltError("current portfolio value must be > 0")
    post_total = current_total + contribution_eur
    candidates: list[Candidate] = []
    inventory: list[dict[str, Any]] = []
    for target in targets:
        current_pct = target.current_value_eur / current_total * 100.0
        desired = post_total * target.target_pct / 100.0
        deficit = desired - target.current_value_eur
        eligible = target.buy_enabled and target.planner_eligible and deficit > EPS
        reason = "eligible"
        if not target.buy_enabled:
            reason = "buy_disabled"
        elif not target.planner_eligible:
            reason = "planner_ineligible"
        elif deficit <= EPS:
            reason = "not_underweight_after_contribution"
        row = {
            "isin": target.isin,
            "name": target.name,
            "target_pct": target.target_pct,
            "current_value_eur": target.current_value_eur,
            "current_pct": current_pct,
            "desired_post_contribution_value_eur": desired,
            "strategic_deficit_eur": deficit,
            "buy_enabled": target.buy_enabled,
            "planner_eligible": target.planner_eligible,
            "candidate": eligible,
            "candidate_reason": reason,
        }
        inventory.append(row)
        if eligible:
            candidates.append(
                Candidate(
                    target=target,
                    current_pct=current_pct,
                    desired_value_eur=desired,
                    deficit_eur=deficit,
                )
            )
    if not candidates:
        raise TiltError("no strategically eligible underweight candidates")
    candidates.sort(key=lambda c: (-c.deficit_eur, c.target.isin))
    return current_total, post_total, candidates, inventory


def clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def tactical_signals(metrics: dict[str, Any]) -> dict[str, float]:
    r5 = _finite_number(metrics.get("return_5d"), "return_5d")
    r20 = _finite_number(metrics.get("return_20d"), "return_20d")
    dd = _finite_number(metrics.get("drawdown_from_20d_high"), "drawdown_from_20d_high")

    # Full-scale thresholds are research constants, not production policy:
    # -5% over 5 sessions, -10% over 20 sessions, -10% from 20-session high.
    short_weakness = clamp01(-r5 / 0.05)
    medium_weakness = clamp01(-r20 / 0.10)
    drawdown = clamp01(-dd / 0.10)
    multi_window = 0.25 * short_weakness + 0.35 * medium_weakness + 0.40 * drawdown

    # A positive 5-session rebound <= +2% does not suppress the tilt. Between
    # +2% and +8% the suppression ramps linearly; >= +8% suppresses it fully.
    rebound_penalty = clamp01((r5 - 0.02) / 0.06)
    rebound_aware = multi_window * (1.0 - rebound_penalty)
    return {
        "short_weakness": short_weakness,
        "medium_weakness": medium_weakness,
        "drawdown_only": drawdown,
        "multi_window": multi_window,
        "rebound_penalty": rebound_penalty,
        "rebound_aware": rebound_aware,
    }


def _load_market_context(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TiltError(f"cannot read market context: {path}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("targets"), list):
        raise TiltError("market context has invalid shape")
    return raw


def evaluate_market_context(
    context: dict[str, Any],
    candidates: list[Candidate],
    *,
    evaluation_date: date,
    max_age_days: int,
) -> tuple[bool, str, str | None, dict[str, dict[str, Any]]]:
    if max_age_days < 0:
        raise TiltError("max market age must be >= 0")
    by_isin = {
        str(item.get("isin", "")).strip().upper(): item
        for item in context.get("targets", [])
        if isinstance(item, dict)
    }
    normalized: dict[str, dict[str, Any]] = {}
    as_of_dates: set[str] = set()
    problems: list[str] = []

    for candidate in candidates:
        isin = candidate.target.isin
        item = by_isin.get(isin)
        if not isinstance(item, dict):
            problems.append(f"{isin}:missing")
            continue
        if item.get("status") != "ok":
            problems.append(f"{isin}:status={item.get('status')}")
            continue
        if str(item.get("currency", "")).upper() != "EUR":
            problems.append(f"{isin}:currency")
            continue
        if str(item.get("region", "")).upper() != "XETRA":
            problems.append(f"{isin}:region")
            continue
        metrics = item.get("metrics")
        if not isinstance(metrics, dict):
            problems.append(f"{isin}:metrics")
            continue
        try:
            as_of = date.fromisoformat(str(metrics.get("as_of", "")))
            age = (evaluation_date - as_of).days
            if age < 0:
                raise ValueError("future")
            if age > max_age_days:
                problems.append(f"{isin}:stale={age}d")
                continue
            signals = tactical_signals(metrics)
        except (TypeError, ValueError, TiltError):
            problems.append(f"{isin}:invalid_metrics")
            continue
        as_of_text = as_of.isoformat()
        as_of_dates.add(as_of_text)
        normalized[isin] = {
            "as_of": as_of_text,
            "age_calendar_days_at_evaluation": age,
            "symbol": item.get("symbol"),
            "latest_close": metrics.get("latest_close"),
            "return_5d": float(metrics["return_5d"]),
            "return_20d": float(metrics["return_20d"]),
            "drawdown_from_20d_high": float(metrics["drawdown_from_20d_high"]),
            "signals": signals,
        }

    if problems:
        return False, "market_context_incomplete:" + ",".join(problems), None, normalized
    if len(as_of_dates) != 1:
        return False, "market_context_mixed_as_of", None, normalized
    common_as_of = next(iter(as_of_dates))
    return True, "market_context_coherent", common_as_of, normalized


def _winner(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    return sorted(rows, key=lambda row: (-float(row[key]), str(row["isin"])))[0]


def calculate_models(
    candidates: list[Candidate],
    market: dict[str, dict[str, Any]],
    *,
    tactical_active: bool,
    contribution_eur: float,
    tilt_budget_pct: float,
    tie_band_pct: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if tilt_budget_pct < 0 or tie_band_pct < 0:
        raise TiltError("tilt budget and tie band percentages must be >= 0")
    tilt_budget_eur = contribution_eur * tilt_budget_pct / 100.0
    tie_band_eur = contribution_eur * tie_band_pct / 100.0

    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        signals = market.get(candidate.target.isin, {}).get("signals", {}) if tactical_active else {}
        drawdown = float(signals.get("drawdown_only", 0.0))
        multi = float(signals.get("multi_window", 0.0))
        rebound = float(signals.get("rebound_aware", 0.0))
        rows.append(
            {
                "isin": candidate.target.isin,
                "name": candidate.target.name,
                "strategic_deficit_eur": candidate.deficit_eur,
                "current_pct": candidate.current_pct,
                "target_pct": candidate.target.target_pct,
                "drawdown_only": drawdown,
                "multi_window": multi,
                "rebound_aware": rebound,
                "bounded_drawdown_score_eur": candidate.deficit_eur + tilt_budget_eur * drawdown,
                "bounded_multi_window_score_eur": candidate.deficit_eur + tilt_budget_eur * multi,
                "bounded_rebound_aware_score_eur": candidate.deficit_eur + tilt_budget_eur * rebound,
            }
        )

    baseline = _winner(rows, "strategic_deficit_eur")
    best_deficit = float(baseline["strategic_deficit_eur"])

    def model_result(name: str, winner: dict[str, Any], score_key: str, note: str) -> dict[str, Any]:
        sacrifice = best_deficit - float(winner["strategic_deficit_eur"])
        return {
            "model": name,
            "selected_isin": winner["isin"],
            "selected_name": winner["name"],
            "score": float(winner[score_key]),
            "score_unit": "EUR-equivalent" if score_key != "strategic_deficit_eur" else "EUR deficit",
            "strategic_deficit_eur": float(winner["strategic_deficit_eur"]),
            "strategic_sacrifice_eur": max(sacrifice, 0.0),
            "changed_from_baseline": winner["isin"] != baseline["isin"],
            "note": note,
        }

    results = {
        "baseline": model_result(
            "baseline_allocation_only",
            baseline,
            "strategic_deficit_eur",
            "No market context; largest post-contribution allocation deficit wins.",
        ),
        "bounded_drawdown": model_result(
            "bounded_drawdown_only",
            _winner(rows, "bounded_drawdown_score_eur"),
            "bounded_drawdown_score_eur",
            f"Adds at most EUR {tilt_budget_eur:.2f} using 20-session drawdown only.",
        ),
        "bounded_multi_window": model_result(
            "bounded_multi_window",
            _winner(rows, "bounded_multi_window_score_eur"),
            "bounded_multi_window_score_eur",
            f"Adds at most EUR {tilt_budget_eur:.2f} using 5d weakness, 20d weakness and drawdown.",
        ),
        "bounded_rebound_aware": model_result(
            "bounded_rebound_aware",
            _winner(rows, "bounded_rebound_aware_score_eur"),
            "bounded_rebound_aware_score_eur",
            f"Same bounded multi-window signal, suppressed after a strong 5-session rebound.",
        ),
    }

    tie_candidates = [
        row for row in rows if best_deficit - float(row["strategic_deficit_eur"]) <= tie_band_eur + EPS
    ]
    if tactical_active and any(float(row["rebound_aware"]) > EPS for row in tie_candidates):
        tie_winner = sorted(
            tie_candidates,
            key=lambda row: (-float(row["rebound_aware"]), -float(row["strategic_deficit_eur"]), str(row["isin"])),
        )[0]
    else:
        tie_winner = baseline
    tie_result = model_result(
        "tie_break_rebound_aware",
        tie_winner,
        "strategic_deficit_eur",
        f"Only candidates within EUR {tie_band_eur:.2f} of the best strategic deficit may be reordered.",
    )
    tie_result["tactical_score"] = float(tie_winner["rebound_aware"])
    results["tie_break_rebound_aware"] = tie_result

    return rows, {
        "tilt_budget_pct_of_contribution": tilt_budget_pct,
        "tilt_budget_eur": tilt_budget_eur,
        "tie_band_pct_of_contribution": tie_band_pct,
        "tie_band_eur": tie_band_eur,
        "models": results,
    }


def _parse_csv_floats(value: str, *, field: str) -> tuple[float, ...]:
    """Parse a non-empty comma-separated list of finite non-negative floats."""
    parsed: list[float] = []
    seen: set[float] = set()
    for raw in value.split(","):
        text = raw.strip()
        if not text:
            raise argparse.ArgumentTypeError(f"{field} contains an empty value")
        try:
            number = float(text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{field} must contain numbers") from exc
        if not math.isfinite(number) or number < 0:
            raise argparse.ArgumentTypeError(
                f"{field} values must be finite and >= 0"
            )
        if number not in seen:
            seen.add(number)
            parsed.append(number)
    if not parsed:
        raise argparse.ArgumentTypeError(f"{field} must not be empty")
    return tuple(parsed)


def calibration_sweep(
    candidates: list[Candidate],
    market: dict[str, dict[str, Any]],
    *,
    tactical_active: bool,
    contribution_eur: float,
    sweep_pcts: tuple[float, ...],
) -> list[dict[str, Any]]:
    """Evaluate the rebound-aware additive model across tactical bonus ceilings."""
    results: list[dict[str, Any]] = []
    for pct in sweep_pcts:
        rows, policy = calculate_models(
            candidates,
            market,
            tactical_active=tactical_active,
            contribution_eur=contribution_eur,
            tilt_budget_pct=pct,
            tie_band_pct=0.0,
        )
        model = policy["models"]["bounded_rebound_aware"]
        baseline = policy["models"]["baseline"]
        selected = next(row for row in rows if row["isin"] == model["selected_isin"])
        baseline_row = next(row for row in rows if row["isin"] == baseline["selected_isin"])
        results.append(
            {
                "tactical_bonus_ceiling_pct_of_contribution": pct,
                "tactical_bonus_ceiling_eur": policy["tilt_budget_eur"],
                "selected_isin": model["selected_isin"],
                "selected_name": model["selected_name"],
                "changed_from_baseline": model["changed_from_baseline"],
                "actual_strategic_sacrifice_eur": model["strategic_sacrifice_eur"],
                "actual_strategic_sacrifice_pct_of_contribution": (
                    model["strategic_sacrifice_eur"] / contribution_eur * 100.0
                ),
                "selected_rebound_aware_signal": float(selected["rebound_aware"]),
                "baseline_rebound_aware_signal": float(baseline_row["rebound_aware"]),
                "signal_advantage_vs_baseline": (
                    float(selected["rebound_aware"])
                    - float(baseline_row["rebound_aware"])
                ),
            }
        )
    return results


def challenger_break_even(
    rows: list[dict[str, Any]], *, contribution_eur: float
) -> list[dict[str, Any]]:
    """Return additive rebound-aware score parity requirements vs the baseline."""
    if contribution_eur <= 0:
        raise TiltError("contribution_eur must be > 0")
    baseline = _winner(rows, "strategic_deficit_eur")
    best_deficit = float(baseline["strategic_deficit_eur"])
    baseline_signal = float(baseline["rebound_aware"])
    result: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: -float(item["strategic_deficit_eur"])):
        if row["isin"] == baseline["isin"]:
            continue
        gap = max(best_deficit - float(row["strategic_deficit_eur"]), 0.0)
        signal_advantage = float(row["rebound_aware"]) - baseline_signal
        parity_bonus_ceiling_eur: float | None = None
        parity_pct: float | None = None
        parity_multiple: float | None = None
        if gap <= EPS:
            parity_bonus_ceiling_eur = 0.0
            parity_pct = 0.0
            parity_multiple = 0.0
        elif signal_advantage > EPS:
            parity_bonus_ceiling_eur = gap / signal_advantage
            parity_pct = parity_bonus_ceiling_eur / contribution_eur * 100.0
            parity_multiple = parity_bonus_ceiling_eur / contribution_eur
        result.append(
            {
                "isin": row["isin"],
                "name": row["name"],
                "strategic_gap_eur": gap,
                "baseline_signal": baseline_signal,
                "challenger_signal": float(row["rebound_aware"]),
                "signal_advantage": signal_advantage,
                "score_parity_bonus_ceiling_eur": parity_bonus_ceiling_eur,
                "score_parity_bonus_ceiling_pct_of_contribution": parity_pct,
                "score_parity_bonus_ceiling_contribution_multiple": parity_multiple,
                "can_outscore_with_positive_bonus_ceiling": parity_bonus_ceiling_eur is not None,
            }
        )
    return result


def decision_surface(
    *,
    contribution_eur: float,
    strategic_gap_pcts: tuple[float, ...],
    signal_advantages: tuple[float, ...],
) -> dict[str, Any]:
    """Return score-parity bounds across controlled strategic gaps and signal edges."""
    if contribution_eur <= 0:
        raise TiltError("contribution_eur must be > 0")
    if any(value <= 0 for value in signal_advantages):
        raise TiltError("decision-surface signal advantages must be > 0")
    rows: list[dict[str, Any]] = []
    for gap_pct in strategic_gap_pcts:
        gap_eur = contribution_eur * gap_pct / 100.0
        cells = []
        for advantage in signal_advantages:
            required_bonus_ceiling_eur = gap_eur / advantage
            cells.append(
                {
                    "signal_advantage": advantage,
                    "required_bonus_ceiling_eur": required_bonus_ceiling_eur,
                    "required_bonus_ceiling_pct_of_contribution": (
                        required_bonus_ceiling_eur / contribution_eur * 100.0
                    ),
                }
            )
        rows.append(
            {
                "strategic_gap_pct_of_contribution": gap_pct,
                "strategic_gap_eur": gap_eur,
                "cells": cells,
            }
        )
    return {
        "signal_advantages": list(signal_advantages),
        "rows": rows,
        "interpretation": (
            "Each cell is the tactical bonus ceiling required merely to reach score "
            "parity. A clean win may require a slightly larger ceiling when the parity "
            "score ties."
        ),
    }


def effective_gap_capacity(
    *,
    contribution_eur: float,
    bonus_ceiling_pcts: tuple[float, ...],
    signal_advantages: tuple[float, ...],
) -> dict[str, Any]:
    """Show the strategic gap an additive bonus ceiling can overcome at each signal edge."""
    if contribution_eur <= 0:
        raise TiltError("contribution_eur must be > 0")
    if any(value < 0 for value in bonus_ceiling_pcts):
        raise TiltError("bonus ceiling percentages must be >= 0")
    if any(value < 0 or value > 1 for value in signal_advantages):
        raise TiltError("effective-gap signal advantages must be between 0 and 1")
    rows: list[dict[str, Any]] = []
    for pct in bonus_ceiling_pcts:
        ceiling_eur = contribution_eur * pct / 100.0
        cells = []
        for advantage in signal_advantages:
            gap_eur = ceiling_eur * advantage
            cells.append(
                {
                    "signal_advantage": advantage,
                    "effective_strategic_gap_eur": gap_eur,
                    "effective_strategic_gap_pct_of_contribution": (
                        gap_eur / contribution_eur * 100.0
                    ),
                }
            )
        rows.append(
            {
                "tactical_bonus_ceiling_pct_of_contribution": pct,
                "tactical_bonus_ceiling_eur": ceiling_eur,
                "cells": cells,
            }
        )
    return {
        "signal_advantages": list(signal_advantages),
        "rows": rows,
        "interpretation": (
            "The effective strategic gap that can be overcome is tactical bonus ceiling "
            "multiplied by the challenger's positive rebound-aware signal advantage over "
            "the baseline."
        ),
    }


def calibrate(
    allocation_path: Path,
    market_context_path: Path,
    output_dir: Path,
    *,
    evaluation_date: date,
    max_market_age_days: int,
    sweep_pcts: tuple[float, ...],
    surface_gap_pcts: tuple[float, ...],
    surface_signal_advantages: tuple[float, ...],
) -> dict[str, Any]:
    """Calibrate the rebound-aware additive model without changing scoring semantics."""
    contribution, targets, allocation_raw = load_allocation(allocation_path)
    current_total, post_total, candidates, inventory = build_candidates(contribution, targets)
    context = _load_market_context(market_context_path)
    active, context_reason, common_as_of, normalized_market = evaluate_market_context(
        context,
        candidates,
        evaluation_date=evaluation_date,
        max_age_days=max_market_age_days,
    )
    rows, policy = calculate_models(
        candidates,
        normalized_market,
        tactical_active=active,
        contribution_eur=contribution,
        tilt_budget_pct=0.0,
        tie_band_pct=0.0,
    )
    for row in rows:
        row["market_context"] = normalized_market.get(row["isin"])

    sweep = calibration_sweep(
        candidates,
        normalized_market,
        tactical_active=active,
        contribution_eur=contribution,
        sweep_pcts=sweep_pcts,
    )
    break_even = challenger_break_even(rows, contribution_eur=contribution)
    surface = decision_surface(
        contribution_eur=contribution,
        strategic_gap_pcts=surface_gap_pcts,
        signal_advantages=surface_signal_advantages,
    )
    effective_capacity = effective_gap_capacity(
        contribution_eur=contribution,
        bonus_ceiling_pcts=sweep_pcts,
        signal_advantages=surface_signal_advantages,
    )
    doc = {
        "schema": 1,
        "prototype_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_date": evaluation_date.isoformat(),
        "scope": "research_only_tactical_tilt_calibration",
        "reference_model": "bounded_rebound_aware",
        "reference_tactical_bonus_ceiling": {
            "pct_of_contribution": REFERENCE_TACTICAL_BONUS_CEILING_PCT,
            "eur": contribution * REFERENCE_TACTICAL_BONUS_CEILING_PCT / 100.0,
            "status": "provisional_research_reference_not_production_policy",
        },
        "allocation": {
            "source_label": allocation_raw.get("source_label"),
            "contribution_eur": contribution,
            "current_portfolio_value_eur": current_total,
            "post_contribution_portfolio_value_eur": post_total,
            "inventory": inventory,
        },
        "market_context_gate": {
            "active": active,
            "reason": context_reason,
            "common_as_of": common_as_of,
            "max_calendar_age_days": max_market_age_days,
            "failure_semantics": "neutral_fallback_to_allocation_only",
        },
        "baseline": policy["models"]["baseline"],
        "candidate_scores": rows,
        "sweep": sweep,
        "challenger_break_even": break_even,
        "effective_gap_capacity": effective_capacity,
        "decision_surface": surface,
        "limitations": [
            "Calibration does not change the v0.2.0 tactical signal or additive score formula.",
            "The tactical bonus ceiling is an EUR-equivalent score addition at signal=1.0; it is not a direct maximum strategic sacrifice.",
            "Score-parity analysis is not a forecast of future returns and does not imply that a price decline will recover.",
            "This PoC ranks allocation candidates only; full PA provider, cash, funding, fee, policy and execution routing remain outside scope.",
            "Market-context failure or staleness is neutral and never reduces core PA actionability.",
        ],
    }
    _json_dump(output_dir / "calibration.json", doc)
    write_calibration_report(doc, output_dir / "calibration_report.txt")
    return doc


def evaluate(
    allocation_path: Path,
    market_context_path: Path,
    output_dir: Path,
    *,
    evaluation_date: date,
    tilt_budget_pct: float,
    tie_band_pct: float,
    max_market_age_days: int,
) -> dict[str, Any]:
    contribution, targets, allocation_raw = load_allocation(allocation_path)
    current_total, post_total, candidates, inventory = build_candidates(contribution, targets)
    context = _load_market_context(market_context_path)
    active, context_reason, common_as_of, normalized_market = evaluate_market_context(
        context,
        candidates,
        evaluation_date=evaluation_date,
        max_age_days=max_market_age_days,
    )
    rows, model_block = calculate_models(
        candidates,
        normalized_market,
        tactical_active=active,
        contribution_eur=contribution,
        tilt_budget_pct=tilt_budget_pct,
        tie_band_pct=tie_band_pct,
    )
    for row in rows:
        row["market_context"] = normalized_market.get(row["isin"])

    doc = {
        "schema": 1,
        "prototype_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_date": evaluation_date.isoformat(),
        "scope": "research_only_allocation_ranking",
        "allocation": {
            "source_label": allocation_raw.get("source_label"),
            "contribution_eur": contribution,
            "current_portfolio_value_eur": current_total,
            "post_contribution_portfolio_value_eur": post_total,
            "inventory": inventory,
        },
        "market_context_gate": {
            "active": active,
            "reason": context_reason,
            "common_as_of": common_as_of,
            "max_calendar_age_days": max_market_age_days,
            "failure_semantics": "neutral_fallback_to_allocation_only",
        },
        "candidate_scores": rows,
        "policy": model_block,
        "limitations": [
            "This PoC ranks allocation candidates only; it does not reproduce full PA provider, cash, funding, fee, policy or execution routing.",
            "Tactical models are research candidates, not production recommendation policy.",
            "Market-context failure or staleness is neutral and never reduces core PA actionability.",
        ],
    }
    _json_dump(output_dir / "tactical_tilt.json", doc)
    write_report(doc, output_dir / "tactical_tilt_report.txt")
    return doc


def _pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def write_report(doc: dict[str, Any], path: Path) -> None:
    allocation = doc["allocation"]
    gate = doc["market_context_gate"]
    policy = doc["policy"]
    lines = [
        "Portfolio Architect Tactical Tilt PoC",
        f"prototype_version: {doc['prototype_version']}",
        f"generated_at: {doc['generated_at']}",
        f"evaluation_date: {doc['evaluation_date']}",
        "",
        "SCOPE",
        "  Research-only allocation ranking. Full PA execution/provider logic is not reproduced.",
        "",
        "ALLOCATION",
        f"  contribution_eur: {allocation['contribution_eur']:.2f}",
        f"  current_portfolio_value_eur: {allocation['current_portfolio_value_eur']:.2f}",
        f"  post_contribution_portfolio_value_eur: {allocation['post_contribution_portfolio_value_eur']:.2f}",
        "",
        "MARKET CONTEXT",
        f"  tactical_active: {gate['active']}",
        f"  reason: {gate['reason']}",
        f"  common_as_of: {gate['common_as_of']}",
        f"  failure_semantics: {gate['failure_semantics']}",
        "",
        "BOUNDS",
        f"  tactical_bonus_ceiling: {policy['tilt_budget_pct_of_contribution']:.2f}% of contribution = EUR {policy['tilt_budget_eur']:.2f}",
        f"  tie_break_band: {policy['tie_band_pct_of_contribution']:.2f}% of contribution = EUR {policy['tie_band_eur']:.2f}",
        "",
        "CANDIDATES",
    ]
    for row in sorted(doc["candidate_scores"], key=lambda x: -float(x["strategic_deficit_eur"])):
        market = row.get("market_context") or {}
        signals = market.get("signals") or {}
        lines.append(f"  {row['isin']}  {row['name']}")
        lines.append(
            f"    strategic_deficit_eur: {row['strategic_deficit_eur']:.2f}  "
            f"current/target: {row['current_pct']:.2f}% / {row['target_pct']:.2f}%"
        )
        if market:
            lines.append(
                f"    market: as_of={market.get('as_of')}  5d={_pct(market['return_5d'])}  "
                f"20d={_pct(market['return_20d'])}  drawdown={_pct(market['drawdown_from_20d_high'])}"
            )
            lines.append(
                f"    signals: drawdown={signals['drawdown_only']:.3f}  "
                f"multi={signals['multi_window']:.3f}  rebound_penalty={signals['rebound_penalty']:.3f}  "
                f"rebound_aware={signals['rebound_aware']:.3f}"
            )
        else:
            lines.append("    market: neutral/unavailable")
        lines.append("")

    lines.append("MODEL RESULTS")
    for key in (
        "baseline",
        "bounded_drawdown",
        "bounded_multi_window",
        "bounded_rebound_aware",
        "tie_break_rebound_aware",
    ):
        result = policy["models"][key]
        lines.append(f"  {result['model']}")
        lines.append(f"    selected: {result['selected_isin']}  {result['selected_name']}")
        lines.append(f"    strategic_deficit_eur: {result['strategic_deficit_eur']:.2f}")
        lines.append(f"    strategic_sacrifice_eur: {result['strategic_sacrifice_eur']:.2f}")
        lines.append(f"    changed_from_baseline: {result['changed_from_baseline']}")
        if "tactical_score" in result:
            lines.append(f"    tactical_score: {result['tactical_score']:.3f}")
        lines.append(f"    note: {result['note']}")
        lines.append("")

    lines.extend(
        [
            "INTERPRETATION",
            "  No model in this report is production policy. Compare how often and by how much",
            "  each bounded model departs from the allocation-only baseline before choosing a design.",
            "  A market-data failure makes Tactical Tilt neutral; core PA remains unaffected.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_calibration_report(doc: dict[str, Any], path: Path) -> None:
    allocation = doc["allocation"]
    gate = doc["market_context_gate"]
    baseline = doc["baseline"]
    lines = [
        "Portfolio Architect Tactical Tilt calibration",
        f"prototype_version: {doc['prototype_version']}",
        f"generated_at: {doc['generated_at']}",
        f"evaluation_date: {doc['evaluation_date']}",
        f"reference_model: {doc['reference_model']}",
        "",
        "SCOPE",
        "  Research-only calibration of the tactical bonus ceiling.",
        "  The ceiling is an EUR-equivalent score bonus at signal=1.0, not a direct maximum strategic sacrifice.",
        "  The v0.2.0 rebound-aware signal and additive score formula are unchanged.",
        "",
        "ALLOCATION",
        f"  contribution_eur: {allocation['contribution_eur']:.2f}",
        f"  current_portfolio_value_eur: {allocation['current_portfolio_value_eur']:.2f}",
        f"  post_contribution_portfolio_value_eur: {allocation['post_contribution_portfolio_value_eur']:.2f}",
        f"  baseline: {baseline['selected_isin']}  {baseline['selected_name']}",
        f"  baseline_strategic_deficit_eur: {baseline['strategic_deficit_eur']:.2f}",
        "",
        "MARKET CONTEXT",
        f"  tactical_active: {gate['active']}",
        f"  reason: {gate['reason']}",
        f"  common_as_of: {gate['common_as_of']}",
        f"  failure_semantics: {gate['failure_semantics']}",
        "",
        "PROVISIONAL RESEARCH REFERENCE",
        f"  tactical_bonus_ceiling: {doc['reference_tactical_bonus_ceiling']['pct_of_contribution']:.1f}% of contribution = EUR {doc['reference_tactical_bonus_ceiling']['eur']:.2f}",
        f"  status: {doc['reference_tactical_bonus_ceiling']['status']}",
        "",
        "TACTICAL BONUS CEILING SWEEP",
        "  Ceiling        Selected       Actual sacrifice   Signal edge   Changed",
    ]
    for row in doc["sweep"]:
        lines.append(
            "  "
            f"{row['tactical_bonus_ceiling_pct_of_contribution']:>6.1f}% "
            f"EUR {row['tactical_bonus_ceiling_eur']:>7.2f}  "
            f"{row['selected_isin']}  "
            f"EUR {row['actual_strategic_sacrifice_eur']:>7.2f}  "
            f"{row['signal_advantage_vs_baseline']:+.3f}      "
            f"{row['changed_from_baseline']}"
        )

    lines.extend(["", "LIVE CHALLENGER BREAK-EVEN"])
    if not doc["challenger_break_even"]:
        lines.append("  No challenger candidates.")
    for row in doc["challenger_break_even"]:
        lines.append(f"  {row['isin']}  {row['name']}")
        lines.append(
            f"    strategic_gap_eur: {row['strategic_gap_eur']:.2f}  "
            f"signal_advantage: {row['signal_advantage']:+.3f}"
        )
        if row["score_parity_bonus_ceiling_eur"] is None:
            lines.append(
                "    score_parity: none at any positive bonus ceiling; tactical signal does not exceed baseline"
            )
        else:
            lines.append(
                f"    score_parity: EUR {row['score_parity_bonus_ceiling_eur']:.2f} = "
                f"{row['score_parity_bonus_ceiling_pct_of_contribution']:.1f}% of contribution = "
                f"{row['score_parity_bonus_ceiling_contribution_multiple']:.2f}x one contribution"
            )

    capacity = doc["effective_gap_capacity"]
    lines.extend(
        [
            "",
            "EFFECTIVE STRATEGIC GAP CAPACITY",
            "  Each cell is the strategic gap the ceiling can overcome at the given signal edge.",
        ]
    )
    capacity_header = "  ceiling" + "".join(
        f"      +{adv:.2f}" for adv in capacity["signal_advantages"]
    )
    lines.append(capacity_header)
    for row in capacity["rows"]:
        rendered = "".join(
            f"  EUR {cell['effective_strategic_gap_eur']:>7.2f}"
            for cell in row["cells"]
        )
        lines.append(
            f"  {row['tactical_bonus_ceiling_pct_of_contribution']:>6.1f}% "
            f"(EUR {row['tactical_bonus_ceiling_eur']:>7.2f})"
            + rendered
        )

    surface = doc["decision_surface"]
    lines.extend(
        [
            "",
            "GENERIC DECISION SURFACE",
            "  Each cell is the tactical bonus ceiling required to reach additive-score parity.",
            "  Rows are strategic gaps; columns are rebound-aware signal advantages.",
        ]
    )
    header = "  gap" + "".join(
        f"      +{adv:.2f}" for adv in surface["signal_advantages"]
    )
    lines.append(header)
    for row in surface["rows"]:
        rendered = "".join(
            f"  {cell['required_bonus_ceiling_pct_of_contribution']:>8.1f}%"
            for cell in row["cells"]
        )
        lines.append(
            f"  EUR {row['strategic_gap_eur']:>7.2f} "
            f"({row['strategic_gap_pct_of_contribution']:>5.1f}%)"
            + rendered
        )

    lines.extend(
        [
            "",
            "INTERPRETATION",
            "  A larger tactical bonus ceiling makes TT relevant across wider allocation gaps,",
            "  but the effective strategic gap it can overcome is ceiling × positive signal edge.",
            "  Reaching score parity is not the same as proving superior future returns.",
            "  Overweight/ineligible targets remain outside the candidate set before calibration.",
            "  A market-data failure makes Tactical Tilt neutral; core PA remains unaffected.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("score", "calibrate"))
    parser.add_argument("--allocation", type=Path, default=Path("allocation_state.json"))
    parser.add_argument(
        "--market-context", type=Path, default=Path("output") / "market_context.json"
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output") / "tactical_tilt")
    parser.add_argument("--evaluation-date", type=date.fromisoformat, default=None)
    parser.add_argument(
        "--tactical-bonus-ceiling-pct",
        "--tilt-budget-pct",
        dest="tilt_budget_pct",
        type=float,
        default=DEFAULT_TILT_BUDGET_PCT,
        help="score-command tactical bonus ceiling as percent of one contribution; --tilt-budget-pct is a compatibility alias",
    )
    parser.add_argument("--tie-band-pct", type=float, default=DEFAULT_TIE_BAND_PCT)
    parser.add_argument("--max-market-age-days", type=int, default=DEFAULT_MAX_MARKET_AGE_DAYS)
    parser.add_argument(
        "--sweep-pct",
        type=lambda value: _parse_csv_floats(value, field="sweep-pct"),
        default=DEFAULT_CALIBRATION_SWEEP_PCTS,
        help="tactical bonus ceilings as comma-separated percentages of one contribution",
    )
    parser.add_argument(
        "--surface-gap-pct",
        type=lambda value: _parse_csv_floats(value, field="surface-gap-pct"),
        default=DEFAULT_SURFACE_GAP_PCTS,
        help="decision-surface strategic gaps as percentages of one contribution",
    )
    parser.add_argument(
        "--surface-signal-advantages",
        type=lambda value: _parse_csv_floats(value, field="surface-signal-advantages"),
        default=DEFAULT_SURFACE_SIGNAL_ADVANTAGES,
        help="decision-surface rebound-aware signal advantages",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        evaluation_date = args.evaluation_date or datetime.now(timezone.utc).date()
        if args.command == "score":
            doc = evaluate(
                args.allocation,
                args.market_context,
                args.output_dir,
                evaluation_date=evaluation_date,
                tilt_budget_pct=args.tilt_budget_pct,
                tie_band_pct=args.tie_band_pct,
                max_market_age_days=args.max_market_age_days,
            )
            gate = doc["market_context_gate"]
            print(
                "tactical context:",
                "active" if gate["active"] else "neutral",
                f"({gate['reason']})",
            )
            for key, result in doc["policy"]["models"].items():
                print(
                    f"{key}: {result['selected_isin']} "
                    f"sacrifice=EUR {result['strategic_sacrifice_eur']:.2f} "
                    f"changed={result['changed_from_baseline']}"
                )
            print(f"report: {args.output_dir / 'tactical_tilt_report.txt'}")
            return 0

        doc = calibrate(
            args.allocation,
            args.market_context,
            args.output_dir,
            evaluation_date=evaluation_date,
            max_market_age_days=args.max_market_age_days,
            sweep_pcts=args.sweep_pct,
            surface_gap_pcts=args.surface_gap_pct,
            surface_signal_advantages=args.surface_signal_advantages,
        )
        gate = doc["market_context_gate"]
        print(
            "tactical context:",
            "active" if gate["active"] else "neutral",
            f"({gate['reason']})",
        )
        print(f"baseline: {doc['baseline']['selected_isin']}")
        for row in doc["sweep"]:
            print(
                f"bonus_ceiling={row['tactical_bonus_ceiling_pct_of_contribution']:.1f}% "
                f"(EUR {row['tactical_bonus_ceiling_eur']:.2f}): "
                f"{row['selected_isin']} actual_sacrifice=EUR "
                f"{row['actual_strategic_sacrifice_eur']:.2f} "
                f"changed={row['changed_from_baseline']}"
            )
        print(f"report: {args.output_dir / 'calibration_report.txt'}")
        return 0
    except TiltError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
