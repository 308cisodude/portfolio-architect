# Upgrade to Portfolio Architect 1.18.1

Version 1.18.1 is a stable observability and dashboard-language maintenance release.
It is built from the v1.18.0 stable baseline and does not include the experimental
v1.19.0 brokerage-diagnostic branch.

## 1. Update through HACS

Install version `1.18.1` and wait for **Pending restart**. Before restarting, verify
that `manifest.json`, `const.py`, and `engine/__init__.py` all report `1.18.1` and
that only one Portfolio Architect `manifest.json` exists. Then run a Home Assistant
configuration check and restart.

## 2. Replace the dashboard YAML

Replace the complete raw dashboard configuration with
`portfolio-architect-v1.18.1-bilingual-dashboard.yaml` if you want the wording polish:

- **Complete portfolio** becomes **Total portfolio value**;
- **Current plan drift** becomes **Current portfolio allocation**;
- German headings become **Gesamtportfoliowert** and **Aktuelle Portfolioallokation**.

No additional restart is required after saving the dashboard.

## 3. Gateway App

Update the Gateway App in place to `1.18.1` to expose provider-supplied position
quantities when Comdirect returns them. Existing authentication, session state,
selected account, refresh schedule, and cached snapshot remain in App-private data.
Do not uninstall the App and do not remove its data.

The REST portfolio remains schema 1. `quantity` is an optional position field: older
Gateway snapshots remain valid, and quantity entities are unavailable when a source
does not provide a quantity.

## 4. Verify

Confirm:

- `sensor.portfolio_architect_version` reports `1.18.1`;
- existing entities retain their IDs;
- every holding has a new `<holding>_holding_quantity` entity;
- the quantity entity is available for sources that supply a quantity and unavailable
  rather than fabricated when they do not;
- portfolio value, allocation, recommendations, investment reserve, Gateway health,
  and Plan Delta remain unchanged except when live source data changes.

## Rollback

Restore v1.18.0 through HACS or the previous manual drop-in and restore the previous
dashboard if desired. Gateway App 1.18.0 remains compatible with the established
portfolio behavior; the new quantity entities will become unavailable after rollback.
