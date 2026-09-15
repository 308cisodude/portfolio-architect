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

VERSION = "0.2.0"
DEFAULT_TILT_BUDGET_PCT = 10.0
DEFAULT_TIE_BAND_PCT = 10.0
DEFAULT_MAX_MARKET_AGE_DAYS = 4
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
        f"  tactical_budget: {policy['tilt_budget_pct_of_contribution']:.2f}% of contribution = EUR {policy['tilt_budget_eur']:.2f}",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("score",))
    parser.add_argument("--allocation", type=Path, default=Path("allocation_state.json"))
    parser.add_argument(
        "--market-context", type=Path, default=Path("output") / "market_context.json"
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output") / "tactical_tilt")
    parser.add_argument("--evaluation-date", type=date.fromisoformat, default=None)
    parser.add_argument("--tilt-budget-pct", type=float, default=DEFAULT_TILT_BUDGET_PCT)
    parser.add_argument("--tie-band-pct", type=float, default=DEFAULT_TIE_BAND_PCT)
    parser.add_argument("--max-market-age-days", type=int, default=DEFAULT_MAX_MARKET_AGE_DAYS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        evaluation_date = args.evaluation_date or datetime.now(timezone.utc).date()
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
    except TiltError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
