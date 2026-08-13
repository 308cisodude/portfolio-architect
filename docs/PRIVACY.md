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
