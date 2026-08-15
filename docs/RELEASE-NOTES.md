# Portfolio Architect 1.27.1

Version 1.27.1 is the publishable Gateway transport-security milestone. Its
production TLS, provider-acquisition and portfolio behavior are unchanged from the
v1.27.0 tag; only release/version metadata is advanced to 1.27.1: the patch corrects immutable-release CI so the tag-triggered provider-shell
Docker smoke test has the same authenticated Supervisor context as protected PR
validation. Official provider
Gateway Apps now serve their private Portfolio Architect REST API over verified
HTTPS while retaining the existing dedicated bearer token as an independent
application-layer authentication control.

The release deliberately changes transport and trust lifecycle only. Portfolio
payload schema 8, REST portfolio schema 1, Gateway health schema 6, entity IDs,
provider acquisition, portfolio calculation, authorized-cash semantics, source
atomicity, LKG behavior, date presentation, and the read-only/no-trading boundary
remain unchanged.


## Immutable-publication workflow correction

The v1.27.0 tag reached the immutable-release workflow with the completed HTTPS
implementation, but publication stopped because `release.yml` still used the old
standalone v1.26 provider-shell smoke test. The production v1.27 Gateway correctly
refused to bootstrap hostname-bound TLS without `SUPERVISOR_TOKEN` and Supervisor
`/addons/self/info`.

Version 1.27.1 changes no production TLS or Gateway runtime logic for this
incident; release/version metadata is aligned to 1.27.1. The release workflow now uses the same bounded mock Supervisor, ephemeral
Supervisor token, `supervisor` network alias and hostname-verified private-CA TLS
handshake as protected PR validation. A regression contract requires the two smoke
step bodies to remain identical.

## Per-Gateway private PKI

Each official Gateway App creates and persists a per-installation ECDSA P-256
private CA plus a server certificate under App-private `/data/gateway/tls` state.
The leaf certificate is issued for the Supervisor-assigned internal App hostname.
The CA is long-lived across normal App upgrades and restarts; leaf certificates can
renew under the same CA.

The App validates its CA/key/leaf set before serving. Existing incomplete or invalid
CA state fails closed rather than being silently replaced with a new trust root.
Private keys remain inside the provider App and are never published to Home
Assistant state, diagnostics, REST responses, or Supervisor discovery.

## Supervisor-distributed public trust

After its HTTPS listener is live, each Gateway publishes a bounded Supervisor
discovery record containing only:

- transport-discovery schema version 1;
- bounded provider ID;
- Supervisor internal hostname, port and fixed portfolio path;
- the public CA certificate; and
- the CA certificate SHA-256 fingerprint.

The Gateway bearer token is not part of discovery. The Apps retain
`hassio_api: false`; only the Supervisor endpoints available to Apps for self-info
and discovery are used.

## Verified Home Assistant client transport

Portfolio Architect stores the discovered public CA with the matching REST source
and creates a certificate-verifying TLS client context with hostname checking and a
minimum of TLS 1.2. For Supervisor-discovered private CA trust, the context trusts
that CA explicitly rather than widening trust with the operating-system public root
store.

The existing local-only DNS validation and request-scoped DNS pinning remain in
place. The original hostname stays in the request URL, so HTTP Host, TLS SNI and
certificate-name validation all refer to the same validated identity. Redirects,
ambient proxies, cookies, response-size bounds, bearer authentication and GET-only
API restrictions remain unchanged.

## Fail-closed automatic migration

Existing v1.26.x REST sources are not rewritten merely because v1.27.1 is installed.
The Home Assistant integration must be updated first; it temporarily keeps legacy
HTTP entries loadable while their matching Gateway Apps are upgraded.

When an upgraded Gateway publishes discovery, Portfolio Architect matches it to an
existing source by network identity and, for supplemental Gateways, provider ID. It
then validates the discovered HTTPS health endpoint with the existing bearer token
and private CA **before** atomically replacing the stored HTTP endpoint and trust
material. Once migrated, there is no automatic plaintext fallback.

For an already secured source, a different discovered CA fingerprint is treated as
a trust change and automatic replacement is refused.

New Comdirect installations can be initiated from verified Supervisor discovery.
New supplemental providers require explicit user confirmation and their existing
bearer token before the normal health/snapshot/integrity/provider-collision checks
can add them to the portfolio.

## Compatibility and security invariants

- Portfolio payload schema 8: unchanged.
- REST portfolio schema 1: unchanged.
- Gateway health schema 6: unchanged; health schemas 1–5 remain supported where
  previously supported.
- Existing Home Assistant entity IDs / unique IDs: unchanged.
- Comdirect OAuth/session/PhotoTAN/account selection/authorized cash: unchanged.
- Trade Republic statement import and persisted snapshot: unchanged; this release
  does not move PDF parsing into Portfolio Architect.
- DKB Gateway remains experimental/manual-only/fail-closed with no live acquisition
  path. DKB live Gateway acquisition remains a later provider-specific milestone.
- v1.26.6 bounded unavailable-source diagnostics and v1.26.7 cold-restart snapshot
  identity guarantees remain unchanged.
- No trading, order, transfer, payment, or transaction-history capability is added.
- The historical experimental `v1.19.0-rc2` brokerage diagnostics/fee-probe work
  remains separate and is not promoted by this release.

The required upgrade sequence is documented in `docs/UPGRADE-1.27.1.md`. No
reference-dashboard YAML migration is required.
