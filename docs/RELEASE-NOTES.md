# Portfolio Architect 1.35.0

Version 1.35.0 adds provider-scoped investment cash and explicit funding topology to the
local advisory planner. It is prepared from the v1.34.1 baseline and preserves the existing
provider acquisition, private-PKI transport, target-identity and presentation contracts.

## Provider-scoped cash

Each accepted REST Gateway's authorized investment cash is now preserved with that provider's
identity. Multiple provider cash pools remain separate throughout allocation and recommendation
calculation; cash reported by one institution is never silently treated as cash already available
at another.

The existing provider-owned authorization semantics remain unchanged. `all_available` still
authorizes all eligible provider cash and `capped` still limits that provider's usable cash to the
configured cap.

## Explicit funding topology

`broker.yaml` schema 3 extends the established schema-2 execution-provider model with a bounded
list of directed `funding_transfers`. Each relationship contains:

- `from_provider`;
- `to_provider`;
- `fee_eur`; and
- `settlement_business_days`.

Same-provider funding remains implicit and free. Cross-provider funding is considered only when
the exact directed edge exists; reverse transferability is never inferred.

The optimizer now chooses funding source and execution route together. Transfer fees participate
in the economic cost ratio. Settlement business days are used only as a deterministic tie-breaker
after cost. A configured fixed transfer fee is counted once per source/destination edge within one
allocation run.

Recommendations remain advisory. When cross-provider funding wins, the payload exposes bounded
source/destination metadata and an aggregate transfer plan with the amount required at the
destination, transfer fee and settlement delay. Portfolio Architect does not initiate the transfer,
move money, place an order, record transaction history or assume that the recommendation was
executed.

## Small presentation and diagnostic corrections

- The accumulating Robotics target is labelled `Robotics · Acc` in the English reference
  dashboard and `Robotik · Thes.` in the German dashboard, keeping the retained distributing
  outside-scope share class visibly distinct as `Robotics · Dist` / `Robotik · Aussch.`.
- The DKB anonymous FinTS capability probe now fingerprints the exact bounded HTTP response body
  before whitespace normalization/base64 decoding and records only SHA-256 plus byte length. The
  existing decoded-response fingerprint remains. Exact raw and decoded response bytes are still
  discarded and never persisted.

## Compatibility and security invariants

- Portfolio payload schema 8: unchanged; provider-scoped funding fields are additive and validated.
- REST portfolio schema 1: unchanged.
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- Broker schemas 1 and 2: unchanged compatibility behavior. Schema 3 is explicit opt-in for funding
  topology so older configurations acquire no transfer assumptions merely by upgrading.
- Presentation schema 1 and opaque schema-2 target identity: unchanged.
- Comdirect OAuth/session/PhotoTAN acquisition behavior: unchanged.
- Trade Republic statement import and provider-side memory-only PDF parsing: unchanged.
- DKB remains experimental, manual-only and non-live. The anonymous BPD probe does not add login,
  PIN/TAN, holdings, balance, order, transfer or payment business transactions.
- Verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and
  no-plaintext fallback: unchanged.
- No trading, order placement, transfer execution, payment, transaction-history or automatic-sell
  capability is introduced.

See `docs/EXECUTION-PROVIDERS.md` and `docs/UPGRADE-1.35.0.md`.

## Long-running compatibility contracts

- v1.33.0 source-freshness and plan-schedule separation remains preserved; v1.35.0 does not change any configured freshness threshold.
- Recurring scheduling remains anchored to the latest valid Portfolio Architect evaluation.
- DKB live Gateway acquisition remains a later provider-specific milestone; the v1.35.0 diagnostic fingerprint does not enable authenticated holdings acquisition.
- This release does not move PDF parsing into Portfolio Architect; Trade Republic statement PDF parsing remains isolated provider-side and memory-only.
- The historical v1.19.0-rc2 brokerage probe remains excluded and is not promoted by this release.
- No trading, order, transfer, payment, or transaction-history capability is introduced. Funding topology is advisory planning metadata only.
