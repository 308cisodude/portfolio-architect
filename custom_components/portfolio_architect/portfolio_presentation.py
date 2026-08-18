"""Bounded machine-readable portfolio presentation contract.

The presentation model describes portfolio *structure* and stable identity. Live
monetary values and actionable purchase guidance remain on their dedicated native
entities so this index does not become a large recorder payload on every refresh.
"""

from __future__ import annotations

from typing import Any

from .model import PortfolioData

PRESENTATION_SCHEMA_VERSION = 1


def build_portfolio_presentation(
    data: PortfolioData,
    *,
    plan_actionable: bool,
    actionability_reason: str,
) -> dict[str, Any]:
    """Return the generic target/outside-scope structural presentation model."""
    targets: list[dict[str, Any]] = []
    for order, (key, position) in enumerate(data.positions.items()):
        if not position.is_target_position:
            continue
        if key != position.target_id:
            raise ValueError("target presentation identity is inconsistent")
        targets.append(
            {
                "target_id": position.target_id,
                "entity_key": position.target_id,
                "order": order,
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
    for holding in data.holdings.values():
        if holding.in_current_plan:
            current_plan_holdings.append(
                {
                    "position_id": holding.position_id,
                    "target_id": holding.plan_target_id,
                    "entity_key": holding.position_id,
                    "source_ids": list(holding.source_ids),
                }
            )
            continue
        outside_holdings.append(
            {
                "position_id": holding.position_id,
                "entity_key": holding.position_id,
                "name": holding.name,
                "isin": holding.isin,
                "wkn": holding.wkn,
                "instrument_type": holding.instrument_type,
                "source_type": holding.source_type,
                "source_ids": list(holding.source_ids),
            }
        )

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
