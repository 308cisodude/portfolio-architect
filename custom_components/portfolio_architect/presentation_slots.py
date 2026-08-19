"""Deterministic native-dashboard presentation slot ordering.

The stable instrument identities remain the target IDs and holding position IDs in
``PortfolioData``. Presentation slots are deliberately ephemeral UI projections:
they provide a bounded set of predictable native Home Assistant entity IDs that a
static reference dashboard can filter dynamically without custom frontend code.

Slot ordering is derived from the same validated current-state collections consumed
by :mod:`portfolio_presentation`. Slots must never be used as portfolio identity,
history/tombstone storage, or an automation contract.
"""

from __future__ import annotations

from .model import (
    MAX_HOLDINGS,
    MAX_POLICY_FINDINGS,
    MAX_POSITIONS,
    HoldingData,
    PolicyFindingData,
    PortfolioData,
    PositionData,
)

MAX_TARGET_PRESENTATION_SLOTS = MAX_POSITIONS
MAX_OUTSIDE_PRESENTATION_SLOTS = MAX_HOLDINGS
MAX_POLICY_PRESENTATION_SLOTS = MAX_POLICY_FINDINGS


def ordered_target_positions(data: PortfolioData) -> tuple[PositionData, ...]:
    """Return current configured targets in their authoritative presentation order."""
    return tuple(
        position for position in data.positions.values() if position.is_target_position
    )


def ordered_current_plan_holdings(data: PortfolioData) -> tuple[HoldingData, ...]:
    """Return current-plan holdings in accepted source order."""
    return tuple(holding for holding in data.holdings.values() if holding.in_current_plan)


def ordered_outside_holdings(data: PortfolioData) -> tuple[HoldingData, ...]:
    """Return complete current outside-scope holding inventory in accepted source order."""
    return tuple(holding for holding in data.holdings.values() if not holding.in_current_plan)


def ordered_non_pass_findings(data: PortfolioData) -> tuple[PolicyFindingData, ...]:
    """Return active policy findings in their validated stable mapping order."""
    return tuple(data.policy.non_pass_findings)


def target_position_for_slot(data: PortfolioData, slot: int) -> PositionData | None:
    """Resolve a one-based target presentation slot against current state."""
    if not 1 <= slot <= MAX_TARGET_PRESENTATION_SLOTS:
        raise ValueError("target presentation slot is outside the bounded range")
    rows = ordered_target_positions(data)
    return rows[slot - 1] if slot <= len(rows) else None


def outside_holding_for_slot(data: PortfolioData, slot: int) -> HoldingData | None:
    """Resolve a one-based outside-scope presentation slot against current state."""
    if not 1 <= slot <= MAX_OUTSIDE_PRESENTATION_SLOTS:
        raise ValueError("outside-scope presentation slot is outside the bounded range")
    rows = ordered_outside_holdings(data)
    return rows[slot - 1] if slot <= len(rows) else None


def policy_finding_for_slot(data: PortfolioData, slot: int) -> PolicyFindingData | None:
    """Resolve a one-based active policy-finding presentation slot against current state."""
    if not 1 <= slot <= MAX_POLICY_PRESENTATION_SLOTS:
        raise ValueError("policy presentation slot is outside the bounded range")
    rows = ordered_non_pass_findings(data)
    return rows[slot - 1] if slot <= len(rows) else None
