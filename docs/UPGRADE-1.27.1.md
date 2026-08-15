# Upgrade to Portfolio Architect 1.27.1

Version 1.27.1 is the publishable form of the v1.27 HTTPS milestone. The v1.27.0
tag did not complete immutable publication because its tag-triggered Docker smoke
test lacked the Supervisor context that the production HTTPS bootstrap correctly
requires. No production integration or Gateway runtime behavior was changed to
resolve that publication failure.

Version 1.27.1 hardens the internal Gateway transport from bearer-authenticated
plaintext HTTP to **bearer-authenticated, certificate-verified HTTPS**. Portfolio
calculation, provider acquisition, entity IDs, payload schema 8, REST portfolio
schema 1 and Gateway health schema 6 are unchanged.

The upgrade order matters because a v1.27 Gateway App serves HTTPS-only on its
private REST port while a pre-v1.27 Portfolio Architect entry still contains an
HTTP endpoint.

## Required upgrade order

1. Update **Portfolio Architect through HACS to 1.27.1 first**.
2. Restart Home Assistant once and confirm the Portfolio Architect version entity
   reports `1.27.1`. Existing pre-v1.27 HTTP Gateway entries remain temporarily
   loadable solely for this migration window.
3. Update **Portfolio Architect Gateway — Comdirect** to 1.27.1 in place.
4. Wait for Supervisor discovery and confirm Portfolio Architect returns to
   healthy/live operation. The integration validates the App's new HTTPS endpoint
   with the existing bearer token and the Supervisor-distributed private CA before
   replacing the stored HTTP endpoint.
5. Update **Portfolio Architect Gateway — Trade Republic** to 1.27.1 if installed
   and configured as an additional REST source. Wait for the same automatic
   verified-HTTPS migration and healthy recovery.
6. Update **Portfolio Architect Gateway — DKB** to 1.27.1 if installed. The DKB App
   remains an experimental manual-only fail-closed shell; no live DKB acquisition
   is introduced.

Do **not** update a Gateway App to 1.27.1 before the Home Assistant integration.
Do not edit `.storage`, copy CA files manually, disable certificate verification,
or change the Gateway bearer token merely for this upgrade. **Do not reauthenticate Comdirect**
solely because of this transport migration.

## Private PKI and trust distribution

Each official Gateway App creates a per-installation ECDSA private CA and HTTPS
server certificate under its App-private `/data/gateway/tls` directory. The CA and
server private keys never leave the App. The certificate is bound to the
Supervisor-assigned internal App hostname.

After HTTPS is listening, the App publishes only the public CA certificate,
its SHA-256 fingerprint, provider ID and internal endpoint identity through Home
Assistant Supervisor discovery. The bearer token is never included in discovery.
Portfolio Architect validates HTTPS with hostname checking and the discovered CA,
then keeps the existing bearer authentication as an independent application-layer
control.

The CA is intentionally long-lived across normal App upgrades/restarts. Leaf
certificates can be renewed under the same CA. If existing CA state is incomplete
or invalid, the App fails closed rather than silently generating a new trust root.
If a previously secured Portfolio Architect source receives discovery with a
different CA fingerprint, automatic trust replacement is refused.

## New installations and additional Gateways

A newly discovered Comdirect Gateway can start the Portfolio Architect setup flow.
The user still enters the existing Gateway bearer token and Portfolio configuration
directory; Supervisor discovery supplies the HTTPS endpoint and public CA.

A newly discovered Trade Republic or future functional DKB Gateway is **not**
silently added to an existing portfolio. Portfolio Architect asks for explicit
confirmation and that Gateway's bearer token, validates health schema 6 plus the
live snapshot/integrity contract, and only then adds the provider as an additional
source. Existing source-count/provider-collision and DKB-CSV exclusivity checks
remain in force.

## Verify the migration

After each configured Gateway migration:

1. Confirm the Runtime health section returns to `Source healthy`, `Gateway status:
   OK`, `Operating mode: Live`, and `Snapshot verified` as applicable.
2. Download Portfolio Architect diagnostics and confirm the primary REST adapter
   reports `transport_security: verified_https`, `custom_ca_configured: true`, and
   a bounded `tls_ca_sha256` fingerprint. Configured supplemental REST Gateways
   should report the same transport state in their public diagnostic entries.
3. Restart the migrated Gateway App once. Its CA fingerprint must remain unchanged
   and Portfolio Architect must recover without any certificate-trust action.
4. No dashboard YAML migration is required.

## Failure behavior

A certificate chain, hostname, CA fingerprint, or HTTPS connection failure is a
source failure. Portfolio Architect does not retry the same source over plaintext
HTTP. Existing atomic all-configured-source and last-known-good behavior remains
authoritative: a matching trusted LKG may remain informationally visible while new
investment actionability fails closed.

No Comdirect PhotoTAN, account reselection, cash-policy migration, Trade Republic
statement re-import, or Portfolio Architect source recreation is required solely
because of v1.27.1.
