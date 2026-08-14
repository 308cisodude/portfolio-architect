# Upgrade to Portfolio Architect 1.26.0

Version 1.26.0 adds simultaneous consumption of multiple provider-isolated local
Gateway REST snapshots. Existing single-Gateway installations remain compatible and
require no source migration.

## Existing Comdirect installation

1. Update **Portfolio Architect Gateway — Comdirect** to 1.26.0 in place.
2. Update Portfolio Architect to 1.26.0 through HACS.
3. Restart Home Assistant once after the HACS update.
4. Confirm normal live health, `health_schema_version: 6`, and
   `provider_id: comdirect`.

No Comdirect reauthentication, account reselection, API-token change, cash-policy
migration, configuration-entry migration or entity migration is required solely
because of this upgrade.

## Trade Republic App

Update **Portfolio Architect Gateway — Trade Republic** to 1.26.0 in place. The
validated v1.25 statement snapshot and bearer token remain App-private state. The
App now starts automatically so a configured REST consumer can recover after Home
Assistant restarts without a manual App start.

The supported German text-PDF `DEPOTAUSZUG` import boundary is unchanged. The
original PDF is still parsed in memory and never persisted.

## Add Trade Republic as an additional Gateway

Keep the existing Comdirect Gateway as the primary source. Open:

**Settings → Devices & services → Portfolio Architect → Configure → Portfolio sources → Additional REST Gateways → Add REST Gateway**

Enter the Trade Republic App's internal Home Assistant App-network portfolio
endpoint on port 8787, ending in `/api/v1/portfolio`, and the bearer token shown only
on the Trade Republic App's admin-only Ingress page.

Portfolio Architect validates the Gateway's bearer authentication, health schema 6,
`provider_id`, live snapshot and integrity metadata before storing the additional
source. Do not expose port 8787 to the LAN merely to make this connection; the
intended path is the private Home Assistant App network.

Removing an additional Gateway from Portfolio Architect does not uninstall or alter
the Gateway App or its private snapshot.

## Expected aggregate

With the current Comdirect REST source, the established DKB CSV supplement and the
accepted Trade Republic statement configured together, the reference data should
report three sources and three distinct providers. The Trade Republic Robotics
holding should participate in the same provider-neutral aggregation and target
coverage as every other holding.

The **Source provider** reference-dashboard tile now uses the additive
`provider_summary` / `provider_summary_de` attributes, for example
`Multi-source portfolio · 3 providers`. Existing copied dashboards are user-owned;
HACS does not replace them automatically.

## Failure semantics

Configured additional Gateways are part of one atomic aggregate. If Trade Republic
is temporarily unavailable, Portfolio Architect must not silently remove its
holdings and recompute a smaller live portfolio. A matching previously validated
complete aggregate is retained as Home Assistant last-known-good data, runtime
health becomes degraded/last-known-good and new investment actions are disabled.
Normal live operation resumes automatically when every configured REST Gateway is
healthy again.

Changing the configured source set invalidates the previous source-set LKG
fingerprint by design.

## Compatibility

- payload schema 8 unchanged
- REST portfolio schema 1 unchanged
- Gateway health schema 6 unchanged
- existing entity IDs / unique IDs unchanged
- existing primary REST configuration unchanged
- authorized-cash semantics unchanged
- no trading/order/transfer/payment/transaction-history capability
