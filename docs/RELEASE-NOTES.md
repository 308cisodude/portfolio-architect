# Portfolio Architect 1.45.1

Portfolio Architect v1.45.1 is a narrow migration-resilience hotfix for the DKB CSV-to-Gateway bridge introduced in v1.45.0. Live acceptance of v1.45.0 proved the exact-equivalence guard itself works, but also exposed an interaction with the DKB Gateway's normal cached-snapshot age policy: a legacy DKB CSV older than the Gateway's default seven-day serving horizon could not be used as the migration comparison oracle without temporarily widening that runtime age limit.

## Bounded migration snapshot

The common Gateway shell now supports an optional authenticated read-only migration-snapshot endpoint at `/api/v1/migration-snapshot`. The endpoint is disabled by default and is enabled only by **Portfolio Architect Gateway — DKB**.

The endpoint returns only the already-normalized canonical provider snapshot. It never returns raw CSV bytes, depot numbers, filenames, upload metadata, FinTS material, credentials, or any provider-private acquisition state. It uses the same bearer token, private-CA verified HTTPS, local-address validation, DNS pinning, response-size bounds, canonical JSON parser, SHA-256 integrity header, and position-count integrity header as the normal portfolio endpoint.

Crucially, this endpoint does **not** alter normal runtime availability. An expired snapshot remains unavailable from `/api/v1/portfolio`, continues to fail closed for normal Portfolio Architect operation, and is exposed through the migration endpoint only for the one exact legacy-equivalence comparison.

## Expired health documents are schema-consistent

The common Gateway health document now omits snapshot timestamp, age, expiry, SHA-256, and position-count fields whenever the normal runtime snapshot is unavailable because its cached-snapshot age limit has expired. This restores the health-schema invariant already enforced by the Home Assistant parser: `snapshot_available: false` cannot be combined with available-snapshot age or integrity metadata.

Normal healthy and last-known-good health semantics are unchanged.

## DKB legacy migration behavior

The v1.45 migration remains fail-closed and atomic:

- if the DKB snapshot is still normally available, v1.45.1 uses the established `/api/v1/portfolio` path and requires health/snapshot timestamp, SHA-256 and position-count parity exactly as before;
- if the normal DKB snapshot is unavailable only through the valid degraded/unavailable Gateway state, the migration flow may fetch the bounded migration snapshot instead;
- the migration snapshot still requires verified transport integrity and exact canonical holdings, quantity, instrument identity and conservative source-timestamp equality with the configured legacy DKB CSV source;
- any mismatch, authentication failure, TLS failure, malformed response, missing migration endpoint, invalid Gateway state, or source-path failure leaves the existing configuration untouched;
- the legacy `dkb_csv` source is removed only in the same atomic config-entry mutation that installs the verified `provider_id: dkb` Gateway source.

A v1.45.1 integration paired with an older DKB App remains compatible for normal fresh-snapshot migration. An expired legacy comparison requires the DKB App to be updated to v1.45.1 so the bounded migration endpoint exists.

## Historical compatibility contracts retained

The v1.33.0 source-freshness and plan-schedule separation remains intact: recurring scheduling is anchored to the latest valid Portfolio Architect evaluation, and this hotfix does not change any configured freshness threshold. The historical v1.39 colourful allocation view was not included in v1.38.1; that sequencing remains documented. The historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release. Trade Republic provider-specific statement parsing remains in its Gateway; this release does not move PDF parsing into Portfolio Architect. authenticated DKB FinTS acquisition remains disabled. No trading, order, transfer, payment, or transaction-history capability is introduced.

## Unchanged boundaries

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported;
- presentation schema 2 and broker schemas 1/2/3: unchanged;
- DKB CSV parsing, newest-per-depot selection, exact Decimal valuation, privacy rules and canonical persistence: unchanged from v1.45.0;
- normal DKB cached-snapshot age policy: unchanged;
- Comdirect acquisition, OAuth/session maintenance and provider-scoped cash: unchanged;
- Trade Republic holdings/cash statement acquisition: unchanged;
- DKB FinTS remains the same isolated anonymous BPD capability probe; authenticated FinTS acquisition, PIN/TAN, transfers, payments, orders, transaction history, sell and withdrawal capability remain absent;
- allocation, drift, policy, recommendation, funding, route economics and execution-path behavior: unchanged;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- no dashboard YAML replacement is required.

Protected GitHub workflows remain authoritative for actual provider-App Docker/private-PKI smoke execution when local Docker is unavailable.
