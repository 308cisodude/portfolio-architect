# Upgrade to Portfolio Architect 1.45.0

Version 1.45.0 moves DKB depot-CSV acquisition from the Home Assistant integration boundary into **Portfolio Architect Gateway — DKB**. The migration is deliberately fail-closed and should be performed with the existing legacy DKB CSV source still configured.

## Upgrade order

1. Update the Portfolio Architect Home Assistant integration to **1.45.0** and restart Home Assistant once.
2. Update **Portfolio Architect Gateway — DKB** to **1.45.0**. Align the Comdirect and Trade Republic Gateway Apps to **1.45.0** as normal package-version hygiene; their provider behavior is unchanged.
3. Open the DKB Gateway admin-only Ingress page. It now contains a **DKB acquisition** section above the existing FinTS research controls.
4. Upload the current DKB depot CSV export. If more than one DKB depot contributes to Portfolio Architect, upload all current depot exports together in the same batch. Older dated exports may be included; only the newest export for each depot is selected.
5. Confirm the DKB Gateway reports an active canonical snapshot with the expected position count and conservative snapshot date. The raw CSV and depot numbers are not retained.
6. Return to Home Assistant. Supervisor discovery for the DKB Gateway should offer **Migrate legacy DKB CSV to the DKB Gateway** rather than a normal additional-source action.
7. Enter the bearer token shown by the DKB Gateway. Portfolio Architect will validate private-CA HTTPS, provider identity, health/snapshot integrity and exact canonical equivalence with the currently configured legacy DKB CSV source.
8. Only an exact match completes the cut-over. On success, the legacy `dkb_csv` option paths are removed and one verified-HTTPS supplemental `provider_id: dkb` source is stored atomically. On any mismatch, no source configuration is changed.
9. Confirm Portfolio Architect reloads healthy and that total portfolio value, DKB contribution, source freshness, holdings quantity and plan output are unchanged apart from the source label/transport now being the DKB Gateway.
10. No dashboard YAML replacement is required.

## Important migration rule

Do **not** remove the existing DKB CSV source manually before importing and validating the Gateway snapshot. The legacy source is the comparison oracle for the bridge release. v1.45.0 intentionally retains the old parser only for this equivalence proof and for installations that have not migrated yet.

New HA-side DKB CSV source creation is no longer offered. After the v1.45 migration is live-proven, a later cleanup release can remove the legacy provider-specific parser/path from Portfolio Architect itself.

## DKB CSV batch semantics

The upload is authoritative rather than incremental. Up to eight current exports may be selected together. Portfolio Architect Gateway — DKB performs newest-per-depot selection in memory and persists one canonical provider snapshot. This avoids storing depot identifiers or private raw documents merely to support incremental per-depot state.

## FinTS is not part of this migration

The existing anonymous BPD probe remains optional and independent. You do not need to probe FinTS, change the FinTS product registration, or obtain Big Slow Blue's blessing to migrate DKB CSV acquisition. A probe cannot alter the CSV snapshot. Authenticated FinTS acquisition remains disabled.

## Preserved contracts

Payload schema 8, REST portfolio schema 1, Gateway health schema 6, presentation schema 2 and broker schemas 1/2/3 remain unchanged. Comdirect and Trade Republic provider behavior is unchanged. Verified private-PKI HTTPS, bearer authentication, source-set/LKG binding, provider isolation and Portfolio Architect's advisory-only boundary remain intact.
