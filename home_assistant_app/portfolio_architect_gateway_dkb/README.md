# Portfolio Architect Gateway — DKB v1.28.1

Version 1.28.1 leaves the v1.28.0 DKB research boundary unchanged while aligning
the package with GitHub Actions runtime maintenance. The DKB App still does not
become a portfolio source. The App remains **experimental** and
**manual-only** and adds only a registration-gated anonymous FinTS 3.0 bank-parameter
(BPD) capability probe.

The probe is fixed to DKB's documented FinTS endpoint and bank code. It sends only
anonymous dialog-initialization segments and reduces the response to bounded,
non-private metadata: BPD version, observed parameter-segment identifiers, bounded
return codes, and whether the securities-holdings parameter segment `HIWPDS` is
advertised. The raw FinTS response is discarded.

## Registration gate

FinTS production access requires Portfolio Architect's **own** FinTS product
registration number. Enter that registration number in the admin-only App Web UI
before running the probe. Do not reuse a FinTS library/kernel registration number;
those identifiers are for internal testing rather than the user-facing application.

The product registration number is stored only in the App-private data directory
with mode `0600`. No DKB login name, PIN or TAN is requested or stored in v1.28.1.

## Deliberate limits

A positive `HIWPDS` result is only bank-level capability evidence. It does **not**
enable live DKB holdings, does not add the DKB Gateway to Portfolio Architect, and
does not prove that an authenticated user's UPD advertises the same capability.
Authenticated user-capability validation and DKB-App decoupled authentication are a
later gate.

The v1.28.1 DKB App sends no holdings request and contains no order, transfer,
payment, debit, transaction-history or other write-capable FinTS operation. Its
provider REST source remains fail-closed and cannot publish a DKB portfolio snapshot.

Verified HTTPS/private CA trust, bearer authentication, REST schema 1, health schema
6, provider identity `dkb`, and the existing `dkb` versus `dkb_csv` collision rules
remain unchanged. Upgrade in place to retain the App-private TLS trust root and
bearer token.
