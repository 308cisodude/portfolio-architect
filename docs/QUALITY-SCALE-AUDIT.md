# Home Assistant quality-scale audit

Portfolio Architect is a community custom integration and does not claim an
official Home Assistant quality tier. The integration nevertheless tracks its
alignment with the current quality-scale rules in
`custom_components/portfolio_architect/quality_scale.yaml`.

The audit is intentionally conservative:

- `done` means the repository contains an implementation and regression evidence;
- `exempt` includes a bounded reason explaining why the rule does not apply;
- an empty rule remains open and is not treated as completed.

The publication workflow runs hassfest so changes in Home Assistant metadata and
quality requirements become visible before release. An official quality tier
would require Home Assistant project review and is outside the claims of this
community release.
