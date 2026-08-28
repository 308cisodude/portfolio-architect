# Upgrade to Portfolio Architect 1.55.0

Version 1.55.0 is a deliberately staged App-identity migration for Comdirect. It introduces the provider-qualified Home Assistant App slug `portfolio_architect_gateway_comdirect` while keeping the historical `portfolio_architect_gateway` App available as the migration source. The new App is visibly named **Portfolio Architect Gateway — Comdirect NEW** during coexistence so the two instances cannot be confused.

The migration preserves the existing Gateway bearer token, private CA/key, client credentials, selected investment-account/cash-policy state, acquisition mode, staged static CSV evidence and canonical portfolio snapshot. It deliberately does **not** transfer `comdirect-session.json`; a migrated Live API installation must establish a fresh PhotoTAN session before the new endpoint can become discoverable.

## Security model

- There is no generic destination URL. The historical App derives exactly one successor hostname from its own Supervisor identity: `*-portfolio-architect-gateway` → `*-portfolio-architect-gateway-comdirect`.
- Transfer uses an ephemeral self-signed TLS receiver in **Comdirect NEW**. The one-time migration code carries the receiver certificate SHA-256 plus a one-time bearer secret; the historical App verifies the exact peer leaf fingerprint before sending anything.
- Only an explicit allowlist of long-lived App-private files is transferred. Each file is bounded and SHA-256 verified; symlinks, unknown files, oversized payloads and a pending acquisition switch fail closed.
- The Comdirect OAuth/session file is excluded and deleted on the target before cut-over.
- The migrated private CA must remain byte-identical. The new App renews only the server leaf for its new Supervisor hostname. Portfolio Architect refuses cut-over if the discovered CA fingerprint differs from the already trusted primary Comdirect CA.
- The historical App can be explicitly frozen for cut-over: provider refresh and OAuth/session maintenance stop while its already trusted cached HTTPS snapshot remains served. A separate explicit resume action cancels a frozen cut-over on the next restart.
- The new App does not publish Supervisor discovery while it is merely installed, staged, or imported. Canonical runtime must be explicitly approved, and discovery is delayed until Gateway health schema 8 reports a healthy live Comdirect snapshot.
- Portfolio Architect asks for explicit confirmation of the exact historical→provider-qualified hostname change. It reuses the existing bearer token, validates provider identity, health schema 8, no-fallback state, snapshot timestamp, position count and SHA-256, and only then changes the configured endpoint.

## Recommended migration order

1. Update Portfolio Architect through HACS to **1.55.0** and restart Home Assistant once.
2. Update the installed historical **Portfolio Architect Gateway — Comdirect** App to **1.55.0**. Keep it running and authoritative.
3. Align the installed DKB and Trade Republic Apps to **1.55.0**. Generic Import only needs alignment if it is intentionally installed. If Generic Import is not intentionally configured, do **not** install it or add its discovery card/source solely for this migration. Any isolated Generic Import smoke test must not alter the real production source set or broker configuration, and a Generic Import App installed only for this standalone smoke test should be uninstalled after this standalone smoke test.
4. Install **Portfolio Architect Gateway — Comdirect NEW**. Do not uninstall or stop the historical App. The new App starts only its migration/setup shell and must not create a PA discovery flow yet.
5. Open **Comdirect NEW** and copy its one-time migration code.
6. Open the historical Comdirect App. In **App identity migration**, paste the code and stage the migration. Verify the bounded summary shown by both Apps: source hostname, private-CA SHA-256, canonical snapshot time/SHA-256, acquisition mode and private-file count. No account identifiers or OAuth secrets should be shown.
7. In **Comdirect NEW**, explicitly commit the staged long-lived state. The App reconciles the historical non-secret Supervisor options to its own configuration before allowing cut-over.
8. Return to the historical App and choose **Freeze legacy for cut-over**. Do not uninstall it. Its provider activity stops, but Portfolio Architect can continue reading the already trusted cached snapshot during the transition.
9. Return to **Comdirect NEW**, confirm that the legacy App is frozen, and explicitly approve canonical runtime. Restart **Comdirect NEW**.
10. If the migrated acquisition mode is `live_api`, perform a fresh Comdirect PhotoTAN bootstrap in **Comdirect NEW**. The old OAuth session was intentionally not transferred. If the active mode is static CSV, no provider authentication is required solely for the migration.
11. Wait for the Home Assistant discovery flow **Migrate Comdirect Gateway identity securely**. Confirm only after it shows the expected old/new hosts and the same private-CA SHA-256. Portfolio Architect then performs its own authenticated health/snapshot validation before updating the endpoint.
12. Reload/inspect Portfolio Architect. Require the same single `comdirect` provider, healthy verified HTTPS, inactive HA LKG, normal freshness and unchanged portfolio/planner semantics. Confirm the configured Comdirect endpoint now uses the `*-portfolio-architect-gateway-comdirect` hostname and the CA SHA-256 is unchanged.
13. Only after step 12 passes, uninstall the historical **Portfolio Architect Gateway — Comdirect** App. Keep **Comdirect NEW** installed; its visible name remains intentionally distinguishable for the v1.55 migration release and can be simplified in a later cosmetic release.

## Recovery before PA cut-over

If anything fails before Portfolio Architect has changed its endpoint, leave the historical App installed. If it was frozen, use its **Resume legacy on restart** action and restart it. The new App remains non-authoritative until the explicit PA cut-over validates successfully. Do not delete the historical App-private state merely to retry.

## After PA cut-over

Do not reinstall/start the historical App as another active Comdirect source. Portfolio Architect continues to use the canonical provider identity `comdirect`; the App slug change does not create a second portfolio provider or alter acquisition/freshness semantics.

No dashboard replacement, broker change, DKB probe, Trade Republic re-import, order, transfer or trading capability is introduced by v1.55.0.
