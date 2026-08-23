# Provider diagnostic evidence policy

Portfolio Architect treats provider diagnostics as **classified evidence**, not as a general-purpose copy of upstream traffic. Provider failures can carry useful operational hints, but the diagnostic boundary must remain narrower than the provider protocol itself.

## Common contract

Every provider App must follow these rules:

- retain only bounded, explicitly classified evidence needed to understand a failure;
- keep persisted diagnostics App-private with mode `0600` state and no cross-provider sharing;
- never persist raw upstream response bodies merely because parsing failed;
- never persist credentials, bearer/OAuth tokens, cookies, PIN/TAN material, account/depot IDs, customer identifiers, portfolio quantities or monetary values as diagnostic text;
- never expose private provider diagnostics through the public portfolio REST endpoint;
- keep Home Assistant Ingress form actions and redirects inside the App namespace;
- use provider-specific allowlists/redaction rather than a generic "log whatever the bank returned" mechanism;
- bound diagnostic counts, text lengths and state size;
- replace obsolete failure evidence after a successful operation instead of building an unbounded historical log archive; and
- keep diagnostics advisory: they must not silently change acquisition, actionability, trading or authentication semantics.

A response fingerprint may be retained only when the provider-specific data classification makes that safe and useful. A fingerprint is not automatically harmless: for a private user-supplied document it can itself become a persistent document identifier.

## DKB

The anonymous FinTS BPD probe has no customer login, PIN/TAN, account or holdings request. Its v1.31.2 diagnostic state therefore retains only bounded `HIRMG`/`HIRMS` return codes and sanitized return-message text, plus decoded-response SHA-256/byte count for correlation. The configured 25-character FinTS product registration identity is redacted if echoed. Raw FinTS response bytes and arbitrary segment payload are discarded.

A successful BPD response replaces an earlier failure state. DKB CSV acquisition is active through the experimental auto-starting DKB Gateway. v1.47.0 adds independent Girokonto cash CSV evidence but persists only normalized balance/date state; account identifiers, transaction rows, counterparties, references and raw cash CSV bytes are not retained or fingerprinted. Normal age-based availability remains unchanged and authenticated FinTS remains disabled until later authenticated user-capability gates are separately implemented and accepted.

## Comdirect

Comdirect traffic is authenticated and therefore has a stricter privacy boundary. The live Gateway health/runtime keeps bounded failure classes, recommended action and provider-safe status reason; refresh/session logs use exception class, HTTP status/operation or the already-bounded OAuth rejection reason rather than raw response content.

The Comdirect App already uses relative Ingress redirects. v1.32.0 adds regression coverage that this boundary and the sanitized runtime-error contract stay intact. Authenticated upstream response fingerprints or free-text response retention are **not** enabled by this foundation release.

## Trade Republic

The Trade Republic source is an operator-supplied private `DEPOTAUSZUG` PDF. The document is parsed in memory and is never persisted. v1.32.0 also persists only the latest bounded import outcome (`accepted`, `rejected`, or `internal_error`) and an allowlisted operator message in App-private state so an import failure survives Web UI reopen/App restart.

Parser/form error text is retained only when it matches a controlled allowlist. Unexpected exception text is replaced by a generic bounded rejection message, preventing future parser changes from accidentally persisting document-derived names, IBANs or other private content. Persisted diagnostic state is revalidated on every read; malformed or tampered message/timestamp content fails closed to a fixed internal-error notice and is never echoed.

Trade Republic intentionally does **not** retain a PDF SHA-256 or raw document-size fingerprint as diagnostic state. The uploaded document itself is private evidence, so persistent document identity is unnecessary for troubleshooting and would weaken data minimisation.

## New provider requirement

Any future provider implementation must document its diagnostic data classification before adding new persisted evidence. Tests must inject synthetic secrets/private identifiers into unexpected error paths and prove that they cannot escape into logs, persisted diagnostic state, Home Assistant entities/diagnostics, Gateway health or public REST responses.
