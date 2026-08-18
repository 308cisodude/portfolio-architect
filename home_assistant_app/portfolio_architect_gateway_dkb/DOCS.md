# Portfolio Architect Gateway — DKB v1.34.0

Version 1.34.0 is package alignment for the Home Assistant-side generic target and presentation-
model milestone and preserves the live-accepted v1.31.2 registration-gated anonymous FinTS 3.0 BPD
capability-probe plus the shared provider-diagnostics policy. The current live probe has reached DKB and returned bounded product-registration
rejection evidence; no DKB acquisition capability is added. The DKB App remains **experimental**, **manual-only** and non-live
as a Portfolio Architect source.

The probe stays fixed to DKB's documented FinTS endpoint and bank code. It sends only
anonymous dialog-initialization segments and persists only bounded, non-private evidence.
Raw FinTS response content is discarded after bounded diagnostic extraction and correlation fingerprinting.

## Registration gate

FinTS production access requires Portfolio Architect's own issued product registration
identity. The live-accepted contract remains:

- the ID must contain exactly 25 alphanumeric characters;
- the complete value is sent exclusively as the product designation in `HKVVB`;
- the separate bounded product-version field remains distinct; and
- the ID remains stored only in App-private mode-`0600` state.

The Web UI applies the same exact-length requirement. An in-place upgrade retains an
already configured valid 25-character registration identity.

## Ingress-safe Web UI

Registration-storage and probe POST actions now redirect relatively to the App root. They
therefore remain inside the Home Assistant Ingress namespace instead of navigating the
iframe to Home Assistant's absolute `/` dashboard.

## Persisted sanitized probe outcomes

Successful BPD evidence contains only BPD version, observed parameter-segment identifiers,
bounded four-digit return codes, bounded sanitized `HIRMG`/`HIRMS` return-message text,
decoded-response SHA-256/byte count, timestamp and whether `HIWPDS` is advertised.

Expected unsuccessful attempts also persist a bounded outcome so reopening the Web UI does
not falsely return to `ready / not probed`. A valid FinTS response with `HIRMG`/`HIRMS`
return codes but no BPD is shown as `bank_rejected`; its recognized return codes and bounded
sanitized operator-message text survive. The configured product ID is redacted if echoed,
arbitrary/unknown segment payload is not persisted, and a decoded-response SHA-256/byte count
allows correlation without retaining the raw response. HTTP, transport and strict-protocol
failures use separate bounded states.

A newly issued product registration that has not yet propagated to an institute is only one
possible explanation for `bank_rejected`. The App does not assert that interpretation from
an unknown return code.

## Deliberate limits

A positive `HIWPDS` result is only bank-level capability evidence. It does **not** enable
live DKB holdings and does not prove that an authenticated user's UPD advertises the same
capability. Authenticated user-capability validation and DKB-App decoupled authentication
remain later gates.

The v1.34.0 DKB App requests no DKB login name, PIN or TAN and sends no holdings, balance,
transaction, order, transfer, payment, debit or transaction-history business transaction.
Its provider REST source remains fail-closed and cannot publish a DKB portfolio snapshot.

Verified HTTPS/private CA trust, bearer authentication, REST schema 1, health schema 6,
provider identity `dkb`, and the existing `dkb` versus `dkb_csv` collision rules remain
unchanged. Upgrade in place to retain App-private state.
