"""Canonical provider identities published by Portfolio Architect Gateway Apps.

These values deliberately live outside the CSV importer provider namespace.
For example, DKB Gateway discovery uses ``dkb`` while the legacy DKB CSV
source adapter uses ``dkb_csv``. Keeping the identifiers distinct prevents a
Gateway discovery flow from accidentally comparing unlike provider namespaces.
"""

from __future__ import annotations

from typing import Final

GATEWAY_PROVIDER_COMDIRECT: Final = "comdirect"
GATEWAY_PROVIDER_DKB: Final = "dkb"


def gateway_provider_conflicts_with_dkb_csv(
    provider_id: str | None, raw_dkb_sources: object
) -> bool:
    """Return whether a Gateway provider duplicates configured DKB CSV scope."""
    return (
        provider_id == GATEWAY_PROVIDER_DKB
        and isinstance(raw_dkb_sources, list)
        and bool(raw_dkb_sources)
    )
