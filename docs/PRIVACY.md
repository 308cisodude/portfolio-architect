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

## Investment-reserve privacy

The Gateway account-discovery screen is available only through authenticated,
admin-only Home Assistant Ingress. It presents bounded masked choices and uses
short-lived random browser-selection tokens rather than exposing account IDs in
HTML forms.

The selected Comdirect account identifier is stored only in the Gateway App's
private data directory with restrictive file permissions. The public Portfolio
Architect REST snapshot may contain only:

- the usable EUR investment-reserve amount;
- the reserve timestamp.

IBANs, account numbers, account IDs, account-holder names, account labels,
transactions, credit limits, and raw balance documents are not exposed to Home
Assistant entities, diagnostics, logs, or release fixtures.

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

## Experimental brokerage-diagnostic data

Version 1.19.0-rc2 keeps probe state exclusively in Gateway process memory. The
Ingress page uses random short-lived tokens for private depot and venue identifiers.
The sanitized result may contain public instrument/venue labels and cost values, but
not depot IDs, venue IDs, customer/account metadata, OAuth/session material,
request headers, upstream links, inducement objects, or raw responses.

Clearing the probe or restarting the App removes the result. It is not written to
App-private storage, Home Assistant storage, recorder history, diagnostics, the
portfolio snapshot, or the Gateway health document.
