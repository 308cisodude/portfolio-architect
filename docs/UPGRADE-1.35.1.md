# Upgrade to Portfolio Architect 1.35.1

Version 1.35.1 is a narrow Comdirect session-maintenance resilience hotfix prepared on top of
v1.35.0. It does not change provider-scoped funding, broker schema 3, target identity, provider
aggregation, Gateway wire schemas or any banking write boundary.

## Why this hotfix exists

Live acceptance of v1.35.0 exposed an inherited Comdirect resilience edge case in the provider-
specific OAuth maintenance worker. A direct `ConnectionResetError` from the HTTPS stack escaped the
transport error classifier and then escaped the maintenance loop, terminating the long-lived
`comdirect-session-maintenance` thread. A later portfolio refresh received the bank's conclusive
`invalid_token` response and correctly required PhotoTAN reauthentication.

The connection reset is not treated as proof that the later invalid token was caused by that event.
The defect is the thread termination itself: a transient connection failure must remain retryable
and must not silently remove the independent five-minute OAuth-maintenance cadence.

## Fix

- Direct built-in `ConnectionError` failures, including `ConnectionResetError`, are reduced to the
  established bounded `RemoteApiError(status=0, operation=...)` transport classification.
- The long-lived Comdirect session-maintenance loop retains its specific handling for
  `ReauthenticationRequired`, `RemoteApiError`, authentication/configuration and protocol failures.
- A final per-iteration `Exception` containment barrier prevents an unexpected ordinary exception
  from terminating the worker. It logs only the exception class name, never arbitrary exception
  text.
- Conclusive bank-side OAuth rejection semantics are unchanged. `invalid_grant`, `invalid_token`,
  HTTP 401 and HTTP 403 still require interactive reauthentication.

## Upgrade order

1. Update **Portfolio Architect** through HACS to 1.35.1 and restart Home Assistant once.
2. Keep the existing plan, source configuration, freshness policy and real `broker.yaml` unchanged.
3. Update **Portfolio Architect Gateway — Comdirect** to 1.35.1 in place. Preserve `/data/gateway`,
   bearer token, private CA, OAuth/session state, selected investment account and cash policy.
4. Update the Trade Republic and DKB Apps to 1.35.1 for package alignment; preserve App-private
   state. No Trade Republic statement re-import or DKB FinTS reprobe is required solely for this
   hotfix.
5. Do not perform PhotoTAN reauthentication merely because of the upgrade when the current
   Comdirect session remains healthy.

## Expected live result

After the Comdirect App is on 1.35.1, normal five-minute session maintenance and fifteen-minute
portfolio refreshes remain independent. A transient upstream connection reset during an OAuth
maintenance attempt should be reported as a bounded retryable remote-API failure while the
maintenance worker remains alive for later cycles.

A deliberate production connection reset is **not** required for acceptance. Package alignment,
healthy repeated scheduled operation and regression evidence are sufficient; a naturally occurring
reset can later provide additional live evidence.

## Presentation cleanup

The two remaining German allocation-chart entries in the reference dashboard are corrected from
`Robotics · Acc` to `Robotik · Thes.`. Existing imported/copied dashboards remain user-owned and are
not overwritten automatically. Merge this presentation-only correction only if desired.

## Preserved boundaries

- portfolio payload schema 8 unchanged;
- REST portfolio schema 1 unchanged;
- Gateway health schema 6 unchanged;
- broker schemas 1/2/3 and v1.35.0 provider-scoped funding semantics unchanged;
- Comdirect provider acquisition, PhotoTAN bootstrap and authorized-cash semantics unchanged apart
  from the transport/maintenance resilience correction above;
- Trade Republic statement parsing/import behavior unchanged;
- DKB v1.35.0 anonymous FinTS raw/decoded response fingerprinting unchanged and DKB remains
  experimental/manual-only/non-live;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and
  no-plaintext fallback unchanged;
- no trading, order placement, automatic sell, transfer execution, payment or transaction-history
  capability.
