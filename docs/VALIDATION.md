# v1.27.0 validation

Portfolio Architect v1.27.0 retains the complete v1.26.7 cold-restart integrity,
v1.26.6 unavailable-source, v1.26 multi-provider atomic-LKG, provider-App,
publication/privacy and reproducible-release regression pipeline while adding
verified Gateway HTTPS transport contracts.

The release-specific contracts must prove:

- integration and all three official provider App package versions align with
  1.27.0;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- each official App serves the common Gateway API with a TLS certificate/key and
  advertises the `portfolio_architect` Supervisor discovery service;
- App containers retain least privilege (`hassio_api: false`, no host networking or
  host REST-port mapping) while using the allowed Supervisor self-info/discovery
  endpoints;
- each App generates a private ECDSA CA/leaf set in App-private storage, uses the
  Supervisor internal hostname as the server-certificate identity, protects private
  files with mode 0600, and preserves the CA across leaf renewal;
- incomplete or invalid existing CA state fails closed rather than silently
  replacing the trust anchor;
- Supervisor discovery contains only bounded endpoint/provider identity, the public
  CA certificate and its SHA-256 fingerprint, never Gateway bearer tokens or private
  keys;
- Portfolio Architect validates the discovery schema, provider ID, hostname,
  port/path, public CA and fingerprint before using them;
- Supervisor-discovered private CA transport uses a TLS client context with
  certificate verification, hostname checking, minimum TLS 1.2 and private-CA-only
  trust;
- local/private address validation and request-scoped DNS pinning remain active for
  HTTPS and preserve the original hostname for Host/SNI/certificate verification;
- no `ssl=False`, `verify=False`, redirect, proxy or cookie bypass is introduced;
- config-entry schema version 9 tolerates legacy HTTP only for in-place migration
  and reauthentication, while new/reconfigured REST sources require HTTPS;
- an existing legacy source is rewritten only after its discovered HTTPS health
  endpoint validates with the existing bearer token and expected provider identity;
- a different CA fingerprint for an already secured source is never accepted as an
  automatic trust replacement;
- a newly discovered supplemental provider requires explicit user confirmation,
  bearer authentication, health-schema-6 identity, live snapshot integrity and the
  existing provider/source collision rules before being added;
- once a source is HTTPS, transport failures fail closed/LKG and never trigger an
  automatic plaintext downgrade;
- v1.26.7 quantity/cache/HTTP-validator tests and v1.26.6 unavailable-source tests
  remain green;
- Comdirect OAuth/session/PhotoTAN/account/cash behavior and Trade Republic
  statement-import behavior remain unchanged;
- the common REST API remains authenticated GET-only and no provider App gains
  trading/order/transfer/payment/transaction-history capability;
- source and built artifacts pass publication/privacy gates; and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

Live acceptance starts from the healthy, live-accepted v1.26.7 three-source /
three-provider installation. Update the Home Assistant integration first, restart
Home Assistant, then update configured Gateway Apps one at a time. Each source must
recover through verified HTTPS without manual CA copying, bearer-token replacement,
provider reconfiguration or a plaintext fallback. A normal Gateway restart must
preserve the same CA fingerprint.
