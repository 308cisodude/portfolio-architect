"""Pure resilience helpers for Portfolio Architect runtime telemetry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _as_utc(value: datetime) -> datetime:
    """Return one timezone-aware datetime normalized to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Resilience timestamps must include a timezone")
    return value.astimezone(timezone.utc)


def snapshot_age_seconds(
    generated_at: datetime | None,
    *,
    now: datetime,
) -> int | None:
    """Return locally derived age for the snapshot PA actually accepted."""
    if generated_at is None:
        return None
    current = _as_utc(now)
    generated = _as_utc(generated_at)
    return max(0, int((current - generated).total_seconds()))


def snapshot_expires_in_seconds(
    generated_at: datetime | None,
    *,
    maximum_age_seconds: int | None,
    now: datetime,
) -> int | None:
    """Return locally derived remaining informational retention time."""
    if maximum_age_seconds is None or maximum_age_seconds <= 0:
        return None
    age = snapshot_age_seconds(generated_at, now=now)
    if age is None:
        return None
    return max(0, maximum_age_seconds - age)


def refresh_overdue_is_evidenced(
    *,
    next_refresh_due_at: datetime | None,
    health_observed_at: datetime | None,
    refresh_in_progress: bool | None,
    grace_seconds: int | None,
    now: datetime,
) -> bool | None:
    """Return overdue only when a health observation proves a missed deadline.

    A locally ticking entity must not turn an old ``next_refresh_due_at`` value
    into a failure after that health sample has itself become stale. The Gateway
    has to have been observed at or after the deadline plus grace while still
    advertising the missed deadline.
    """
    if (
        next_refresh_due_at is None
        or health_observed_at is None
        or grace_seconds is None
    ):
        return None
    if refresh_in_progress:
        return False

    current = _as_utc(now)
    due = _as_utc(next_refresh_due_at)
    observed = _as_utc(health_observed_at)
    threshold = due + timedelta(seconds=max(0, grace_seconds))
    if current <= threshold:
        return False
    if observed < threshold:
        return False
    return True


def snapshot_within_retention(
    generated_at: datetime | None,
    *,
    maximum_age_seconds: int,
    now: datetime,
) -> bool:
    """Return whether a trusted snapshot may still be shown informationally."""
    if generated_at is None or maximum_age_seconds <= 0:
        return False
    age = snapshot_age_seconds(generated_at, now=now)
    return age is not None and age <= maximum_age_seconds
