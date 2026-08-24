# Upgrade to Portfolio Architect 1.51.0

Version 1.51.0 completes the current provider-acquisition cleanup by moving the remaining provider-neutral mapped CSV acquisition path out of the Home Assistant integration and into a dedicated **Portfolio Architect Gateway — Generic Import** App. It also removes the DKB probe UI's installation-specific Europe/Berlin assumption while keeping the probe timestamp canonical in UTC.

## Normal upgrade from v1.50.0

For the normal Gateway-backed architecture used by current installations:

1. Update the Portfolio Architect integration to **1.51.0** and restart Home Assistant once.
2. Align the Comdirect, DKB and Trade Republic Gateway Apps to **1.51.0** in place. Preserve all App-private state and trust material.
3. Confirm the same configured provider set remains healthy and freshness/economics are unchanged.
4. No CSV/PDF re-import, Comdirect reauthentication, broker migration or dashboard replacement is required solely because of this release.
5. Install **Portfolio Architect Gateway — Generic Import** only if a provider-neutral mapped CSV escape hatch is actually needed. Existing official Comdirect/DKB/Trade Republic sources do not require it.

## Fail-closed migration for an active local generic CSV source

Config-entry schema 12 no longer permits Portfolio Architect itself to acquire a local mapped CSV. An installation that still has `source_type: local_files` therefore **does not migrate automatically**. No path, mapping or source is silently discarded or reinterpreted.

Remain on v1.50.0 and perform an explicit cut-over:

1. Install **Portfolio Architect Gateway — Generic Import 1.51.0**.
2. Open its admin-only Ingress page and import the mapped CSV using the explicit encoding, delimiter, header-row, number-format and column mapping controls.
3. Verify the Generic Import Gateway reports a healthy canonical snapshot with provider ID `generic_csv` over verified private-PKI HTTPS.
4. While still on v1.50.0, reconfigure Portfolio Architect from the local CSV source to that verified REST Gateway and verify the portfolio result.
5. Only then upgrade the integration to v1.51.0.

## Generic Import Gateway boundary

The new App is deliberately provider-neutral and cannot impersonate an official provider. Its fixed provider identity is `generic_csv` and its acquisition mode is `csv`.

The uploaded CSV exists only for the duration of the request. The App persists only:

- the validated canonical REST-schema-1 holdings snapshot;
- the bounded non-secret mapping configuration required for the next explicit import; and
- a privacy-safe accepted/rejected import diagnostic.

No raw CSV, filename, account identifier, transaction row or provider credential is persisted. The App provides holdings only; it does not infer or import provider cash. If a Currency column is mapped, every imported position must explicitly be EUR. No currency conversion is performed.

Because a generic mapped CSV carries no standardized institution-issued portfolio timestamp, the successful explicit import time is the holdings evidence timestamp. Re-importing is an explicit operator attestation and deliberately refreshes that evidence clock.

## DKB probe timestamp localization

The persisted DKB `probe_sent_at` value and `/status` representation remain timezone-aware UTC. v1.51.0 removes the hard-coded Europe/Berlin display conversion.

Home Assistant Ingress does not expose the viewing user's configured frontend timezone to the App through a stable supported server-side interface. The DKB Ingress page therefore uses the browser's standard `Intl.DateTimeFormat` timezone as the conservative local-display fallback and continues to show authoritative UTC alongside it. It does not inspect undocumented Home Assistant parent-page internals or gain Home Assistant API permission merely for timezone presentation.

This changes display only. Probe dispatch, registration gating, bounded parsing, fingerprints and authenticated-FinTS acquisition gates are unchanged.

## Preserved boundaries

- portfolio payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 7: unchanged; schemas 1–6 remain supported
- presentation schema 2 and broker schemas 1/2/3: unchanged
- Comdirect `live_api`/`csv` arbitration and no-fallback semantics: unchanged
- DKB CSV holdings/cash acquisition and Trade Republic PDF holdings/cash acquisition: unchanged
- v1.48 acquisition-aware freshness and explicit thresholds: unchanged
- holdings and cash evidence clocks remain independent
- verified private-PKI HTTPS, bearer authentication, DNS pinning, source-set atomicity and Home Assistant LKG: unchanged
- no trading, order, transfer, payment, transaction-history, sell or withdrawal capability is added
