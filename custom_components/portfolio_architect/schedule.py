"""Pure calendar calculations for recurring portfolio review cycles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

FREQUENCY_WEEKLY = "weekly"
FREQUENCY_MONTHLY = "monthly"
FREQUENCY_QUARTERLY = "quarterly"
FREQUENCY_YEARLY = "yearly"
FREQUENCIES = {
    FREQUENCY_WEEKLY,
    FREQUENCY_MONTHLY,
    FREQUENCY_QUARTERLY,
    FREQUENCY_YEARLY,
}


@dataclass(frozen=True, slots=True)
class PlanScheduleConfig:
    """Validated recurring investment-plan schedule."""

    frequency: str
    execution_days: tuple[int, ...]
    execution_month: int | None = None
    execution_month_offset: int | None = None

    @property
    def executions_per_period(self) -> int:
        """Return the number of planned executions in one configured period."""
        return len(self.execution_days)


@dataclass(frozen=True, slots=True)
class PlanReviewSchedule:
    """Dates derived from one successful portfolio evaluation."""

    evaluated_on: date
    planned_execution_on: date
    next_review_on: date
    review_for_execution_on: date
    frequency: str
    executions_per_period: int

    def is_due(self, current_date: date) -> bool:
        """Return whether the next review date has been reached."""
        return current_date >= self.next_review_on


def validate_schedule_config(
    frequency: object,
    execution_days: Iterable[object],
    *,
    execution_month: object | None = None,
    execution_month_offset: object | None = None,
) -> PlanScheduleConfig:
    """Validate and normalise one recurring schedule configuration."""
    if not isinstance(frequency, str) or frequency not in FREQUENCIES:
        raise ValueError("frequency is invalid")
    if isinstance(execution_days, (str, bytes)):
        raise ValueError("execution_days must be a collection of integers")

    parsed_days: set[int] = set()
    for raw in execution_days:
        if isinstance(raw, bool):
            raise ValueError("execution_days must contain integers")
        try:
            value = int(raw)
        except (TypeError, ValueError) as err:
            raise ValueError("execution_days must contain integers") from err
        parsed_days.add(value)
    if not parsed_days:
        raise ValueError("at least one execution day is required")

    if frequency == FREQUENCY_WEEKLY:
        if min(parsed_days) < 1 or max(parsed_days) > 7:
            raise ValueError("weekly execution days must be between 1 and 7")
        return PlanScheduleConfig(frequency, tuple(sorted(parsed_days)))

    if min(parsed_days) < 1 or max(parsed_days) > 28:
        raise ValueError("calendar execution days must be between 1 and 28")

    month: int | None = None
    offset: int | None = None
    if frequency == FREQUENCY_QUARTERLY:
        if isinstance(execution_month_offset, bool):
            raise ValueError("quarterly month offset must be between 1 and 3")
        try:
            offset = int(execution_month_offset)
        except (TypeError, ValueError) as err:
            raise ValueError("quarterly month offset must be between 1 and 3") from err
        if not 1 <= offset <= 3:
            raise ValueError("quarterly month offset must be between 1 and 3")
    elif frequency == FREQUENCY_YEARLY:
        if isinstance(execution_month, bool):
            raise ValueError("yearly execution month must be between 1 and 12")
        try:
            month = int(execution_month)
        except (TypeError, ValueError) as err:
            raise ValueError("yearly execution month must be between 1 and 12") from err
        if not 1 <= month <= 12:
            raise ValueError("yearly execution month must be between 1 and 12")

    return PlanScheduleConfig(
        frequency=frequency,
        execution_days=tuple(sorted(parsed_days)),
        execution_month=month,
        execution_month_offset=offset,
    )


def calculate_plan_review_schedule(
    evaluated_on: date,
    schedule_or_execution_day: PlanScheduleConfig | int,
    review_lead_days: int,
) -> PlanReviewSchedule:
    """Calculate the execution covered by an evaluation and the next review.

    An integer second argument is retained as a backwards-compatible shorthand
    for one monthly execution day.
    """
    if isinstance(review_lead_days, bool) or not 1 <= review_lead_days <= 7:
        raise ValueError("review_lead_days must be between 1 and 7")

    if isinstance(schedule_or_execution_day, PlanScheduleConfig):
        config = schedule_or_execution_day
    else:
        config = validate_schedule_config(
            FREQUENCY_MONTHLY,
            [schedule_or_execution_day],
        )

    planned_execution = _next_occurrence(evaluated_on, config)
    review_for_execution = _first_execution_in_next_period(planned_execution, config)
    next_review = review_for_execution - timedelta(days=review_lead_days)

    # A very long lead time can theoretically place the review before the
    # evaluation (most relevant for weekly schedules). Advance period by period
    # until the next review genuinely follows the evaluation.
    guard = 0
    while next_review <= evaluated_on and guard < 400:
        review_for_execution = _first_execution_in_next_period(
            review_for_execution, config
        )
        next_review = review_for_execution - timedelta(days=review_lead_days)
        guard += 1
    if next_review <= evaluated_on:
        raise ValueError("could not derive a future review date")

    return PlanReviewSchedule(
        evaluated_on=evaluated_on,
        planned_execution_on=planned_execution,
        next_review_on=next_review,
        review_for_execution_on=review_for_execution,
        frequency=config.frequency,
        executions_per_period=config.executions_per_period,
    )


def _first_execution_in_next_period(
    current_execution: date, config: PlanScheduleConfig
) -> date:
    """Return the first configured execution in the following plan period."""
    first_day = config.execution_days[0]
    if config.frequency == FREQUENCY_WEEKLY:
        next_week_monday = current_execution + timedelta(
            days=8 - current_execution.isoweekday()
        )
        return next_week_monday + timedelta(days=first_day - 1)

    if config.frequency == FREQUENCY_MONTHLY:
        year, month = _shift_month(current_execution.year, current_execution.month, 1)
        return date(year, month, first_day)

    if config.frequency == FREQUENCY_QUARTERLY:
        year, month = _shift_month(current_execution.year, current_execution.month, 3)
        # The current execution month already matches the selected month within
        # its quarter, so adding three months preserves the offset.
        return date(year, month, first_day)

    if config.frequency == FREQUENCY_YEARLY:
        return date(current_execution.year + 1, config.execution_month, first_day)

    raise ValueError("unsupported plan frequency")


def _next_occurrence(after: date, config: PlanScheduleConfig) -> date:
    """Return the first configured occurrence strictly after ``after``."""
    if config.frequency == FREQUENCY_WEEKLY:
        for delta in range(1, 15):
            candidate = after + timedelta(days=delta)
            if candidate.isoweekday() in config.execution_days:
                return candidate
        raise ValueError("could not derive weekly execution")

    year = after.year
    month = after.month
    for month_delta in range(0, 241):
        candidate_year, candidate_month = _shift_month(year, month, month_delta)
        if not _month_matches(candidate_year, candidate_month, config):
            continue
        for day in config.execution_days:
            candidate = date(candidate_year, candidate_month, day)
            if candidate > after:
                return candidate
    raise ValueError("could not derive calendar execution")


def _month_matches(year: int, month: int, config: PlanScheduleConfig) -> bool:
    del year
    if config.frequency == FREQUENCY_MONTHLY:
        return True
    if config.frequency == FREQUENCY_QUARTERLY:
        return ((month - 1) % 3) + 1 == config.execution_month_offset
    if config.frequency == FREQUENCY_YEARLY:
        return month == config.execution_month
    return False


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1
