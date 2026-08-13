"""Pure execution-timing and actionability semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

PLAN_ACTIONABILITY_ACTIONABLE_NOW = "actionable_now"
PLAN_ACTIONABILITY_SCHEDULED = "scheduled"
PLAN_ACTIONABILITY_OVERDUE = "overdue_actionable"
PLAN_ACTIONABILITY_NOT_READY = "not_ready"
PLAN_ACTIONABILITY_NOT_ACTIONABLE = "not_actionable"

PLAN_ACTIONABILITY_STATES = (
    PLAN_ACTIONABILITY_ACTIONABLE_NOW,
    PLAN_ACTIONABILITY_SCHEDULED,
    PLAN_ACTIONABILITY_OVERDUE,
    PLAN_ACTIONABILITY_NOT_READY,
    PLAN_ACTIONABILITY_NOT_ACTIONABLE,
)

SCHEDULE_RELATION_NOT_CONFIGURED = "not_configured"
SCHEDULE_RELATION_UPCOMING = "upcoming"
SCHEDULE_RELATION_DUE_TODAY = "due_today"
SCHEDULE_RELATION_PAST = "past_scheduled_date"


@dataclass(frozen=True, slots=True)
class PlanActionabilitySemantics:
    """One bounded current-state interpretation of a scheduled recommendation."""

    state: str
    schedule_relation: str
    days_until_scheduled_execution: int | None


def derive_plan_actionability(
    *,
    source_actionable: bool,
    execution_state: str,
    planned_execution_on: date | None,
    current_date: date,
) -> PlanActionabilitySemantics:
    """Separate schedule timing from current recommendation actionability.

    The scheduled execution date is historical/planning context. It does not
    expire a recommendation by itself. Source trust/freshness and the execution
    state decide whether the recommendation can still be acted on.
    """
    if planned_execution_on is None:
        relation = SCHEDULE_RELATION_NOT_CONFIGURED
        days_until = None
    else:
        days_until = (planned_execution_on - current_date).days
        if days_until > 0:
            relation = SCHEDULE_RELATION_UPCOMING
        elif days_until == 0:
            relation = SCHEDULE_RELATION_DUE_TODAY
        else:
            relation = SCHEDULE_RELATION_PAST

    if not source_actionable:
        state = PLAN_ACTIONABILITY_NOT_ACTIONABLE
    elif execution_state != "ready":
        state = PLAN_ACTIONABILITY_NOT_READY
    elif days_until is None or days_until == 0:
        state = PLAN_ACTIONABILITY_ACTIONABLE_NOW
    elif days_until > 0:
        state = PLAN_ACTIONABILITY_SCHEDULED
    else:
        state = PLAN_ACTIONABILITY_OVERDUE

    return PlanActionabilitySemantics(
        state=state,
        schedule_relation=relation,
        days_until_scheduled_execution=days_until,
    )
