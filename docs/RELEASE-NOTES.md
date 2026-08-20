# Portfolio Architect 1.37.0

Portfolio Architect 1.37.0 introduces the shared Gateway human-input validation foundation that was deliberately deferred from the v1.36 presentation line. The milestone centralizes reusable human-numeric parsing mechanics while keeping provider and field semantics explicit and separate.

## Shared human-input validation

A new mirrored `human_input.py` Gateway helper provides opt-in bounded primitives for:

- EUR/money values;
- percentages;
- quantities; and
- bounded integers.

Human numeric parsing accepts only validated locale-style syntax and returns canonical typed `Decimal`/integer values. Common German/English decimal and grouping conventions are supported where the primitive can interpret them safely. Ambiguous quantity syntax such as a lone `1,234` is rejected rather than guessed when it could mean either a decimal quantity or thousands grouping.

Rejected input produces bounded guidance that never echoes the raw rejected token. Signs, exponent notation, currency text, unsafe grouping and overlong input are rejected. Common bounds are enforced before provider/field-specific semantics.

The helper is deliberately opt-in. Protocol identifiers, registrations, credentials, tokens and exact IDs do not pass through locale numeric normalization. The DKB FinTS product-registration path and Trade Republic statement import remain on their existing provider-specific exact-validation paths.

## Comdirect first production consumer

The existing Comdirect **Cap authorized cash** and **Keep cash reserve** form fields now use the shared EUR primitive instead of a private duplicate parser. The live-proven v1.35.4 behavior is preserved:

- `1024`, `1024.00`, `1024,00`;
- `1.024,00` and `1,024.00`;
- validated space/NBSP/narrow-NBSP/apostrophe grouping.

Private persisted policy state remains canonical and locale-neutral. Invalid input is still parsed before any save, so the previous valid private policy remains untouched and the established bounded Ingress feedback remains unchanged.

## Preserved behavior and security boundaries

Historical experimental `v1.19.0-rc2` brokerage-diagnostic work remains excluded and is not promoted by this release.

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported;
- broker schemas 1/2/3 runtime compatibility: unchanged;
- presentation schema 2 and v1.36.1 dynamic dashboard behavior: unchanged;
- provider-scoped authorized cash, retained-cash mathematics and exact directed funding topology: unchanged;
- v1.35.1 Comdirect OAuth/session-maintenance resilience: unchanged;
- Trade Republic local/private statement import: unchanged; this release does not move PDF parsing into Portfolio Architect and no cash or transaction-history parser is added;
- DKB remains experimental, manual-only and non-live; DKB live Gateway acquisition remains a later authenticated milestone;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- No trading, order, transfer, payment, or transaction-history capability is added; no automatic-sell capability is added.


The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, source timestamps remain evidence-only freshness inputs, and v1.37.0 does not change any configured freshness threshold.

The dashboard is unchanged from live-accepted v1.36.1; no Lovelace YAML replacement is required for v1.37.0.
