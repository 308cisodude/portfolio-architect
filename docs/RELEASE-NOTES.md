# Portfolio Architect 1.44.0

Portfolio Architect v1.44.0 is a **Configure UX consistency release**. It audits every menu below the native Configure entry point and makes every selected-object editor identify the immutable object being edited above its editable fields.

The release is presentation/configuration UX only. Planner economics, route evidence semantics, provider acquisition, wire schemas, dashboard presentation, and Portfolio Architect's advisory-only boundary are unchanged.

## Self-identifying edit forms

Three native Configure flows edit an existing selected object and now expose explicit non-editable context before the editable fields:

- **Edit execution provider** shows the provider display name plus immutable provider ID.
- **Edit savings-plan route** shows the provider display name, immutable provider ID, and ISIN.
- **Edit funding transfer** shows the exact directed source-provider → destination-provider relationship, including provider IDs.

The existing plan-instrument editor was already compliant because it shows instrument name, ISIN, WKN, and target ID. Global settings forms remain identified by their own form titles because they do not edit a separately selected object.

The context is rendered through the normal Home Assistant options-flow description area; it is not an editable selector and it does not alter the identity fields sent to the broker editor.

## Configure menu audit

All seven native Configure menu surfaces are now covered by one regression contract:

- root Configure menu;
- portfolio sources;
- additional REST Gateways;
- execution providers & funding;
- execution providers;
- savings-plan routes; and
- funding topology.

Every emitted menu target must have a non-empty English and German label and a translated target-step title. Translation-key ordering is kept aligned with menu emission order, including **Edit funding transfer / Finanzierungsbeziehung bearbeiten**.

Because Home Assistant caches backend translations for the lifetime of the Core process, install v1.44.0 through the normal HACS workflow and restart Home Assistant before evaluating the updated Configure text.

## Compatibility and unchanged behavior

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- presentation schema 2 remains unchanged.
- broker schemas 1/2/3 remain unchanged.
- v1.43 route-level evidence/fallback/freshness semantics are unchanged.
- route ranking economics, v1.41.1 local-cash tie-break, provider-scoped cash, and funding-transfer cost ordering are unchanged.
- The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, and v1.44.0 does not change any configured freshness threshold.
- v1.42 normalized execution-path sensor and bilingual native dashboard renderer are unchanged; no dashboard migration is required.
- The v1.39.0 colourful paired allocation Tile view was not included in v1.38.1; the current native allocation and drift presentation remains unchanged.
- Trade Republic `DEPOTAUSZUG`/`KONTOAUSZUG` acquisition is unchanged; Trade Republic PDF parsing remains provider-isolated and does not move PDF parsing into Portfolio Architect.
- Comdirect OAuth/session/cash behavior is unchanged. DKB live Gateway acquisition remains a later gated milestone; the anonymous capability probe remains fail-closed.
- Verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning, provider isolation, and fail-closed provider behavior remain unchanged.
- The historical v1.19.0-rc2 state remains historical and is not promoted by this release.
- No trading, order, transfer, payment, or transaction-history capability is introduced; sell and withdrawal capability likewise remain absent.

## Upgrade

Update the integration and all three Gateway Apps in place to v1.44.0, then restart Home Assistant so the updated options-flow translations are loaded. Existing broker configuration requires no migration. No dashboard YAML replacement is required.

For live acceptance, deliberately keep at least one Trade Republic savings-plan route on v1.43 provider-evidence fallback. Verify an explicit route and a legacy/fallback route both show the correct immutable edit context, then save the legacy route if desired to prove the fallback-to-explicit migration path remains intact. Verify the existing Comdirect → Trade Republic funding editor shows the directed edge above the form and that the menu row label is visible.
