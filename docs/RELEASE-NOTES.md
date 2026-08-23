# Portfolio Architect 1.47.0

Portfolio Architect v1.47.0 gives **Portfolio Architect Gateway — DKB** the same provider-side holdings/cash separation already established for Trade Republic. DKB depot CSV remains the holdings evidence family; a native DKB Girokonto `Umsatzliste` CSV can now supply independent provider-scoped investment cash.

## Independent DKB Girokonto cash evidence

The DKB Gateway Ingress UI now has a separate cash-import control for the supported native Girokonto CSV export. The bounded parser:

- requires the recognized `Girokonto` export structure;
- requires exactly one dated `Kontostand vom DD.MM.YYYY:` row;
- accepts only an explicit EUR balance and parses it as an exact Decimal;
- validates the expected transaction-table shape without retaining transaction contents;
- rejects malformed, ambiguous, oversized, non-EUR or future-dated exports fail-closed;
- treats positive balance as eligible/authorized cash under the existing `all_available` provider policy;
- clamps zero or negative balance to EUR 0 eligible/authorized cash; and
- never infers an overdraft, credit line, pending-credit amount, or cash value from transaction arithmetic.

The raw CSV, account identifier, transaction rows, counterparties, payment references and other transaction-level fields never persist. Only normalized balance/date state is written to the App-private data volume.

## Holdings and cash clocks remain independent

A DKB depot CSV import replaces only holdings evidence. A Girokonto cash import replaces only cash evidence.

The canonical DKB REST snapshot composes the most recently accepted holdings and cash evidence without changing the holdings `generated_at`. DKB holdings remain freshness-classified as `gateway_snapshot`; DKB cash is freshness-gated using the `imported_statement` policy family, matching Trade Republic cash. Re-importing the same dated cash file cannot refresh its evidence age merely because the upload happened later.

## Provider-neutral wire contract remains unchanged

The DKB Gateway publishes cash through the existing optional REST-schema-1 fields:

- `investment_reserve.available_eur` + `as_of`; and
- `investment_cash` with account balance, eligible cash, authorized cash, `all_available` policy and `as_of`.

No new REST or health schema version is introduced. Portfolio Architect's existing provider-scoped cash aggregation, funding topology and route-selection logic consume the DKB cash automatically when it is fresh.

## FinTS boundary unchanged

The anonymous registration/BPD capability probe remains isolated. No DKB login, PIN/TAN, authenticated FinTS holdings/balance/transaction request, order, transfer, payment, sell or withdrawal capability is introduced. FinTS cannot replace or silently fall back to either CSV evidence family.

## Historical compatibility contracts retained

The v1.33.0 source-freshness and plan-schedule separation remains intact: recurring scheduling is anchored to the latest valid Portfolio Architect evaluation, and this release does not change any configured freshness threshold. The historical v1.39 colourful allocation view was not included in v1.38.1; that sequencing remains documented. The historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release. Trade Republic provider-specific statement parsing remains in its Gateway; this release does not move PDF parsing into Portfolio Architect. authenticated DKB FinTS acquisition remains disabled. No trading, order, transfer, payment, or transaction-history capability is introduced.

## Preserved contracts

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported;
- presentation schema 2 and broker schemas 1/2/3: unchanged;
- DKB depot CSV parsing/newest-per-depot/conflict semantics: unchanged;
- Comdirect live acquisition, OAuth/session maintenance and authorized-cash behavior: unchanged;
- Trade Republic DEPOTAUSZUG/KONTOAUSZUG acquisition: unchanged;
- source-set atomicity, Home Assistant LKG, planner economics and advisory funding topology: unchanged;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- no dashboard YAML replacement is required.

The next provider-acquisition architecture milestone remains moving the existing Comdirect CSV adapter into **Portfolio Architect Gateway — Comdirect**, with explicit live-API/CSV arbitration and no silent fallback.
