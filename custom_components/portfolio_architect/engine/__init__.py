"""Self-contained calculation engine for Portfolio Architect."""

from __future__ import annotations

__version__ = "1.41.1"

from .calculator import (
    calculate_portfolio_payload,
    calculate_portfolio_payload_from_positions,
)

__all__ = [
    "__version__",
    "calculate_portfolio_payload",
    "calculate_portfolio_payload_from_positions",
]
