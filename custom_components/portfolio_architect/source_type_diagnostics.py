"""Interpret bounded cross-source instrument type evidence for HA diagnostics."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def describe_instrument_type_findings(
    findings: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Separate unspecified types from disagreements between known types.

    Gateway parsers use ``other`` when a source does not establish a type. An
    older cached calculation can contain the same raw findings, so classify
    them at presentation time without requiring another source acquisition.
    """
    classified: list[dict[str, Any]] = []
    unspecified = 0
    disagreement = 0
    for finding in findings:
        observed = finding.get("observed", ())
        types = (
            {value.casefold() for value in observed if isinstance(value, str)}
            if isinstance(observed, (list, tuple))
            else set()
        )
        has_unspecified = "other" in types
        has_disagreement = len(types - {"other"}) > 1
        unspecified += has_unspecified
        disagreement += has_disagreement
        classification = (
            "known_type_disagreement_with_unspecified"
            if has_disagreement and has_unspecified
            else "known_type_disagreement"
            if has_disagreement
            else "type_unspecified"
            if has_unspecified
            else "type_difference"
        )
        classified.append({**finding, "classification": classification})

    def summary(*, german: bool) -> str:
        parts: list[str] = []
        if unspecified:
            if german:
                parts.append(f"{unspecified} unbekannte Typangabe{'n' if unspecified != 1 else ''}")
            else:
                parts.append(f"{unspecified} unspecified type{'s' if unspecified != 1 else ''}")
        if disagreement:
            if german:
                parts.append(f"{disagreement} Typkonflikt{'e' if disagreement != 1 else ''}")
            else:
                parts.append(f"{disagreement} known type conflict{'s' if disagreement != 1 else ''}")
        return " · ".join(parts) if parts else str(len(classified))

    return {
        "findings": classified,
        "unspecified_type_count": unspecified,
        "known_type_conflict_count": disagreement,
        "finding_summary": summary(german=False),
        "finding_summary_de": summary(german=True),
    }
