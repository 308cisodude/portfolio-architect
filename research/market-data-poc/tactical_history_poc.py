#!/usr/bin/env python3
"""Portfolio Architect Tactical Tilt historical cadence replay PoC.

Research-only harness that converts provider-neutral daily price history into
synthetic PA planning-cycle observations, feeds those observations through the
existing Tactical Tilt signal and cadence-aware persistence contracts, and
summarizes how real market history would have behaved at weekly, monthly,
quarterly, and yearly plan frequencies.

Daily price observations never advance governance state directly. They are used
only to derive the market evidence attached to synthetic PA planning cycles and
to determine whether a recovery was confirmed by a continuous completed-session
run across PA-cycle boundaries.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import market_data_poc as md
import tactical_persistence_poc as tp
import tactical_tilt_poc as tt

VERSION = "0.4.3"
HISTORY_SCHEMA = 1
DEFAULT_RECOVERY_CONFIRM_SESSIONS = 5
DEFAULT_FREQUENCIES = ("weekly", "monthly", "quarterly", "yearly")


class HistoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class HistoricalBar:
    day: date
    open: float
    high: float
    low: float
    close: float
    volume: float | None


@dataclass(frozen=True)
class HistoricalTarget:
    isin: str
    name: str
    symbol: str
    currency: str
    region: str
    bars: tuple[HistoricalBar, ...]  # chronological oldest -> newest


def _json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _finite(value: Any, field: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise HistoryError(f"{field} must be numeric") from exc
    if not math.isfinite(out):
        raise HistoryError(f"{field} must be finite")
    return out


def _parse_iso_day(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise HistoryError(f"{field} must be YYYY-MM-DD") from exc


def _bar_from_av(day_text: str, values: Any, symbol: str) -> dict[str, Any]:
    if not isinstance(values, dict):
        raise HistoryError(f"invalid Alpha Vantage bar for {symbol} on {day_text}")
    try:
        volume_text = str(values.get("5. volume", "")).strip()
        return {
            "date": date.fromisoformat(day_text).isoformat(),
            "open": float(values["1. open"]),
            "high": float(values["2. high"]),
            "low": float(values["3. low"]),
            "close": float(values["4. close"]),
            "volume": float(volume_text) if volume_text else None,
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise HistoryError(f"invalid Alpha Vantage bar for {symbol} on {day_text}") from exc


def _load_mapping(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryError(f"cannot read mapping: {path}") from exc
    targets = raw.get("targets") if isinstance(raw, dict) else None
    if not isinstance(targets, list) or not targets:
        raise HistoryError("mapping must contain targets")
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(targets):
        if not isinstance(item, dict) or item.get("status") != "resolved":
            raise HistoryError(f"mapping target {idx} is not resolved")
        selected = item.get("selected")
        if not isinstance(selected, dict):
            raise HistoryError(f"mapping target {idx} has no selected listing")
        isin = str(item.get("isin", "")).strip().upper()
        name = str(item.get("name", "")).strip()
        symbol = str(selected.get("symbol", "")).strip()
        currency = str(selected.get("currency", "")).strip().upper()
        region = str(selected.get("region", "")).strip()
        if len(isin) != 12 or not name or not symbol:
            raise HistoryError(f"mapping target {idx} identity is incomplete")
        out.append({
            "isin": isin,
            "name": name,
            "symbol": symbol,
            "currency": currency,
            "region": region,
        })
    return out


def fetch_history(
    mapping_path: Path,
    output_path: Path,
    av_key: str,
    guard: md.AlphaVantageGuard,
    *,
    outputsize: str,
) -> dict[str, Any]:
    if outputsize not in {"compact", "full"}:
        raise HistoryError("outputsize must be compact or full")
    targets = _load_mapping(mapping_path)
    fetched: list[dict[str, Any]] = []
    for target in targets:
        payload = md._av_get(  # research PoC deliberately reuses the proven provider guard
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": target["symbol"],
                "outputsize": outputsize,
            },
            av_key,
            guard,
        )
        series = payload.get("Time Series (Daily)")
        if not isinstance(series, dict) or not series:
            raise HistoryError(f"Alpha Vantage returned no daily history for {target['symbol']}")
        bars = [_bar_from_av(day_text, values, target["symbol"]) for day_text, values in series.items()]
        bars.sort(key=lambda row: row["date"])
        if len(bars) < 21:
            raise HistoryError(f"Alpha Vantage returned fewer than 21 daily sessions for {target['symbol']}")
        fetched.append({**target, "status": "ok", "bars": bars})

    document = {
        "schema": HISTORY_SCHEMA,
        "prototype_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "alpha_vantage",
        "quote_type": "daily_raw_ohlcv",
        "requested_outputsize": outputsize,
        "alpha_vantage_policy": guard.usage(),
        "targets": fetched,
    }
    _json_dump(output_path, document)
    return document



def import_history_csv(csv_path: Path, output_path: Path) -> dict[str, Any]:
    """Import provider-neutral daily OHLCV history from a consolidated CSV.

    Required columns: isin,name,symbol,currency,region,date,open,high,low,close.
    Optional column: volume. One row per trading session.
    """
    try:
        handle = csv_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise HistoryError(f"cannot read history CSV: {csv_path}") from exc
    grouped: dict[str, dict[str, Any]] = {}
    with handle:
        reader = csv.DictReader(handle)
        required = {"isin", "name", "symbol", "currency", "region", "date", "open", "high", "low", "close"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            missing = sorted(required - set(reader.fieldnames or []))
            raise HistoryError("history CSV missing columns: " + ", ".join(missing))
        for ridx, row in enumerate(reader, start=2):
            isin = str(row.get("isin", "")).strip().upper()
            name = str(row.get("name", "")).strip()
            symbol = str(row.get("symbol", "")).strip()
            currency = str(row.get("currency", "")).strip().upper()
            region = str(row.get("region", "")).strip()
            if len(isin) != 12 or not isin.isalnum() or not name or not symbol:
                raise HistoryError(f"history CSV row {ridx} has invalid identity")
            target = grouped.setdefault(isin, {
                "isin": isin, "name": name, "symbol": symbol, "currency": currency, "region": region, "status": "ok", "bars": []
            })
            if any(target[k] != v for k, v in (("name", name), ("symbol", symbol), ("currency", currency), ("region", region))):
                raise HistoryError(f"history CSV identity changes within {isin}")
            day = _parse_iso_day(row.get("date"), f"history CSV row {ridx} date")
            close = _finite(row.get("close"), f"history CSV row {ridx} close")
            open_ = _finite(row.get("open"), f"history CSV row {ridx} open")
            high = _finite(row.get("high"), f"history CSV row {ridx} high")
            low = _finite(row.get("low"), f"history CSV row {ridx} low")
            volume_text = str(row.get("volume", "")).strip()
            volume = None if not volume_text else _finite(volume_text, f"history CSV row {ridx} volume")
            target["bars"].append({"date": day.isoformat(), "open": open_, "high": high, "low": low, "close": close, "volume": volume})
    if not grouped:
        raise HistoryError("history CSV contains no data rows")
    for target in grouped.values():
        target["bars"].sort(key=lambda bar: bar["date"])
        days = [bar["date"] for bar in target["bars"]]
        if len(days) != len(set(days)):
            raise HistoryError(f"history CSV contains duplicate session dates for {target['isin']}")
        if len(days) < 21:
            raise HistoryError(f"history CSV has fewer than 21 sessions for {target['isin']}")
    document = {
        "schema": HISTORY_SCHEMA,
        "prototype_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "imported_csv",
        "quote_type": "daily_raw_ohlcv",
        "requested_outputsize": None,
        "targets": sorted(grouped.values(), key=lambda item: item["isin"]),
    }
    # Validate canonical form before publishing it. Never replace a previously
    # usable history file with malformed imported evidence.
    validation_path = output_path.with_name(output_path.name + ".validate")
    try:
        _json_dump(validation_path, document)
        load_history(validation_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        validation_path.replace(output_path)
    finally:
        if validation_path.exists():
            validation_path.unlink()
    return document

def load_history(path: Path) -> tuple[dict[str, Any], list[HistoricalTarget]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryError(f"cannot read historical market data: {path}") from exc
    if not isinstance(raw, dict) or raw.get("schema") != HISTORY_SCHEMA:
        raise HistoryError("historical market data must be schema 1")
    items = raw.get("targets")
    if not isinstance(items, list) or not items:
        raise HistoryError("historical market data targets must be non-empty")
    targets: list[HistoricalTarget] = []
    seen: set[str] = set()
    for tidx, item in enumerate(items):
        if not isinstance(item, dict) or item.get("status", "ok") != "ok":
            raise HistoryError(f"history target {tidx} is not usable")
        isin = str(item.get("isin", "")).strip().upper()
        if len(isin) != 12 or not isin.isalnum() or isin in seen:
            raise HistoryError(f"history target {tidx} has invalid/duplicate ISIN")
        name = str(item.get("name", "")).strip()
        symbol = str(item.get("symbol", "")).strip()
        currency = str(item.get("currency", "")).strip().upper()
        region = str(item.get("region", "")).strip()
        raw_bars = item.get("bars")
        if not name or not symbol or not isinstance(raw_bars, list) or len(raw_bars) < 21:
            raise HistoryError(f"history target {isin} is incomplete")
        bars: list[HistoricalBar] = []
        prior: date | None = None
        for bidx, bar in enumerate(raw_bars):
            if not isinstance(bar, dict):
                raise HistoryError(f"{isin} bar {bidx} must be an object")
            day = _parse_iso_day(bar.get("date"), f"{isin}.bars[{bidx}].date")
            if prior is not None and day <= prior:
                raise HistoryError(f"{isin} bars must be strictly chronological")
            close = _finite(bar.get("close"), f"{isin}.bars[{bidx}].close")
            open_ = _finite(bar.get("open", close), f"{isin}.bars[{bidx}].open")
            high = _finite(bar.get("high", close), f"{isin}.bars[{bidx}].high")
            low = _finite(bar.get("low", close), f"{isin}.bars[{bidx}].low")
            volume_raw = bar.get("volume")
            volume = None if volume_raw in (None, "") else _finite(volume_raw, f"{isin}.bars[{bidx}].volume")
            if min(open_, high, low, close) <= 0:
                raise HistoryError(f"{isin} bar prices must be > 0")
            bars.append(HistoricalBar(day, open_, high, low, close, volume))
            prior = day
        targets.append(HistoricalTarget(isin, name, symbol, currency, region, tuple(bars)))
        seen.add(isin)
    return raw, targets


def _session_metrics(bars: tuple[HistoricalBar, ...], idx: int) -> dict[str, Any]:
    if idx < 20:
        raise HistoryError("at least 21 completed sessions are required")
    latest = bars[idx]
    close5 = bars[idx - 5].close
    close20 = bars[idx - 20].close
    high20 = max(bar.close for bar in bars[idx - 19 : idx + 1])
    metrics = {
        "as_of": latest.day.isoformat(),
        "latest_close": latest.close,
        "return_5d": latest.close / close5 - 1.0,
        "return_20d": latest.close / close20 - 1.0,
        "drawdown_from_20d_high": latest.close / high20 - 1.0,
    }
    metrics["signals"] = tt.tactical_signals(metrics)
    return metrics


def _stress_qualified(metrics: dict[str, Any]) -> bool:
    signal = float(metrics["signals"]["rebound_aware"])
    return signal + tp.EPS >= tp.MIN_STRESS_SIGNAL and (
        float(metrics["return_20d"]) <= tp.MIN_RETURN_20D + tp.EPS
        or float(metrics["drawdown_from_20d_high"]) <= tp.MIN_DRAWDOWN_20D + tp.EPS
    )


def _month_add(day: date, months: int) -> date:
    absolute = day.year * 12 + (day.month - 1) + months
    year, month0 = divmod(absolute, 12)
    month = month0 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def generate_cycle_dates(anchor: date, start: date, end: date, frequency: str) -> list[date]:
    if frequency not in tp.CADENCE_POLICY:
        raise HistoryError(f"unsupported frequency: {frequency}")
    if start > end:
        raise HistoryError("start must not be after end")
    step_months = {"monthly": 1, "quarterly": 3, "yearly": 12}.get(frequency)
    dates: list[date] = []
    n = 0
    while True:
        current = (
            anchor + timedelta(days=7 * n)
            if frequency == "weekly"
            else _month_add(anchor, int(step_months) * n)
        )
        if current > end:
            break
        if current >= start:
            dates.append(current)
        n += 1
        if n > 10000:
            raise HistoryError("cycle schedule exceeded safety bound")
    return dates


def _last_session_index(bars: tuple[HistoricalBar, ...], on_or_before: date) -> int | None:
    lo, hi = 0, len(bars) - 1
    found: int | None = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if bars[mid].day <= on_or_before:
            found = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return found


def _recovery_confirmation(
    daily: list[dict[str, Any] | None],
    previous_idx: int | None,
    current_idx: int,
    confirm_sessions: int,
) -> dict[str, Any] | None:
    """Return the first newly confirmed continuous non-stress recovery run.

    Recovery evidence is market-session based, not cadence-window based. The
    scan therefore preserves a partial non-stress streak that began on or before
    the previous PA cycle and allows the market session used by the current PA
    cycle to complete the configured run. Only a threshold crossing *after* the
    previous cycle counts as a new recovery confirmation.

    This makes the same five completed market sessions mean the same thing for
    weekly, monthly, quarterly, and yearly PA schedules. Daily sessions still
    never advance governance state; they only prove that recovery occurred.
    """
    if previous_idx is None or confirm_sessions <= 0 or current_idx <= previous_idx:
        return None

    run = 0
    run_started: str | None = None
    for idx in range(0, current_idx + 1):
        metrics = daily[idx]
        if metrics is None:
            continue
        if _stress_qualified(metrics):
            run = 0
            run_started = None
            continue
        if run == 0:
            run_started = str(metrics.get("as_of", f"session_index:{idx}"))
        run += 1
        # Report only the first threshold crossing for a continuous calm run,
        # and only if that crossing happened after the previous PA cycle. A run
        # already confirmed before or on the previous cycle is not rediscovered.
        if run == confirm_sessions and idx > previous_idx:
            return {
                "required_nonstress_sessions": confirm_sessions,
                "run_started_on": run_started,
                "confirmed_on": str(metrics.get("as_of", f"session_index:{idx}")),
                "observed_nonstress_sessions": run,
                "confirmation_includes_current_cycle_session": idx == current_idx,
            }
    return None


def _confirmed_recovery(
    daily: list[dict[str, Any] | None],
    previous_idx: int | None,
    current_idx: int,
    confirm_sessions: int,
) -> bool:
    return _recovery_confirmation(daily, previous_idx, current_idx, confirm_sessions) is not None


def build_cycle_history(
    target: HistoricalTarget,
    *,
    frequency: str,
    anchor: date,
    start: date,
    end: date,
    recovery_confirm_sessions: int,
) -> tuple[tp.TargetHistory | None, list[dict[str, Any]], str | None]:
    cycle_dates = generate_cycle_dates(anchor, start, end, frequency)
    daily: list[dict[str, Any] | None] = [None] * len(target.bars)
    for idx in range(20, len(target.bars)):
        daily[idx] = _session_metrics(target.bars, idx)

    observations: list[tp.CycleObservation] = []
    rows: list[dict[str, Any]] = []
    previous_idx: int | None = None
    for cycle_day in cycle_dates:
        idx = _last_session_index(target.bars, cycle_day)
        if idx is None or idx < 20:
            continue
        metrics = daily[idx]
        assert metrics is not None
        recovery_confirmation = _recovery_confirmation(
            daily, previous_idx, idx, recovery_confirm_sessions
        )
        recovered = recovery_confirmation is not None
        signal = float(metrics["signals"]["rebound_aware"])
        observation = tp.CycleObservation(
            cycle_date=cycle_day,
            tactical_signal=signal,
            return_5d=float(metrics["return_5d"]),
            return_20d=float(metrics["return_20d"]),
            drawdown_from_20d_high=float(metrics["drawdown_from_20d_high"]),
            recovered_since_previous_cycle=recovered,
            selected_by_tt=None,
            note=f"market_as_of={metrics['as_of']}",
        )
        observations.append(observation)
        rows.append({
            "cycle_date": cycle_day.isoformat(),
            "market_as_of": metrics["as_of"],
            "latest_close": metrics["latest_close"],
            "return_5d": metrics["return_5d"],
            "return_20d": metrics["return_20d"],
            "drawdown_from_20d_high": metrics["drawdown_from_20d_high"],
            "rebound_aware_signal": signal,
            "stress_qualified": observation.stress_qualified,
            "recovered_since_previous_cycle": recovered,
            "recovery_confirmation": recovery_confirmation,
        })
        previous_idx = idx

    min_cycles = tp.CADENCE_POLICY[frequency]["review_cycles"]
    if len(observations) < min_cycles:
        return None, rows, f"insufficient_cycles:{len(observations)}<{min_cycles}"
    return tp.TargetHistory(
        scenario_id=f"historical:{target.isin}:{frequency}",
        description="real historical market replay",
        plan_frequency=frequency,
        isin=target.isin,
        name=target.name,
        observations=tuple(observations),
    ), rows, None


def _episode_metrics(result: dict[str, Any]) -> dict[str, Any]:
    observations = result["observations"]
    review_dates: list[str] = []
    prior_review = False
    watch_cycles = 0
    opportunity_cycles = 0
    stressed_cycles = 0
    for row in observations:
        stressed_cycles += int(bool(row["stress_qualified"]))
        state = row["state_after_cycle"]
        opportunity_cycles += int(state == "tactical_opportunity")
        watch_cycles += int(state == "tactical_watch")
        review = state == "strategic_review_due"
        if review and not prior_review:
            review_dates.append(row["cycle_date"])
        prior_review = review
    max_episode_cycles = 0
    for episode in list(result.get("closed_episodes") or []) + ([result["active_episode"]] if result.get("active_episode") else []):
        max_episode_cycles = max(max_episode_cycles, int(episode["stressed_planning_cycles"]))
    return {
        "planning_cycles": len(observations),
        "stressed_cycles": stressed_cycles,
        "tactical_opportunity_cycles": opportunity_cycles,
        "tactical_watch_cycles": watch_cycles,
        "strategic_review_entries": len(review_dates),
        "strategic_review_entry_dates": review_dates,
        "max_episode_stressed_cycles": max_episode_cycles,
        "closed_episode_count": int(result.get("closed_episode_count", 0)),
        "final_state": result["final_state"],
    }


_STATE_RANK = {
    "normal": 0,
    "tactical_opportunity": 1,
    "tactical_watch": 2,
    "strategic_review_due": 3,
}


def _episode_forensics(
    evaluation: dict[str, Any],
    raw_rows: list[dict[str, Any]],
    *,
    recovery_confirm_sessions: int,
) -> list[dict[str, Any]]:
    """Build dated episode evidence aligned with confirmed-recovery continuity."""
    raw_by_cycle = {str(row["cycle_date"]): row for row in raw_rows}
    observations = evaluation.get("observations") or []
    episodes: list[dict[str, Any]] = []
    active_rows: list[tuple[dict[str, Any], dict[str, Any]]] = []

    def close_active(
        *,
        status: str,
        reason: str | None = None,
        observed_on_cycle: str | None = None,
        recovery_confirmation: dict[str, Any] | None = None,
    ) -> None:
        nonlocal active_rows
        if not active_rows:
            return
        eval_rows = [pair[0] for pair in active_rows]
        market_rows = [pair[1] for pair in active_rows]
        stressed = [
            (erow, mrow)
            for erow, mrow in active_rows
            if bool(erow.get("stress_qualified"))
        ]
        if not stressed:
            raise HistoryError("active forensic episode has no stressed planning cycle")
        stressed_eval = [pair[0] for pair in stressed]
        stressed_market = [pair[1] for pair in stressed]
        started = date.fromisoformat(str(stressed_eval[0]["cycle_date"]))
        last_stressed = date.fromisoformat(str(stressed_eval[-1]["cycle_date"]))
        last_observed = date.fromisoformat(str(eval_rows[-1]["cycle_date"]))
        highest = max(
            (str(row["state_after_cycle"]) for row in eval_rows),
            key=lambda state: _STATE_RANK.get(state, -1),
        )
        closure: dict[str, Any] | None = None
        if status == "closed":
            closure = {
                "reason": reason,
                "observed_on_cycle": observed_on_cycle,
                "recovery_confirmed": recovery_confirmation is not None,
                "required_nonstress_sessions": recovery_confirm_sessions,
                "recovery_confirmation": recovery_confirmation,
            }
        unresolved_nonstress = sum(
            not bool(row.get("stress_qualified")) for row in eval_rows
        )
        episodes.append({
            "episode_number": len(episodes) + 1,
            "status": status,
            "continuity_state": (
                "closed_recovered"
                if status == "closed"
                else (
                    "active_stressed"
                    if bool(eval_rows[-1].get("stress_qualified"))
                    else "active_unresolved"
                )
            ),
            "started_cycle": started.isoformat(),
            "last_stressed_cycle": last_stressed.isoformat(),
            "last_observed_cycle": last_observed.isoformat(),
            "elapsed_days": (last_observed - started).days,
            "stressed_planning_cycles": len(stressed_eval),
            "unresolved_nonstress_planning_cycles": unresolved_nonstress,
            "first_market_as_of": str(stressed_market[0]["market_as_of"]),
            "last_stressed_market_as_of": str(stressed_market[-1]["market_as_of"]),
            "last_observed_market_as_of": str(market_rows[-1]["market_as_of"]),
            "peak_tactical_signal": max(float(row["tactical_signal"]) for row in stressed_eval),
            "latest_stressed_tactical_signal": float(stressed_eval[-1]["tactical_signal"]),
            "latest_observed_tactical_signal": float(eval_rows[-1]["tactical_signal"]),
            "worst_return_5d": min(float(row["return_5d"]) for row in stressed_eval),
            "worst_return_20d": min(float(row["return_20d"]) for row in stressed_eval),
            "worst_drawdown_from_20d_high": min(
                float(row["drawdown_from_20d_high"]) for row in stressed_eval
            ),
            "highest_state": highest,
            "closure": closure,
        })
        active_rows = []

    for eval_row in observations:
        cycle = str(eval_row["cycle_date"])
        raw = raw_by_cycle.get(cycle)
        if raw is None:
            raise HistoryError(f"missing raw cycle evidence for {cycle}")

        # Confirmed recovery closes the previous episode before the current PA
        # cycle is evaluated. If weakness has returned, the current cycle starts
        # a new episode rather than extending the recovered one.
        if bool(eval_row.get("recovered_since_previous_cycle")) and active_rows:
            close_active(
                status="closed",
                reason="recovered_between_planning_cycles",
                observed_on_cycle=cycle,
                recovery_confirmation=raw.get("recovery_confirmation"),
            )

        if bool(eval_row.get("stress_qualified")):
            active_rows.append((eval_row, raw))
        elif active_rows:
            # No confirmed recovery: retain the episode as unresolved. This PA
            # cycle extends elapsed persistence but does not increment stressed
            # cycle count.
            active_rows.append((eval_row, raw))

    close_active(status="active")
    return episodes


def replay_history(
    history_path: Path,
    output_dir: Path,
    *,
    anchor: date,
    start: date,
    end: date,
    frequencies: tuple[str, ...],
    recovery_confirm_sessions: int,
) -> dict[str, Any]:
    if recovery_confirm_sessions < 1:
        raise HistoryError("recovery-confirm-sessions must be >= 1")
    source_doc, targets = load_history(history_path)
    results: list[dict[str, Any]] = []
    for target in targets:
        cadence_rows: list[dict[str, Any]] = []
        for frequency in frequencies:
            history, raw_rows, unavailable = build_cycle_history(
                target,
                frequency=frequency,
                anchor=anchor,
                start=start,
                end=end,
                recovery_confirm_sessions=recovery_confirm_sessions,
            )
            if history is None:
                cadence_rows.append({
                    "frequency": frequency,
                    "status": "insufficient_history",
                    "detail": unavailable,
                    "cycle_observations": raw_rows,
                })
                continue
            evaluation = tp.evaluate_history(history)
            cadence_rows.append({
                "frequency": frequency,
                "status": "ok",
                "summary": _episode_metrics(evaluation),
                "cycle_observations": raw_rows,
                "persistence": evaluation,
                "episode_forensics": _episode_forensics(
                    evaluation,
                    raw_rows,
                    recovery_confirm_sessions=recovery_confirm_sessions,
                ),
            })
        results.append({
            "isin": target.isin,
            "name": target.name,
            "symbol": target.symbol,
            "history_first_session": target.bars[0].day.isoformat(),
            "history_last_session": target.bars[-1].day.isoformat(),
            "history_sessions": len(target.bars),
            "cadences": cadence_rows,
        })

    document = {
        "schema": 1,
        "prototype_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "research-only historical cadence replay",
        "history_source": source_doc.get("source", "unknown"),
        "history_requested_outputsize": source_doc.get("requested_outputsize"),
        "replay_window": {"anchor": anchor.isoformat(), "start": start.isoformat(), "end": end.isoformat()},
        "frequencies": list(frequencies),
        "recovery_policy": {
            "confirmed_nonstress_sessions": recovery_confirm_sessions,
            "confirmation_scope": "continuous_completed_sessions_across_pa_cycle_boundaries",
            "current_cycle_market_session_can_complete_recovery": True,
            "partial_recovery_streak_carries_across_cycle_boundary": True,
            "daily_sessions_advance_governance": False,
            "nonqualified_planning_cycle_alone_closes_episode": False,
            "confirmed_recovery_required_for_market_episode_closure": True,
        },
        "qualification_policy": {
            "minimum_rebound_aware_signal": tp.MIN_STRESS_SIGNAL,
            "return_20d_lte": tp.MIN_RETURN_20D,
            "or_drawdown_from_20d_high_lte": tp.MIN_DRAWDOWN_20D,
        },
        "cadence_policy": tp.CADENCE_POLICY,
        "targets": results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _json_dump(output_dir / "historical_replay.json", document)
    (output_dir / "historical_replay_report.txt").write_text(render_report(document), encoding="utf-8")
    (output_dir / "episode_forensics_report.txt").write_text(
        render_forensics_report(document), encoding="utf-8"
    )
    return document


def _pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def render_report(document: dict[str, Any]) -> str:
    lines = [
        "Portfolio Architect Tactical Tilt historical cadence replay",
        f"prototype_version: {document['prototype_version']}",
        f"generated_at: {document['generated_at']}",
        f"history_source: {document['history_source']}",
        f"history_requested_outputsize: {document.get('history_requested_outputsize')}",
        f"replay_window: {document['replay_window']['start']}..{document['replay_window']['end']}",
        f"anchor: {document['replay_window']['anchor']}",
        "",
        "BOUNDARIES",
        "  Real daily history supplies evidence only; governance advances on synthetic PA cycles.",
        "  Replay never infers historical execution and never creates tactical debt.",
        "  Strategic-review prompts remain advisory; target replacement remains human-owned.",
        "",
        "RECOVERY POLICY",
        f"  confirmation: {document['recovery_policy']['confirmed_nonstress_sessions']} consecutive non-stress completed market sessions",
        "  recovery streaks carry across PA-cycle boundaries; the current cycle session may complete the run",
        "  daily sessions prove recovery but never advance governance state",
        "  a non-qualified PA cycle without confirmed recovery leaves the episode unresolved",
        "",
        "RESULTS",
    ]
    for target in document["targets"]:
        lines.append(f"  {target['isin']}  {target['name']}  ({target['symbol']})")
        lines.append(
            f"    history: {target['history_first_session']}..{target['history_last_session']}  sessions={target['history_sessions']}"
        )
        for cadence in target["cadences"]:
            if cadence["status"] != "ok":
                lines.append(f"    {cadence['frequency']:<9} insufficient  {cadence.get('detail')}")
                continue
            s = cadence["summary"]
            entries = ",".join(s["strategic_review_entry_dates"]) or "none"
            lines.append(
                f"    {cadence['frequency']:<9} cycles={s['planning_cycles']:>3} stressed={s['stressed_cycles']:>3} "
                f"watch={s['tactical_watch_cycles']:>3} review_entries={s['strategic_review_entries']:>2} "
                f"max_episode={s['max_episode_stressed_cycles']:>2} final={s['final_state']}"
            )
            lines.append(f"              review_entry_dates: {entries}")
        lines.append("")
    lines.extend([
        "INTERPRETATION",
        "  Review entries are calibration evidence, not a conclusion that an asset was defective.",
        "  Inspect episode_forensics_report.txt before changing stress or cadence thresholds.",
        "  Compact Alpha Vantage history may be too short for quarterly/yearly calibration; those cadences are reported as insufficient rather than guessed.",
    ])
    return "\n".join(lines) + "\n"


def render_forensics_report(document: dict[str, Any]) -> str:
    lines = [
        "Portfolio Architect Tactical Tilt historical episode forensics",
        f"prototype_version: {document['prototype_version']}",
        f"generated_at: {document['generated_at']}",
        f"history_source: {document['history_source']}",
        f"replay_window: {document['replay_window']['start']}..{document['replay_window']['end']}",
        "",
        "BOUNDARIES",
        "  Episodes describe qualified market weakness observed at synthetic PA cycles.",
        "  Daily sessions may confirm recovery but never advance governance by themselves.",
        "  Strategic-review evidence remains advisory; target replacement remains human-owned.",
        "",
        "EPISODES",
    ]
    for target in document["targets"]:
        lines.append(f"  {target['isin']}  {target['name']}  ({target['symbol']})")
        for cadence in target["cadences"]:
            frequency = cadence["frequency"]
            if cadence["status"] != "ok":
                lines.append(f"    {frequency}: insufficient ({cadence.get('detail')})")
                continue
            episodes = cadence.get("episode_forensics") or []
            lines.append(f"    {frequency}: episodes={len(episodes)}")
            if not episodes:
                lines.append("      none")
                continue
            for episode in episodes:
                lines.append(
                    f"      episode {episode['episode_number']} [{episode['status']}] "
                    f"{episode['started_cycle']}..{episode['last_stressed_cycle']} "
                    f"observed_through={episode['last_observed_cycle']} "
                    f"continuity={episode['continuity_state']}"
                )
                lines.append(
                    f"        stressed_cycles={episode['stressed_planning_cycles']}  "
                    f"unresolved_nonstress_cycles={episode['unresolved_nonstress_planning_cycles']}  "
                    f"elapsed_days={episode['elapsed_days']}  highest_state={episode['highest_state']}"
                )
                lines.append(
                    f"        stressed_market_as_of={episode['first_market_as_of']}..{episode['last_stressed_market_as_of']}  "
                    f"last_observed_market_as_of={episode['last_observed_market_as_of']}"
                )
                lines.append(
                    f"        peak_signal={episode['peak_tactical_signal']:.3f}  "
                    f"latest_stressed_signal={episode['latest_stressed_tactical_signal']:.3f}  "
                    f"latest_observed_signal={episode['latest_observed_tactical_signal']:.3f}"
                )
                lines.append(
                    f"        worst_5d={_pct(episode['worst_return_5d'])}  "
                    f"worst_20d={_pct(episode['worst_return_20d'])}  "
                    f"max_drawdown={_pct(episode['worst_drawdown_from_20d_high'])}"
                )
                closure = episode.get("closure")
                if closure is None:
                    lines.append(f"        closure={episode['continuity_state']}")
                else:
                    lines.append(
                        f"        closure={closure['reason']}  "
                        f"observed_on_cycle={closure['observed_on_cycle']}"
                    )
                    confirmation = closure.get("recovery_confirmation")
                    if confirmation:
                        lines.append(
                            f"        recovery={confirmation['observed_nonstress_sessions']} consecutive "
                            f"non-stress sessions {confirmation['run_started_on']}..{confirmation['confirmed_on']} "
                            f"(required={confirmation['required_nonstress_sessions']})"
                        )
                    else:
                        lines.append("        recovery=missing_confirmation_error")
        lines.append("")
    lines.extend([
        "INTERPRETATION",
        "  Episode boundaries are evidence for threshold calibration, not labels of asset quality.",
        "  A closed episode followed by a later episode is intentionally not treated as one permanent counter.",
        "  A merely non-qualified PA cycle does not close an unresolved episode without confirmed recovery.",
        "  Recovery confirmation is market-session based and cadence-independent across PA-cycle boundaries.",
        "  Compare the dated evidence with the market chart before changing qualification, recovery, or cadence thresholds.",
    ])
    return "\n".join(lines) + "\n"


def _parse_frequencies(value: str) -> tuple[str, ...]:
    parts = tuple(part.strip().lower() for part in value.split(",") if part.strip())
    if not parts or any(part not in tp.CADENCE_POLICY for part in parts):
        raise argparse.ArgumentTypeError("frequencies must be comma-separated weekly,monthly,quarterly,yearly")
    return parts


def _require_av_key() -> str:
    key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
    if not key:
        raise HistoryError("ALPHAVANTAGE_API_KEY is required for history-fetch")
    return key


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("history-fetch", help="fetch real Alpha Vantage daily history using cached listing identities")
    fetch.add_argument("--mapping", type=Path, default=Path("output/mapping.json"))
    fetch.add_argument("--output", type=Path, default=Path("output/history/historical_market_data.json"))
    fetch.add_argument("--outputsize", choices=("compact", "full"), default="compact")
    fetch.add_argument("--pause-seconds", type=float, default=md.DEFAULT_AV_MIN_INTERVAL_SECONDS)
    fetch.add_argument("--av-daily-limit", type=int, default=md.DEFAULT_AV_DAILY_LIMIT)
    fetch.add_argument("--av-used-last-24h", type=int, default=0)

    imp = sub.add_parser("history-import-csv", help="import provider-neutral daily OHLCV CSV into the canonical history format")
    imp.add_argument("--csv", type=Path, required=True)
    imp.add_argument("--output", type=Path, default=Path("output/history/historical_market_data.json"))

    replay = sub.add_parser("history-replay", help="replay real historical daily prices through cadence-aware TT persistence")
    replay.add_argument("--history", type=Path, default=Path("output/history/historical_market_data.json"))
    replay.add_argument("--output-dir", type=Path, default=Path("output/tactical_tilt/history"))
    replay.add_argument("--anchor", type=lambda v: _parse_iso_day(v, "anchor"), required=True)
    replay.add_argument("--start", type=lambda v: _parse_iso_day(v, "start"), required=True)
    replay.add_argument("--end", type=lambda v: _parse_iso_day(v, "end"), required=True)
    replay.add_argument("--frequencies", type=_parse_frequencies, default=DEFAULT_FREQUENCIES)
    replay.add_argument("--recovery-confirm-sessions", type=int, default=DEFAULT_RECOVERY_CONFIRM_SESSIONS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "history-fetch":
            av_key = _require_av_key()
            state_path = args.mapping.parent / ".alpha_vantage_usage.json"
            guard = md.AlphaVantageGuard(
                state_path,
                min_interval_seconds=args.pause_seconds,
                daily_limit=args.av_daily_limit,
                initial_used_last_24h=args.av_used_last_24h,
            )
            document = fetch_history(args.mapping, args.output, av_key, guard, outputsize=args.outputsize)
            print(f"history: ok={len(document['targets'])} outputsize={args.outputsize}")
            usage = guard.usage()
            limit = usage["daily_limit"]
            if limit:
                print(f"alpha_vantage local usage: {usage['request_count']}/{limit} call(s) in rolling 24h; remaining={usage['remaining']}")
            else:
                print(f"alpha_vantage local usage: {usage['request_count']} call(s) in rolling 24h; local ceiling disabled")
            print(f"history file: {args.output}")
            return 0
        if args.command == "history-import-csv":
            document = import_history_csv(args.csv, args.output)
            print(f"history import: ok={len(document['targets'])}")
            print(f"history file: {args.output}")
            return 0
        if args.command == "history-replay":
            document = replay_history(
                args.history,
                args.output_dir,
                anchor=args.anchor,
                start=args.start,
                end=args.end,
                frequencies=args.frequencies,
                recovery_confirm_sessions=args.recovery_confirm_sessions,
            )
            ok = sum(1 for target in document["targets"] for row in target["cadences"] if row["status"] == "ok")
            insufficient = sum(1 for target in document["targets"] for row in target["cadences"] if row["status"] != "ok")
            print(f"historical replay: ok={ok} insufficient={insufficient}")
            print(f"report: {args.output_dir / 'historical_replay_report.txt'}")
            print(f"forensics: {args.output_dir / 'episode_forensics_report.txt'}")
            return 0
        raise HistoryError("unknown command")
    except (HistoryError, md.PocError, md.ProviderError, tp.PersistenceError, tt.TiltError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
