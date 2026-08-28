# Upgrade to Portfolio Architect 1.55.1

Version 1.55.1 is a narrow hotfix for the published v1.55.0 Comdirect App-identity migration. The first live v1.55.0 attempt failed safely before private state reached Comdirect NEW because the legacy exporter accepted only acquisition-state schema 1 while the normal production control plane can persist schema 2 after an explicit acquisition-method switch.

## Safe starting state

If the v1.55.0 attempt failed with a generic HTTP 400 while:

- the historical Comdirect App remained healthy/live;
- Comdirect NEW still showed **1 · Receive legacy Comdirect state**;
- Portfolio Architect remained on the historical endpoint;
- neither App showed staged/imported/frozen migration state;

then no rollback or cleanup is required. That is the exact expected starting state for this hotfix.

## Upgrade order

1. Update Portfolio Architect through HACS to **1.55.1** and restart Home Assistant once.
2. Update the historical **Portfolio Architect Gateway — Comdirect** App to **1.55.1** in place.
3. Update **Portfolio Architect Gateway — Comdirect NEW** to **1.55.1** in place. Preserve its App-private data; do not choose fresh setup.
4. Align DKB and Trade Republic to 1.55.1 for package-version hygiene. Align Generic Import only if intentionally installed.
   If Generic Import is not intentionally configured, do **not** install it or add its discovery card/source solely for this migration. Any isolated Generic Import smoke test must not alter the real production source set or broker configuration, and an App installed only for this standalone smoke test should be uninstalled after this standalone smoke test.
5. Confirm Portfolio Architect remains healthy and authoritative on the historical Comdirect endpoint before retrying migration.

Restarting Comdirect NEW creates a fresh ephemeral migration receiver identity and therefore a fresh one-time migration code. Use the code currently displayed by the 1.55.1 App; do not reuse a code copied from the earlier 1.55.0 process.

## Resume the migration

1. Open Comdirect NEW and copy its current one-time migration code.
2. Paste it into **App identity migration** in the historical Comdirect App and choose **Stage private state in provider-qualified App**.
3. The historical App first validates its local long-lived state, including either acquisition-state schema 1 or schema 2, then performs a read-only authenticated fingerprint-pinned status preflight against the exact successor before transmitting private state.
4. If staging fails, the historical App returns to its migration card with one bounded non-secret reason class. Do not freeze or uninstall either App; diagnose the displayed class first.
5. If staging succeeds, compare the bounded summaries on both sides: source hostname, private-CA SHA-256, canonical snapshot timestamp/SHA-256, acquisition mode and private-file count. No OAuth/session secret or account identifier should appear.
6. In Comdirect NEW, explicitly commit the staged long-lived state and allow the bounded Supervisor-option reconciliation to finish.
7. In the historical App, choose **Freeze legacy for cut-over**. Confirm Portfolio Architect remains healthy on the trusted cached historical endpoint.
8. In Comdirect NEW, confirm the legacy freeze, approve canonical runtime and restart Comdirect NEW.
9. Because the production mode is `live_api`, perform a fresh PhotoTAN bootstrap in Comdirect NEW. Do not copy or reuse the old OAuth session.
10. Wait for **Migrate Comdirect Gateway identity securely** in Home Assistant. Confirm only if old/new hostnames are the exact slug-successor pair and the private-CA SHA-256 is unchanged.
11. After PA accepts the migration, require exactly one canonical `comdirect` source, verified HTTPS, `acquisition_mode: live_api`, `fallback_policy: none`, a fresh real snapshot, and no LKG/integrity/attention state.
12. Only then uninstall the historical Comdirect App.

## Recovery

Before PA endpoint cut-over, the historical App remains the recovery authority. If a problem occurs after it has been frozen, use its explicit **Cancel cut-over; resume after legacy App restart** action and restart the legacy App. Do not remove the legacy App until PA is healthy on the provider-qualified endpoint.

No dashboard, broker, freshness, DKB, Trade Republic, or Generic Import data migration is required.
