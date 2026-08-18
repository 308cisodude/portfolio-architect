# Privacy

Portfolio Architect processes portfolio values locally in Home Assistant and the
separate local Gateway App.

## DKB CSV handling

The adapter reads only the fields required to identify and value positions. It
ignores the DKB depot number, entry price, absolute gain, and relative gain.
Those fields are not copied into the canonical model, Home Assistant entities,
last-known-good storage, diagnostics, test fixtures, or release artifacts.

Supplemental sources receive neutral machine identities such as `dkb_1`; the
configured file path is not exposed as holding provenance.

## Secret handling

The Home Assistant-to-Gateway bearer token, Comdirect credentials, OAuth tokens,
and session data are never included in the calculated payload or diagnostics.
Gateway authentication material remains inside App-private storage.

DKB depot numbers are read only as transient in-memory comparison keys for same-depot export deduplication. They are never persisted, logged, included in payloads, diagnostics, fixtures, or entity attributes.

## Authorized-investment-cash privacy

The Gateway account-discovery and cash-policy screens are available only through
authenticated, admin-only Home Assistant Ingress. They present bounded masked
choices and use short-lived random browser-selection tokens rather than exposing
account IDs in HTML forms.

The selected Comdirect account identifier and non-secret authorization policy are
stored only in the Gateway App's private data directory with restrictive file
permissions. The public provider-neutral snapshot may contain these bounded
monetary facts:

- the booked balance of the selected account;
- eligible non-borrowed investment cash;
- the authorized investment cash amount;
- authorization policy and optional cap;
- the corresponding timestamp.

This deliberate disclosure lets Home Assistant explain why the amount available
for allocation differs from the selected account balance. IBANs, account numbers,
account IDs, account-holder names, account labels, transactions, credit limits,
raw bank response documents, and authentication material remain excluded from
entities, diagnostics, logs, and release fixtures.

## Decision-trace privacy

The Home Assistant integration keeps exactly two private provider-neutral decision
snapshots for Plan Delta & Decision Trace. The snapshots contain stable plan fund
IDs, fund display names, allocation status and drift, bounded recommendation and
execution values, policy finding keys/states, source counts, and evaluation
timestamps.

They do not contain ISINs, WKNs, source file paths, raw CSV/PDF/REST documents,
account identifiers, IBANs, transaction history, credentials, OAuth material, or
Gateway session data. Detailed plan-change attributes are excluded from Home
Assistant recorder history; only the bounded enum state may be retained according to
the user's recorder policy. Diagnostics omit monetary trace values and expose only
the state, timestamps, categories, counts, and changed fund IDs.

## v1.22 publication privacy gate

The public repository, complete reachable Git history in protected CI, and release artifacts are subject to a fail-closed privacy check. Raw broker statements/exports, unexpected screenshots, private key/container
formats, valid IBANs, and non-synthetic provider identity literals are rejected.
The checker reports only rule/location metadata and does not echo a detected exact
private literal.

Public security identifiers (for example ISINs), generic provider names, and wholly
synthetic fixtures remain permitted. The approved CSV allowlist is intentionally
small and explicit. A maintainer may supply additional known private literals from a
file outside the repository for local exact matching; the literal file itself is
rejected if placed inside the repository.

Release ZIPs are scanned by content rather than trusted merely because the source
tree was clean. This makes confidentiality a release invariant independent of the
existing reproducibility, checksum, manifest, and archive-safety controls.

## v1.23 provider identity boundary

Gateway health schema 6 adds only a bounded, non-secret machine provider identity
such as `comdirect`. The value identifies the provider implementation, not a person,
account, depot, customer, credential, source document, or bank-side resource.

Future DKB and Trade Republic Gateway Apps are required to preserve the same
boundary: provider-specific authentication state, account/depot identifiers, raw
source material, and import documents remain inside that provider App's private
storage or transient processing. The common Portfolio Architect REST and health
contracts receive only validated provider-neutral portfolio data plus the bounded
provider identifier needed for operational provenance.

## v1.34 target and presentation metadata

Stable `target_id` values identify user-defined portfolio roles. They are bounded application
identifiers, not bank-side account/depot/customer identifiers. The structural presentation model
is built only from already validated Portfolio Architect data and exposes target/holding identity,
source provenance IDs and bounded policy/actionability state.

The presentation model intentionally omits monetary values, quantities, proposed purchases,
account identifiers, source file paths, bearer tokens, OAuth/session material, DKB registration
material and raw provider documents. Existing dedicated entities remain authoritative for
monetary/action information under their established recorder/privacy boundaries.
