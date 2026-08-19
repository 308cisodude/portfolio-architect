# Upgrade to Portfolio Architect 1.35.2

Version 1.35.2 is an execution-policy configuration and provider-owned cash-authorization refinement
prepared on top of the published/live-accepted v1.35.1 baseline. It does not require a portfolio,
dashboard, source, TLS, bearer-token, or broker-schema migration.

## Recommended upgrade order

1. Update **Portfolio Architect** through HACS to 1.35.2 and restart Home Assistant once.
2. Confirm existing Comdirect and Trade Republic sources remain healthy on verified HTTPS, DKB
   remains at its established experimental state, and the current portfolio/recommendation is unchanged.
3. Update **Portfolio Architect Gateway — Comdirect** to 1.35.2 in place. Preserve `/data/gateway`,
   OAuth/session state, selected investment account, bearer token, private CA and cash policy.
4. Align the Trade Republic and DKB Apps to 1.35.2 in place. Their acquisition/capability behavior is
   unchanged apart from common package/schema compatibility.
5. Open **Portfolio Architect → Configure → Execution providers & funding**. Existing schema-2/3
   `broker.yaml` should be represented without requiring manual editing. Do not change tariff evidence
   merely to test the editor.
6. If desired, test **Keep cash reserve** in the Comdirect App Web UI with a deliberately chosen retained
   amount. Verify authorized cash equals `max(eligible - retained, 0)`. Restore the prior policy afterward
   if the retained-cash policy is not intended for normal operation.

## Native broker editor

The editor operates on the existing file-backed `broker.yaml` and validates the full document before
an atomic write. It supports schemas 2 and 3. Schema 1 remains valid at runtime but is not silently
converted; deliberately migrate it to schema 2 first if native provider editing is wanted.

The UI describes `priority` as **Tie-break preference**. Cost still wins first; funding settlement time
is considered next for otherwise equal funded routes; preference resolves only a remaining tie.
Omitting preference is neutral. The YAML `priority` key remains supported for advanced/backward-compatible
configuration.

The `promotional` savings-plan flag is descriptive only and never changes economic ranking.

## Retained-cash compatibility

Existing `all_available` and `capped` policy state loads and continues to save as private schema 1.
Only the new `retain` policy uses private policy schema 2 and publishes an additive `retain_eur` field in
the existing REST portfolio schema-1 `investment_cash` object. Keep the integration and Comdirect App
aligned on 1.35.2 before enabling this mode; a pre-1.35.2 strict client will reject that unknown field.

No account identifier, IBAN, account holder, transaction history or credential is added to the public
snapshot or diagnostics.

## No dashboard migration

The v1.35.1 reference dashboard remains compatible. Version 1.35.2 does not implement native dynamic
portfolio presentation; that remains the next separate presentation milestone.

## Rollback

If rollback is required, restore v1.35.1 packages in place and keep the existing broker file. Before
running a pre-1.35.2 integration against Comdirect, change the Gateway cash authorization back to
**All eligible cash** or **Cap authorized cash** so no `retain_eur` field is emitted. Existing schema-2/3
broker configuration remains compatible with v1.35.1.
