# Portfolio Architect 1.35.1

Version 1.35.1 is a narrow Comdirect session-maintenance resilience hotfix on top of the
live-accepted v1.35.0 provider-scoped funding release.

## Comdirect maintenance-thread resilience

During v1.35.0 live acceptance, the Comdirect OAuth-maintenance thread encountered a direct
`ConnectionResetError` while waiting for an OAuth refresh response. That socket exception was not
covered by the transport's existing `URLError` / timeout / TLS classifier and escaped the worker,
terminating the long-lived maintenance thread.

Version 1.35.1 closes both layers of that failure mode:

- built-in `ConnectionError` failures, including connection reset/refused/aborted conditions, are
  classified as the existing bounded retryable `RemoteApiError` with no retained response body;
- a final ordinary-`Exception` containment barrier around one maintenance iteration prevents an
  unexpected future exception from terminating the thread;
- the defense-in-depth log records only the exception class name and never arbitrary exception
  text; and
- conclusive OAuth rejection handling remains unchanged and still fails closed to PhotoTAN
  reauthentication when the bank actually rejects the refresh session.

The hotfix does not claim that the observed connection reset caused the later `invalid_token`.
It removes the proven resilience defect: one transient transport failure can no longer silently
remove the independent OAuth-maintenance cadence.

## Quiet dashboard correction

The two German allocation-chart labels that still used the English `Robotics · Acc` text now read
`Robotik · Thes.`. The English accumulating target remains `Robotics · Acc`, and the retained
old distributing holding remains `Robotics · Dist` / `Robotik · Aussch.`.

## Compatibility and security invariants

- v1.35.0 provider-scoped authorized cash and funding topology: unchanged.
- Broker schema 3 directed transfer relationships and route economics: unchanged.
- Portfolio payload schema 8: unchanged.
- REST portfolio schema 1: unchanged.
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- Comdirect PhotoTAN/bootstrap, account selection, authorized-cash policy and read-only acquisition:
  unchanged apart from transport/maintenance resilience.
- Trade Republic statement import/private diagnostics: unchanged.
- DKB anonymous FinTS raw/decoded response fingerprinting: unchanged; DKB remains non-live.
- Verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and
  no-plaintext fallback: unchanged.
- No trading, order placement, automatic sell, transfer execution, payment or transaction-history
  capability is introduced.

## Long-running compatibility contracts

- v1.33.0 source-freshness and plan-schedule separation remains preserved; v1.35.1 does not change any configured freshness threshold.
- Recurring scheduling remains anchored to the latest valid Portfolio Architect evaluation.
- The historical `v1.19.0-rc2` brokerage probe remains excluded and is not promoted by this release.
- DKB live Gateway acquisition remains a later provider-specific milestone; v1.35.1 adds no authenticated DKB holdings path.
- This release does not move PDF parsing into Portfolio Architect; Trade Republic statement PDF parsing remains isolated provider-side and memory-only.
- No trading, order, transfer, payment, or transaction-history capability is introduced.
- v1.35.0 provider-scoped funding remains advisory planning metadata only.

See `docs/UPGRADE-1.35.1.md`.
