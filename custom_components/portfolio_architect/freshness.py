"""Privacy-safe source-evidence freshness presentation helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

_FUTURE_TOLERANCE_SECONDS = 5 * 60
_MAX_SUMMARY_CHARS = 240
_STATIC_WEEKLY_DEFAULT_HOURS = 5 * 24
_STATIC_MONTHLY_DEFAULT_HOURS = 14 * 24
_LIVE_DEFAULT_HOURS = 24


def default_static_freshness_hours(plan_frequency: str | None) -> int:
    """Return the cadence-aware default for manually refreshed evidence.

    Weekly execution should see a fresh upload at least once within roughly one
    execution period, while monthly-or-slower plans should not require weekly
    operator work merely to remain actionable.  Explicit configured thresholds
    always override this default in the coordinator.
    """
    token = str(plan_frequency or "").strip().lower()
    return _STATIC_WEEKLY_DEFAULT_HOURS if token == "weekly" else _STATIC_MONTHLY_DEFAULT_HOURS


def default_freshness_thresholds(
    plan_frequency: str | None,
    *,
    legacy_threshold_hours: int = _LIVE_DEFAULT_HOURS,
    preserve_legacy_global: bool = False,
) -> dict[str, int]:
    """Return unconfigured evidence-kind defaults without overriding user policy.

    A pre-v1.33 installation that explicitly configured only the historical global
    threshold keeps that value for every evidence family until the operator saves
    provider-specific thresholds.  Otherwise live evidence defaults to 24 hours and
    manual CSV/PDF evidence follows the plan cadence.
    """
    legacy = max(1, int(legacy_threshold_hours))
    if preserve_legacy_global:
        live = static = legacy
    else:
        live = _LIVE_DEFAULT_HOURS
        static = default_static_freshness_hours(plan_frequency)
    return {
        "live_api": live,
        "gateway_snapshot": live,
        "imported_statement": static,
        "imported_csv": static,
        "csv": static,
        "other": live,
    }


def annotate_source_acquisition_modes(
    source_summaries: Iterable[dict[str, Any]],
    acquisition_modes: Mapping[str, str | None],
) -> tuple[dict[str, Any], ...]:
    """Return source summaries annotated with the latest Gateway acquisition modes.

    Only providers explicitly present in ``acquisition_modes`` are changed.  A
    ``None`` mode deliberately removes any older annotation so a schema downgrade
    or legacy health response falls back to the conservative provider evidence
    class instead of retaining a stale static classification.
    """
    modes = {str(provider): mode for provider, mode in acquisition_modes.items()}
    rows: list[dict[str, Any]] = []
    for item in source_summaries:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        provider = row.get("provider")
        if isinstance(provider, str) and provider in modes:
            mode = modes[provider]
            if isinstance(mode, str) and mode.strip():
                row["acquisition_mode"] = mode.strip().lower()
            else:
                row.pop("acquisition_mode", None)
        rows.append(row)
    return tuple(rows)


def evidence_kind(provider: str, acquisition_mode: str | None = None) -> str:
    """Return a bounded provider/acquisition-aware holdings evidence kind."""
    token = str(provider or "").strip().lower()
    mode = str(acquisition_mode or "").strip().lower()
    if mode == "live_api":
        return "live_api"
    if mode == "csv":
        return "csv"
    if mode == "pdf":
        return "imported_statement"
    # Schema <=6 and other legacy/unknown Gateway health documents do not carry
    # acquisition_mode.  Keep the conservative established fallbacks.
    if token == "comdirect":
        return "live_api"
    if token == "trade_republic":
        return "imported_statement"
    if token in {"dkb", "local_rest_json"}:
        return "gateway_snapshot"
    return "other"


def cash_evidence_kind(provider: str, acquisition_mode: str | None = None) -> str:
    """Return the acquisition-aware evidence family governing provider cash."""
    token = str(provider or "").strip().lower()
    mode = str(acquisition_mode or "").strip().lower()
    if mode == "live_api":
        return "live_api"
    if mode == "csv":
        return "csv"
    if mode == "pdf":
        return "imported_statement"
    if token == "comdirect":
        return "live_api"
    if token in {"trade_republic", "dkb"}:
        return "imported_statement"
    if token == "local_rest_json":
        return "gateway_snapshot"
    return "other"


def source_freshness_rows(
    source_summaries: Iterable[dict[str, Any]],
    *,
    now: datetime,
    threshold_hours: int,
    threshold_hours_by_kind: Mapping[str, int] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Build bounded age evidence for each contributing source.

    ``threshold_hours`` remains the compatibility fallback used by pre-v1.33
    configurations.  Explicit evidence-kind thresholds override it only when the
    user has deliberately configured them.
    """
    if now.tzinfo is None:
        raise ValueError("Freshness evaluation time must include a timezone")
    current = now.astimezone(timezone.utc)
    fallback_threshold = max(0, int(threshold_hours))
    thresholds = {
        str(key): max(0, int(value))
        for key, value in (threshold_hours_by_kind or {}).items()
        if not isinstance(value, bool)
    }
    rows: list[dict[str, Any]] = []
    for item in source_summaries:
        if not isinstance(item, dict):
            continue
        source_id = _bounded_text(item.get("source_id"), fallback="unknown", maximum=32)
        provider = _bounded_text(item.get("provider"), fallback="unknown", maximum=32)
        label = _bounded_text(item.get("label"), fallback=source_id, maximum=80)
        acquisition_mode = item.get("acquisition_mode") if isinstance(item, dict) else None
        kind = evidence_kind(provider, acquisition_mode if isinstance(acquisition_mode, str) else None)
        effective_threshold = thresholds.get(kind, fallback_threshold)
        threshold_seconds = effective_threshold * 3600
        generated_at = _parse_timestamp(item.get("generated_at"))
        if generated_at is None:
            rows.append(
                {
                    "source_id": source_id,
                    "provider": provider,
                    "label": label,
                    "evidence_kind": kind,
                    "generated_at": None,
                    "age_seconds": None,
                    "threshold_hours": effective_threshold,
                    "within_age_threshold": False,
                    "timestamp_status": "invalid",
                }
            )
            continue
        age_seconds = int((current - generated_at).total_seconds())
        if age_seconds < -_FUTURE_TOLERANCE_SECONDS:
            timestamp_status = "future"
            within = False
        else:
            timestamp_status = "ok"
            within = age_seconds <= threshold_seconds
        rows.append(
            {
                "source_id": source_id,
                "provider": provider,
                "label": label,
                "evidence_kind": kind,
                "generated_at": generated_at.isoformat(),
                "age_seconds": age_seconds,
                "threshold_hours": effective_threshold,
                "within_age_threshold": within,
                "timestamp_status": timestamp_status,
            }
        )
    return tuple(rows)


def stale_rows(rows: Iterable[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Return only age-threshold blockers from previously bounded rows."""
    return tuple(item for item in rows if item.get("within_age_threshold") is False)


def stale_summary(
    rows: Iterable[dict[str, Any]],
    *,
    german: bool = False,
) -> str:
    """Return one bounded human-readable blocker summary."""
    blockers = tuple(rows)
    if not blockers:
        return "Keine" if german else "None"
    first = blockers[0]
    label = _bounded_text(first.get("label"), fallback="Source", maximum=80)
    status = first.get("timestamp_status")
    if status == "invalid":
        text = f"{label} · ungültiger Zeitstempel" if german else f"{label} · invalid timestamp"
    elif status == "future":
        text = f"{label} · Zeitstempel liegt in der Zukunft" if german else f"{label} · timestamp is in the future"
    else:
        age = first.get("age_seconds")
        threshold = first.get("threshold_hours")
        age_text = _age_text(age, german=german)
        limit_text = _limit_text(threshold, german=german)
        if german:
            text = f"{label} · {age_text} alt · Grenze {limit_text}"
        else:
            text = f"{label} · {age_text} old · limit {limit_text}"
    if len(blockers) > 1:
        suffix = f" · +{len(blockers) - 1} weitere" if german else f" · +{len(blockers) - 1} more"
        text += suffix
    return _bounded_summary(text)


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _bounded_text(value: Any, *, fallback: str, maximum: int) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        text = fallback
    cleaned = " ".join(text.split())
    return cleaned[:maximum]


def _age_text(value: Any, *, german: bool) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        return "unbekannt" if german else "unknown"
    seconds = max(value, 0)
    if seconds >= 48 * 3600:
        days = seconds / 86400
        token = f"{days:.1f}".replace(".", ",") if german else f"{days:.1f}"
        return f"{token} Tage" if german else f"{token} days"
    if seconds >= 2 * 3600:
        hours = seconds / 3600
        token = f"{hours:.1f}".replace(".", ",") if german else f"{hours:.1f}"
        return f"{token} Stunden" if german else f"{token} hours"
    minutes = max(0, seconds // 60)
    return f"{minutes} Min." if german else f"{minutes} min"


def _limit_text(value: Any, *, german: bool) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        return "unbekannt" if german else "unknown"
    if value and value % 24 == 0:
        days = value // 24
        if german:
            return f"{days} Tag" if days == 1 else f"{days} Tage"
        return f"{days} day" if days == 1 else f"{days} days"
    if german:
        return f"{value} Stunde" if value == 1 else f"{value} Stunden"
    return f"{value} hour" if value == 1 else f"{value} hours"


def _bounded_summary(value: str) -> str:
    if len(value) <= _MAX_SUMMARY_CHARS:
        return value
    return value[: _MAX_SUMMARY_CHARS - 1].rstrip() + "…"
