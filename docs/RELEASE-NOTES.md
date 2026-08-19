# Portfolio Architect 1.35.4

Version 1.35.4 is a narrow Comdirect Ingress usability and validation hotfix prepared on top of the
published v1.35.3 release.

## Human EUR cash-policy input

Live acceptance of **Keep cash reserve** exposed that the v1.35.2 form parser accepted only the
canonical machine representation with `.` as decimal separator. A German operator entering
`1024,00` therefore received a generic HTTP 400 and the previous `all_available` policy correctly
remained unchanged.

Version 1.35.4 keeps private policy state and REST payloads canonical, but makes the human-facing
Ingress boundary locale-tolerant. Both **Cap authorized cash** and **Keep cash reserve** accept common
EUR representations such as:

- `1024`, `1024.00`, `1024,00`;
- `1.024,00` and `1,024.00`;
- grouped forms using ordinary space, non-breaking space, narrow no-break space, straight apostrophe
  or typographic apostrophe.

The parser validates grouping strictly, permits at most two fractional digits, rejects signs,
exponent notation, mixed/malformed separators and non-finite/out-of-range values, and normalizes the
accepted value to a `Decimal` before the existing canonical private persistence boundary.

A single `.` or `,` followed by exactly three digits is treated as thousands grouping rather than as
a decimal separator because cash-policy amounts support at most two decimal places. Persisted policy
files remain locale-neutral and retain the existing strict canonical loader.

## Bounded validation UX

A malformed cash amount no longer drops the Ingress frame onto a browser-generated HTTP 400 page.
The cash-policy POST instead returns through a bounded relative redirect and displays fixed,
non-sensitive guidance on the App page. The rejected token is never reflected into the response, and
an invalid submission cannot overwrite the last valid private cash policy.

Structural form errors, CSRF failures, unsupported methods/content types and other security-relevant
request failures retain their established fail-closed HTTP handling.

## Long-running compatibility contracts

- v1.33.0 source-freshness and plan-schedule separation remains preserved; v1.35.4 does not change any configured freshness threshold.
- Recurring scheduling remains anchored to the latest valid Portfolio Architect evaluation.
- DKB live Gateway acquisition remains a later provider-specific milestone; DKB remains experimental, manual-only and non-live.
- v1.35.1 Comdirect session-maintenance resilience remains unchanged.
- This release does not move PDF parsing into Portfolio Architect; Trade Republic statement import/private diagnostics remain provider-side and unchanged.

## Preserved contracts

- `all_available`: unchanged;
- `capped`: still `min(eligible, cap)`;
- `retain`: still `max(eligible - retain_eur, 0)`;
- private policy schema 1/2 compatibility: unchanged;
- Portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported;
- broker schemas 1/2/3 and v1.35 provider-scoped funding semantics: unchanged;
- v1.35.3 native broker-editor menu-label correction: unchanged;
- v1.35.1 Comdirect session-maintenance resilience: unchanged;
- Trade Republic statement import/private diagnostics: unchanged;
- DKB remains experimental, manual-only and non-live;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and
  no-plaintext fallback: unchanged;
- No trading, order, transfer, payment, or transaction-history capability is introduced; no automatic-sell capability is added.
- no dashboard migration required;
- native dynamic portfolio presentation remains a separate later milestone.
- The historical `v1.19.0-rc2` brokerage probe remains excluded and is not promoted by this release.

See `docs/UPGRADE-1.35.4.md`.
