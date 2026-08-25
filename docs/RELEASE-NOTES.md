# Portfolio Architect 1.52.0

Portfolio Architect v1.52.0 is a Gateway maturity/status cleanup built from the
live-accepted v1.51.1 architecture. It changes how Home Assistant presents App
maturity; it does not change provider acquisition or Portfolio Architect planning
semantics.

## DKB and Trade Republic graduate to stable

The DKB Gateway's bounded depot-CSV holdings path and independent Girokonto cash
CSV path have been repeatedly live-proven across acquisition migration, provider
cash, freshness, private-PKI transport and subsequent upgrades. The Trade Republic
Gateway's local `DEPOTAUSZUG` holdings and `KONTOAUSZUG` cash PDF paths have likewise
been repeatedly live-proven through multi-provider aggregation and later releases.

Their Home Assistant App `stage` therefore changes from `experimental` to `stable`.
This is a maturity-label correction, not a new capability.

## DKB FinTS remains experimental research

Promoting the DKB App does not promote authenticated FinTS. DKB Ingress now labels
the anonymous BPD capability probe itself **EXPERIMENTAL · RESEARCH ONLY**. The
probe remains registration-gated, anonymous, bounded and isolated from the active
CSV evidence. It cannot replace, refresh or silently fall back from DKB CSV
holdings/cash. Authenticated FinTS holdings, balance, transaction or money-movement
operations remain unavailable.

## Generic Import remains experimental

The dedicated provider-neutral Generic Import Gateway remains `experimental` until
its mapped-CSV path receives deliberate live Home Assistant exercise. The release
upgrade guide provides a wholly synthetic, standalone two-position smoke test that
must not be connected to the real portfolio source set.

The Generic Import security boundary is unchanged: fixed provider identity
`generic_csv`, admin-only Ingress, verified private-PKI HTTPS, transient raw CSV,
canonical holdings-only persistence, no provider credentials, no currency
conversion, and no cash/transaction/order/transfer/payment capability.

## Documentation and release metadata cleanup

Current provider documentation now reflects the actual four-App architecture and
capability-scoped maturity model. The SPDX SBOM explicitly includes the Generic
Import Gateway package alongside Comdirect, DKB and Trade Republic.


The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; this release does not change any configured freshness threshold.

The historical v1.39 colourful allocation view was not included in v1.38.1; that release sequencing remains documented.

The historical `v1.19.0-rc2` brokerage-probe branch remains historical and is not promoted by this release. authenticated DKB FinTS acquisition remains disabled. This release does not move PDF parsing into Portfolio Architect; Trade Republic statement parsing remains isolated in its Gateway.

## Preserved contracts

- config-entry schema 12: unchanged
- portfolio payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 7 current; schemas 1–6 remain supported
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- Comdirect `live_api` / explicit `csv` arbitration and no-fallback: unchanged
- DKB CSV holdings/cash acquisition: unchanged
- Trade Republic PDF holdings/cash acquisition: unchanged
- Generic Import mapped-CSV semantics: unchanged
- v1.48 acquisition-aware freshness and explicit thresholds: unchanged
- independent holdings/cash evidence clocks: unchanged
- provider-scoped cash, funding topology, execution-path and planner economics: unchanged
- verified private-PKI HTTPS, bearer authentication, DNS pinning and source-set/LKG behavior: unchanged
- no trading, order, transfer, payment, transaction-history, sell or withdrawal capability

No trading, order, transfer, payment, or transaction-history capability is added; sell and withdrawal capability remain absent.

No dashboard YAML replacement is required.
