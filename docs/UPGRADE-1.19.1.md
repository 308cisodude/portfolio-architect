# Upgrade to Portfolio Architect 1.19.1

Version 1.19.1 is a focused Gateway Ingress maintenance release for the
Authorized Cash Policy introduced in 1.19.0.

## What is fixed

In 1.19.0, switching from **Cap eligible cash** to **All eligible cash** could
return HTTP 400 if the browser still submitted the previous cap value. The
policy itself remained safe because the rejected request was not persisted, but
the operator had to clear the cap field manually and submit again.

Version 1.19.1 makes the server authoritative for this transition:

- `all_available` ignores an irrelevant submitted cap and persists the canonical
  policy with `cap_eur = None`;
- a browser that omits the disabled cap field is accepted;
- capped mode still requires a valid canonical non-negative EUR cap;
- persisted policy files remain strictly validated and malformed
  `all_available` state containing a cap is still rejected.

The Ingress page also clears and disables the cap control when **All eligible
cash** is selected. This is a usability improvement only. Correctness and
validation remain server-side.

## Upgrade

1. Update the Portfolio Architect Gateway App to 1.19.1 through **Settings → Apps**.
2. Update Portfolio Architect to 1.19.1 through HACS.
3. Restart Home Assistant after the HACS update.
4. Existing Gateway authentication, selected account, API token, cached snapshot,
   and cash policy are preserved by the in-place App update.

No reauthentication or account reselection is expected unless Comdirect
independently requires it.

## Compatibility

No portfolio-calculation, entity-ID, payload, REST, or Gateway-health schema is
changed. The integration continues to accept the existing REST schema 1 cash
contract. Gateway App 1.19.0 remains protocol-compatible, while 1.19.1 contains
the corrected policy-transition workflow.

## Acceptance check

For an end-to-end check, temporarily configure a small cap and wait for the next
Portfolio Architect poll. Confirm that authorized investment cash and estimated
cash outlay respect the cap. Then switch back to **All eligible cash** without
manually clearing the previous cap. The save must succeed and, after the next
normal poll, Portfolio Architect must again expose the full eligible amount.
