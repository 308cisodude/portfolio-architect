# Upgrade to Portfolio Architect 1.52.0

Version 1.52.0 is a Gateway maturity/status cleanup built from the live-accepted
v1.51.1 architecture. It does not change acquisition, freshness, planning, wire
schemas, private-PKI transport, source-set atomicity/LKG or advisory-only semantics.

## Gateway maturity labels

The Home Assistant App-level maturity markers now follow the capabilities that have
actually been live-proven:

- **Portfolio Architect Gateway — Comdirect** remains **stable**.
- **Portfolio Architect Gateway — DKB** graduates to **stable** for its established
  depot-CSV holdings and Girokonto cash-CSV acquisition paths.
- **Portfolio Architect Gateway — Trade Republic** graduates to **stable** for its
  established `DEPOTAUSZUG` holdings and `KONTOAUSZUG` cash PDF acquisition paths.
- **Portfolio Architect Gateway — Generic Import** remains **experimental** pending
  deliberate live exercise of its provider-neutral mapped-CSV path.

The DKB App becoming stable does **not** promote FinTS acquisition. The anonymous
BPD probe is explicitly labelled **EXPERIMENTAL · RESEARCH ONLY** inside DKB
Ingress. Authenticated DKB FinTS acquisition remains unavailable and gated on
legitimate product-registration/bank-capability evidence followed by separate
authenticated user-capability validation.

## Upgrade procedure

1. Update **Portfolio Architect** through HACS to **1.52.0** and restart Home
   Assistant once.
2. Update the installed Comdirect, DKB and Trade Republic Gateway Apps to **1.52.0**
   in place, preserving each App-private `/data` volume and trust material.
3. Do not reauthenticate Comdirect and do not re-import DKB/Trade Republic evidence
   solely because of the upgrade.
4. If Generic Import is already installed, update it to 1.52.0 in place. If it is
   not installed, it is not required for the existing official-provider portfolio.
5. No dashboard YAML replacement is required.

## Optional isolated Generic Import live smoke

v1.52.0 deliberately keeps Generic Import experimental so its first real Home
Assistant exercise can be performed without changing an existing portfolio.

For that smoke test:

1. Install **Portfolio Architect Gateway — Generic Import 1.52.0**, but do **not**
   add its discovery card/source to the existing Portfolio Architect config entry.
2. Open its admin-only Ingress page and import this wholly synthetic CSV using the
   default mapping:

   ```csv
   Identifier,Security,Market Value,Currency,ISIN,Asset Type
   DEMOETF1,Example Global ETF,1234.56,EUR,IE00BJ0KDQ92,ETF
   DEMO1234,Example Company,250.00,EUR,DE0005557508,Stock
   ```

3. Confirm the App reports an accepted two-position canonical snapshot and remains
   healthy. Raw CSV bytes and the original filename must not appear in persisted
   state or diagnostics.
4. Keep the App isolated from the real Portfolio Architect source set. If there is
   no genuine Generic Import use case, it may be uninstalled after this standalone
   smoke test rather than leaving synthetic holdings staged for accidental use.

This smoke test proves the App/runtime path only; it must not alter the real
Comdirect/DKB/Trade Republic portfolio.

## Live acceptance

Starting from the live-accepted v1.51.1 installation:

1. Confirm the integration and the three installed official provider Apps report
   1.52.0 after update.
2. Confirm the DKB and Trade Republic App cards no longer carry the App-level
   **Experimental** badge; Generic Import, if installed, still does.
3. Confirm DKB Ingress marks only the anonymous BPD probe as
   **EXPERIMENTAL · RESEARCH ONLY** and authenticated FinTS remains unavailable.
4. Run the established acquisition/freshness template and confirm:
   - Comdirect `live_api / 24 h`;
   - Trade Republic `imported_statement / 336 h`;
   - DKB `csv / 336 h`;
   - `data_fresh: on` under `evidence_kind_thresholds`;
   - static DKB/TR evidence timestamps are not refreshed by the software update.
5. Confirm Home Assistant LKG is inactive, all three official providers remain
   configured exactly once, and provider cash/funding topology/execution path and
   recommendation economics remain unchanged.
6. Optionally perform the isolated Generic Import smoke above without connecting it
   to the real portfolio.
7. Do not send an extra DKB FinTS probe solely for v1.52 acceptance. The next
   naturally timed probe remains the functional acceptance point for the persisted
   probe-dispatch timestamp/local-display path.
