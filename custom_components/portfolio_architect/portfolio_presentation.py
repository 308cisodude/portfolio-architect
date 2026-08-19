"""Bounded machine-readable portfolio presentation contract.

The presentation model describes portfolio *structure* and stable identity. Live
monetary values and actionable purchase guidance remain on their dedicated native
entities so this index does not become a large recorder payload on every refresh.
"""

from __future__ import annotations

from typing import Any

from .model import PortfolioData
from .presentation_slots import (
    ordered_current_plan_holdings,
    ordered_non_pass_findings,
    ordered_outside_holdings,
    ordered_target_positions,
)

PRESENTATION_SCHEMA_VERSION = 2


def build_portfolio_presentation(
    data: PortfolioData,
    *,
    plan_actionable: bool,
    actionability_reason: str,
) -> dict[str, Any]:
    """Return the generic target/outside-scope structural presentation model."""
    targets: list[dict[str, Any]] = []
    for slot, position in enumerate(ordered_target_positions(data), start=1):
        if data.positions.get(position.target_id) is not position:
            raise ValueError("target presentation identity is inconsistent")
        targets.append(
            {
                "target_id": position.target_id,
                "entity_key": position.target_id,
                "order": slot - 1,
                "presentation_slot": slot,
                "slot_key": f"target_{slot:02d}",
                "name": position.name,
                "isin": position.isin,
                "wkn": position.wkn,
                "target_pct": position.target_pct,
                "held": position.is_held,
                "allocation_status": position.allocation_status,
                "buy_enabled": position.buy_enabled,
                "source_ids": list(position.source_ids),
            }
        )

    current_plan_holdings: list[dict[str, Any]] = []
    outside_holdings: list[dict[str, Any]] = []
    for holding in ordered_current_plan_holdings(data):
        current_plan_holdings.append(
            {
                "position_id": holding.position_id,
                "target_id": holding.plan_target_id,
                "entity_key": holding.position_id,
                "source_ids": list(holding.source_ids),
            }
        )

    for slot, holding in enumerate(ordered_outside_holdings(data), start=1):
        outside_holdings.append(
            {
                "position_id": holding.position_id,
                "entity_key": holding.position_id,
                "presentation_slot": slot,
                "slot_key": f"outside_{slot:03d}",
                "name": holding.name,
                "isin": holding.isin,
                "wkn": holding.wkn,
                "instrument_type": holding.instrument_type,
                "source_type": holding.source_type,
                "source_ids": list(holding.source_ids),
            }
        )

    active_policy_findings = [
        {
            "presentation_slot": slot,
            "slot_key": f"policy_{slot:03d}",
            "finding_key": finding.key,
            "target_id": finding.fund_id,
            "rule": finding.rule,
            "state": finding.entity_state,
        }
        for slot, finding in enumerate(ordered_non_pass_findings(data), start=1)
    ]

    policy = data.policy
    return {
        "presentation_schema_version": PRESENTATION_SCHEMA_VERSION,
        "target_count": len(targets),
        "target_ids": [item["target_id"] for item in targets],
        "targets": targets,
        "current_plan_holding_count": len(current_plan_holdings),
        "current_plan_holding_ids": [
            item["position_id"] for item in current_plan_holdings
        ],
        "current_plan_holdings": current_plan_holdings,
        "outside_scope_count": len(outside_holdings),
        "outside_scope_position_ids": [
            item["position_id"] for item in outside_holdings
        ],
        "outside_scope_holdings": outside_holdings,
        "active_policy_finding_count": len(active_policy_findings),
        "active_policy_findings": active_policy_findings,
        "plan_actionable": plan_actionable,
        "plan_actionability_reason": actionability_reason,
        "policy": {
            "status": policy.status,
            "mandatory_controls_compliant": policy.mandatory_controls_compliant,
            "accepted_exceptions": policy.accepted_exceptions,
            "exception_reviews_required": policy.exception_reviews_required,
            "optimisation_opportunities": policy.opportunities,
        },
    }
