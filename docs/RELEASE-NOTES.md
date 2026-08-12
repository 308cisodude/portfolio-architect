# Portfolio Architect 1.19.1

Version 1.19.1 is a focused maintenance release for the Gateway-side Authorized
Cash Policy introduced in 1.19.0.

## Fixed policy transition

The 1.19.0 Ingress form could retain the previous EUR cap when an operator
switched from `capped` to `all_available`. The browser then submitted both
`mode=all_available` and the stale cap. The 1.19.0 server rejected that
combination with HTTP 400, leaving the previously persisted capped policy safely
in place until the cap field was manually cleared.

Version 1.19.1 changes the boundary so that policy semantics, not browser field
state, decide correctness. For an `all_available` submission, the server ignores
any irrelevant cap value and persists the canonical policy with no cap. A form
submission that omits the disabled cap field is accepted as well.

Capped mode remains strict: a valid canonical non-negative EUR cap is required.
The persisted-state loader is also unchanged in principle and still rejects a
malformed on-disk `all_available` policy that contains a cap.

## Ingress usability

The Ingress page now clears and disables the cap control whenever **All eligible
cash** is selected, and enables/requires it for **Cap eligible cash**. This
client-side behavior is only a usability aid; the server-side parser remains the
authoritative validation and normalization boundary.

## Compatibility

Portfolio calculations and allocation behavior are unchanged. Payload schema 8,
REST schema 1, Gateway health schema 5, entity IDs, unique IDs, authentication
state, selected-account state, and the provider-neutral cash metadata contract
are unchanged.

No trading, order, transfer, payment, or transaction-history capability is added.
## Experimental branch note

The historical `v1.19.0-rc2` tag remains a separate experimental brokerage-
diagnostics branch. Stable 1.19.1 does **not** promote those experimental diagnostics.
