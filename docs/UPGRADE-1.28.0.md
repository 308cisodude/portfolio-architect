# Upgrade to Portfolio Architect 1.28.0

Version 1.28.0 begins the DKB live-acquisition path with a deliberately narrow,
registration-gated **anonymous FinTS capability probe**. It does not yet enable live
DKB portfolio acquisition.

The established Portfolio Architect calculation engine, payload schema 8, REST
portfolio schema 1, Gateway health schema 6, verified-HTTPS/private-PKI transport,
bearer authentication, multi-source atomicity and LKG behavior remain unchanged.
Comdirect's live-proven v1.27.4 OAuth/session-maintenance fix and Trade Republic's
local statement-import behavior are unchanged.

## Upgrade order

1. Update **Portfolio Architect** through HACS to 1.28.0.
2. Restart Home Assistant once and confirm the Portfolio Architect version entity
   reports `1.28.0`.
3. Update **Portfolio Architect Gateway — Comdirect** in place. Do not remove App
   data or reauthenticate solely because of this release.
   Do not reauthenticate Comdirect solely because of the v1.28.0 upgrade when the current session is healthy.
4. Update **Portfolio Architect Gateway — Trade Republic** in place if installed.
5. Update **Portfolio Architect Gateway — DKB** in place if installed. The App
   remains experimental and `manual_only`.
6. Confirm the private-CA fingerprints for already-secured Gateway sources remain
   unchanged and the existing live providers recover normally.

No dashboard YAML migration is required.

## DKB FinTS capability-probe milestone

The DKB App now contains a minimal provider-specific FinTS 3.0 probe fixed to:

- endpoint: `https://fints.dkb.de/fints`;
- bank code: `12030000`;
- anonymous customer identifier: `9999999999`;
- protocol version: FinTS 3.0.

The App sends only anonymous dialog-initialization segments (`HNHBK`, `HKIDN`,
`HKVVB`, `HNHBS`). It does **not** send a holdings request or any account,
transaction, order, transfer, payment or debit business transaction.

The probe reduces the bank response to bounded metadata and discards the raw FinTS
response. Persisted probe state contains only:

- BPD version;
- observed parameter-segment identifiers;
- bounded four-digit return codes;
- probe timestamp; and
- whether the securities-holdings parameter segment `HIWPDS` is advertised.

## FinTS product registration is required

Do not run the probe with another product's registration number. FinTS production
access requires the registration number issued for the **Portfolio Architect**
application itself; a FinTS library/kernel registration may be used only for
internal testing and must not be reused as the production application identity.

The DKB App Web UI therefore starts in `registration_required` state. After the
project receives its own FinTS product registration number, enter it in the
admin-only Ingress page. The value is validated, stored only in App-private state,
and written with mode `0600`.

Version 1.28.0 does not ask for or persist a DKB login name, PIN or TAN.

## Interpretation gate

A positive bank-level BPD result such as `HIWPDS advertised: yes` is **not** enough
to enable live holdings acquisition. It is only evidence that the DKB bank
parameters advertise a securities-holdings transaction family.

Before a later release may implement holdings acquisition, Portfolio Architect must
still establish a separate authenticated DKB FinTS dialog and validate the
**authenticated user's** capabilities/UPD, including DKB-App decoupled
authentication behavior. Provider-specific authentication must remain inside the
DKB Gateway App.

If the necessary read-only holdings capability is not available for the authenticated
user, the Gateway must remain fail-closed. A future local DKB securities-document
import may then be considered instead of scraping DKB web/mobile interfaces.

## Existing DKB CSV source

The established DKB CSV importer remains provider identity `dkb_csv`; the DKB
Gateway remains provider identity `dkb`. Version 1.28.0 does not migrate or replace
DKB CSV and does not add the DKB Gateway as an active portfolio source. Existing
scope-collision and discovery-suppression rules remain authoritative, preventing
silent double counting.

## Security boundary

The capability probe:

- uses the fixed DKB HTTPS hostname and path with normal certificate and hostname
  verification;
- does not accept a user-configurable URL;
- does not use ambient HTTP proxy handling or follow redirects;
- bounds HTTP/base64/decoded response sizes and FinTS segment counts;
- understands FinTS escaping and binary-field lengths before segment splitting;
- persists no raw bank response;
- adds no FinTS library/runtime dependency and therefore does not import a broad
  transfer/payment/order API surface into the DKB App; and
- keeps the provider REST snapshot fail-closed because no DKB acquisition path
  exists yet.

The normal v1.27 private-PKI HTTPS boundary between the Gateway and Home Assistant
is separate from the DKB App's outbound verified TLS connection to DKB.

## First capability-probe acceptance

After the project's own FinTS registration number has been issued:

1. Start **Portfolio Architect Gateway — DKB** manually.
2. Open its admin-only Web UI.
3. Enter the Portfolio Architect FinTS product registration number.
4. Run **Probe DKB FinTS capabilities**.
5. Record only the sanitized result: BPD version, whether `HIWPDS` is advertised,
   observed parameter-segment identifiers, and bounded return codes.
6. Do not configure the DKB Gateway as a Portfolio Architect source; its portfolio
   endpoint remains intentionally unavailable.

A positive `HIWPDS` result moves the project to the authenticated UPD/authentication
research gate. A negative result stops live-holdings implementation until another
supported read-only acquisition design is identified.

## Public reference points

The v1.28.0 probe boundary was prepared against the public provider/standard-owner
documentation available at release preparation time:

- DKB electronic-banking parameters and FinTS 3.0 endpoint:
  `https://www.dkb.de/geschaeftskunden/electronic-banking`
- FinTS product-registration process:
  `https://www.fints.org/de/hersteller/produktregistrierung`
- FinTS product-registration FAQ, including the rule that the user-facing product
  requires its own registration identity and library/kernel registrations are not
  production application identities:
  `https://www.fints.org/de/hersteller/faq-produktregistrierung`

These public references do not themselves prove DKB depot-holdings support for a
specific customer relationship; that is precisely why the BPD and later authenticated
UPD gates are kept separate.
