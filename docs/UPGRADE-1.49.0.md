# Upgrade to Portfolio Architect 1.49.0

Version 1.49.0 retires the completed Home Assistant-side Comdirect CSV migration bridge. Provider-specific Comdirect CSV acquisition remains fully supported inside **Portfolio Architect Gateway — Comdirect**; only the temporary PA-side parser/oracle used for the v1.48 migration window is removed.

## Normal upgrade from v1.48.2

1. Confirm Portfolio Architect is already using **Portfolio Architect Gateway — Comdirect**, not a legacy Home Assistant-side `comdirect_csv` source.
2. Update the Portfolio Architect integration to **1.49.0** and restart Home Assistant once.
3. Align the Comdirect, DKB and Trade Republic Gateway Apps to **1.49.0** in place for package-version hygiene.
4. Preserve all App-private data volumes, Gateway bearer tokens and private-CA trust. Do not reauthenticate Comdirect or re-import DKB/TR evidence solely because of this release.
5. Confirm the same three provider Gateways remain healthy, source count/provider identities are unchanged, freshness remains valid, and planner/cash-routing economics are unchanged.
6. No dashboard YAML replacement is required.

## Legacy Comdirect CSV prerequisite

A config entry that still uses the historical Home Assistant-side `source_provider: comdirect_csv` cannot migrate to config-entry schema 11. This is deliberate fail-closed behavior: v1.49.0 will not reinterpret or silently discard that source.

Such an installation must remain on **v1.48.2**, complete the verified v1.48 Comdirect Gateway cut-over while the one-release migration oracle still exists, verify the Gateway-backed source, and only then update to v1.49.0.

## What is removed

- the production Home Assistant-side Comdirect depot-CSV parser;
- the `comdirect_csv` current source-provider option/enum state;
- the Supervisor discovery confirmation step that compared legacy local Comdirect CSV holdings with a verified schema-7 Comdirect Gateway in explicit `csv` mode; and
- the associated current translation/icon surfaces.

Historical upgrade/release documentation remains as audit history.

## What is unchanged

- Comdirect Gateway `live_api` and `csv` acquisition modes, including strict no-fallback arbitration;
- static Comdirect depot holdings and Girokonto cash import inside the Comdirect Gateway;
- DKB CSV and Trade Republic PDF acquisition;
- v1.48.1/v1.48.2 acquisition-aware cadence freshness and explicit user thresholds;
- independent holdings/cash evidence clocks;
- portfolio payload schema 8, REST portfolio schema 1, Gateway health schema 7, presentation schema 2 and broker schemas 1/2/3;
- verified private-PKI HTTPS, bearer authentication, DNS pinning, snapshot integrity, source-set atomicity and Home Assistant LKG; and
- the advisory-only boundary: no trading, order, transfer, payment, transaction-history, sell or withdrawal capability is added.
