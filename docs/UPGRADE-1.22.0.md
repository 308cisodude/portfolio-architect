# Upgrade to Portfolio Architect 1.22.0

Version 1.22.0 hardens the publication pipeline. Portfolio calculation,
recommendation, actionability, cash authorization, Gateway banking behavior, and
Home Assistant entity semantics are unchanged from 1.21.0.

## What changes

- The release pipeline now runs a Portfolio Architect-specific privacy gate over
  the repository and every built release artifact; protected GitHub validation also
  applies those checks to complete reachable Git history.
- GitHub validation and release workflows run Gitleaks from an immutable image over
  the tracked source tree, complete Git patch history, and safely staged release
  artifact contents.
- Raw broker documents, unapproved CSV exports, unexpected screenshots/images,
  backup/database/key-container formats, valid IBANs, and non-synthetic provider
  identity literals fail the publication gate.
- The three existing public CSVs remain explicitly approved as generic/synthetic
  fixtures.
- Maintainers can optionally provide a private literal list from outside the
  repository for exact local matching without publishing those values.
- Dashboard documentation now states explicitly that an imported/copied reference
  dashboard is user-owned and is not replaced by HACS or the integration.
- `docs/ROADMAP.md` records the next provider-separated Gateway milestone followed
  by Trade Republic statement import.

## Upgrade procedure

1. Update **Portfolio Architect Gateway** to 1.22.0 through **Settings → Apps**.
2. Update **Portfolio Architect** to 1.22.0 through HACS.
3. Restart Home Assistant once after the HACS update.
4. Confirm `Version` reports 1.22.0 and normal live health returns.

No reauthentication, entity migration, configuration migration, source change, or
dashboard replacement is required solely by this release.

The reference dashboard is unchanged functionally from 1.21.0. If you already
imported the v1.21.0 reference dashboard, there is no visual migration to perform.
HACS updates the custom integration package only; it never overwrites a dashboard
that you copied into Home Assistant.

## Compatibility

- payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 5 (unchanged)
- existing entity IDs / unique IDs: unchanged
- v1.21 actionability semantics: unchanged
- authorized-cash and v1.20/v1.20.1 LKG semantics: unchanged
- Gateway banking runtime: unchanged apart from package/user-agent version alignment
- no trading, order, transfer, payment, or transaction-history capability
