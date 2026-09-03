"""Self-contained calculation engine for Portfolio Architect."""

from __future__ import annotations

__version__ = "1.62.4"

from .calculator import (
    calculate_portfolio_payload_from_positions,
)

__all__ = [
    "__version__",
    "calculate_portfolio_payload_from_positions",
]
