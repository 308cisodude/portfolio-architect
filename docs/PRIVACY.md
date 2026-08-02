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
