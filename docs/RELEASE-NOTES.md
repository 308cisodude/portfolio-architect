# Portfolio Architect 1.27.4

Version 1.27.4 fixes a timing-dependent Comdirect OAuth session-lifetime defect
identified during live acceptance after the v1.27 HTTPS line.

Portfolio acquisition intentionally runs on a fixed 15-minute cadence. Comdirect's
secondary access token can still be usable at an early portfolio refresh while the
associated refresh-session lifetime continues to age. In the reproduced live case,
a PhotoTAN bootstrap completed shortly before an existing scheduled refresh; that
refresh reused the still-valid access token and therefore did not renew the OAuth
chain. The following 15-minute portfolio cycle then arrived after the persisted
refresh session had already been rejected, causing `reauthentication_required`.

A controlled phase-shift test confirmed the diagnosis: after authenticating just
after a scheduled refresh, four subsequent 15-minute refreshes completed normally.
The defect was therefore not an HTTPS, bearer-token, snapshot-integrity, or
portfolio-calculation failure.

## Provider-owned session maintenance

Comdirect OAuth/session lifetime is now maintained inside the Comdirect Gateway App
on a dedicated five-minute maintenance cadence, independent of portfolio snapshot
acquisition.

The maintenance loop:

- calls only the existing Comdirect token-maintenance path;
- performs no depot, position, instrument, balance, transaction, order, payment, or
  transfer request;
- is a no-op while the current access token remains safely usable;
- refreshes the existing OAuth chain before its short-lived renewal window can be
  missed merely because of portfolio-poll timing;
- persists successful replacement OAuth state through the existing atomic private
  session store;
- leaves PhotoTAN bootstrap unchanged;
- classifies transient OAuth transport/service failures as retryable operational
  failures rather than reauthentication; and
- fails closed when Comdirect conclusively rejects the persisted refresh session.

After one conclusive refresh-session rejection, the running Gateway latches that
reauthentication requirement locally until an interactive bootstrap succeeds. This
avoids repeatedly submitting the same rejected refresh token every scheduled cycle.
A bounded non-secret reason (`invalid_grant`, `invalid_token`, `http_401`, or
`http_403`) is written to the Gateway log when that rejection is first classified.

The same provider-specific session maintenance is wired into both the Home Assistant
Comdirect App runtime and the standalone Comdirect Gateway service. The common
provider-neutral Gateway contract remains free of OAuth assumptions.

## AI-assisted development disclosure

`AI_POLICY.md` now documents an additional defense-in-depth practice used for
material release candidates: a separate AI system may perform an independent
second-opinion review with explicit security focus. The policy also states the
scope limits of such review and makes clear that it is not a security certification
and has no merge, tagging, publication, or deployment authority.

## Security and compatibility

- Portfolio payload schema 8: unchanged.
- REST portfolio schema 1: unchanged.
- Gateway health schema 6: unchanged; schemas 1–5 remain supported where previously supported.
- v1.27 private-PKI hostname-verified HTTPS and bearer authentication: unchanged.
- No automatic plaintext fallback is introduced.
- Comdirect PhotoTAN bootstrap, account selection, authorized cash, portfolio
  normalization, and provider request allowlists: unchanged.
- The portfolio refresh cadence remains independently configurable; the new OAuth
  maintenance cadence is provider-owned and is not a portfolio freshness policy.
- `request_timeout_seconds` behavior and defaults are unchanged by this release.
- Trade Republic statement import: unchanged; this release does not move PDF parsing into Portfolio Architect.
- DKB Gateway remains experimental/manual-only/fail-closed with no live acquisition.
- DKB live Gateway acquisition remains a later provider-specific milestone.
- Portfolio calculations, source atomicity, LKG behavior, entity identities, and
  dashboard behavior are unchanged.
- No trading, order, transfer, payment, or transaction-history capability is added.
- The historical experimental `v1.19.0-rc2` brokerage diagnostics/fee-probe work remains separate and is not promoted by this release.

The upgrade path is documented in `docs/UPGRADE-1.27.4.md`. No dashboard YAML
migration is required.
