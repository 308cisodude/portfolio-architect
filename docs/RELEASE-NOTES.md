# Portfolio Architect 1.48.0

Portfolio Architect v1.48.0 moves provider-specific Comdirect CSV acquisition into **Portfolio Architect Gateway — Comdirect** and makes acquisition policy explicit. The Comdirect Gateway now has two mutually exclusive modes: `live_api` and `csv`. Portfolio Architect continues to consume only the same provider-neutral REST portfolio snapshot.

## Complete static Comdirect acquisition

The Comdirect Gateway can now operate without automatic Comdirect API acquisition when the operator deliberately selects `csv` mode:

- depot CSV supplies holdings;
- Girokonto transaction CSV may supply independent provider-scoped investment cash, but only when the export contains exactly one explicit opening balance and one explicit closing/current balance that reconcile exactly through the transaction deltas;
- transaction rows are validated structurally but never summed to invent a balance;
- holdings and cash uploads are parsed in memory and raw CSV bytes, filenames, depot/account identifiers and transaction contents are never persisted;
- only normalized holdings, normalized cash and bounded evidence timestamps survive in the App-private data volume; and
- static holdings and cash have independent evidence clocks. Importing one cannot refresh the other.

The supported Comdirect depot CSV has no trustworthy bank-issued snapshot timestamp in its securities table. Static holdings therefore use the explicit Gateway import time as evidence. The cash importer likewise uses import time and fails closed unless the explicit opening balance, transaction deltas and explicit closing/current balance reconcile exactly.

## Explicit acquisition arbitration

`live_api` remains the backward-compatible default. CSV uploads can be staged while live API mode is active, but they cannot become authoritative without an explicit operator mode switch.

There is no cross-mode fallback:

- an API refresh failure never consults staged CSV evidence;
- CSV mode never performs automatic holdings/cash API acquisition;
- the Comdirect OAuth/session-maintenance worker is inactive while CSV mode is selected; and
- a missing/stale/invalid static evidence family never triggers a live API fallback.

An explicit operator-triggered PhotoTAN bootstrap remains possible while CSV mode is active so live credentials can be prepared. It does not change the active source. Mode changes validate the requested source before persistence and roll back if the new mode cannot publish a valid snapshot.

The existing Comdirect investment-cash authorization policy is acquisition-neutral: when static cash is active, the same all-available/cap/retain policy is applied to the explicit imported balance. A non-positive balance never authorizes overdraft or credit.

## Legacy Comdirect CSV migration bridge

New Home Assistant-side `comdirect_csv` source creation is no longer offered. A still-configured legacy primary Comdirect CSV can migrate through Supervisor discovery only when the discovered Comdirect Gateway:

- uses verified private-CA HTTPS and the expected bearer authentication;
- reports provider identity `comdirect` through health schema 7;
- reports explicit `acquisition_mode: csv` and healthy snapshot state;
- passes snapshot hash/count/timestamp transport-integrity checks; and
- produces canonical holdings exactly equal to the existing legacy parser result.

The historical local filesystem mtime is deliberately not treated as bank evidence and is not required to equal the Gateway import timestamp. Only an exact holdings match completes one atomic config-entry cut-over; every mismatch leaves the existing source untouched.

## Gateway acquisition UX

All three provider Apps now make acquisition boundaries visually obvious:

- Comdirect has separate, optically distinct **Live acquisition · Comdirect API** and **Static acquisition · Comdirect CSV** cards with ACTIVE/INACTIVE state;
- DKB separates **Static acquisition · DKB CSV** from **Live acquisition · DKB FinTS**, explicitly marking authenticated FinTS as unavailable/research-only; and
- Trade Republic separates its active static statement-import family from an explicitly unavailable live-acquisition section.

This is presentation of the existing security boundary, not a relaxation of it.

## Health and freshness

Gateway health schema **7** adds one bounded `acquisition_mode` field. Health schemas 1–6 remain accepted for compatibility. REST portfolio schema 1 is unchanged.

Comdirect static holdings and cash are freshness-classified as CSV evidence rather than live API evidence. `live_api` retains the existing live freshness semantics. DKB and Trade Republic acquisition behavior/freshness are otherwise unchanged.

## Historical compatibility contracts retained

The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; this release does not change any configured freshness threshold. The historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release. The historical v1.39 colourful allocation view was not included in v1.38.1; that sequencing remains documented. Trade Republic provider-specific statement parsing remains in its Gateway; this release does not move PDF parsing into Portfolio Architect. authenticated DKB FinTS acquisition remains disabled. No trading, order, transfer, payment, or transaction-history capability is introduced.

## Preserved boundaries

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 7 current; schemas 1–6 remain supported;
- presentation schema 2 and broker schemas 1/2/3: unchanged;
- source-set atomicity, Home Assistant LKG, planner economics, funding topology and execution-path behavior: unchanged;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- no trading, order, transfer, payment, transaction-history, sell or withdrawal capability is added; and
- no dashboard YAML replacement is required.
