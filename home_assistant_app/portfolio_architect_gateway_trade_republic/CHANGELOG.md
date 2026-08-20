# Changelog

## 1.36.1

- Package/version alignment for the Portfolio Architect v1.36.1 Home Assistant dashboard hotfix; statement import and private diagnostics are unchanged.
- No Trade Republic cash acquisition, transaction-history, transfer or trading capability is added.

## 1.36.0

- Package/version alignment for Portfolio Architect v1.36.0 native dynamic presentation. Trade Republic provider acquisition/runtime behavior is unchanged.
- Preserves verified HTTPS/private CA trust, bearer authentication, established provider-specific state and the read-only/advisory boundary.

## 1.35.4

- Package/common-runtime alignment for the Comdirect cash-input localization hotfix; Trade Republic statement import and private diagnostics are unchanged.
- No Trade Republic cash acquisition, transfer or trading capability is added.

## 1.35.3

- Package/common-runtime alignment for Portfolio Architect v1.35.3; the Home Assistant-only broker-editor menu-label fix does not change statement import or private diagnostics.
- No Trade Republic cash acquisition, transfer or trading capability is added.

## 1.35.2

- Package/common-runtime alignment for Portfolio Architect v1.35.2; statement import and private diagnostics remain unchanged.
- The common REST schema-1 model accepts the additive retained-cash metadata contract for future provider use, but this release does not add Trade Republic cash acquisition or authorization.

## 1.35.1

- Package alignment for Portfolio Architect v1.35.1; statement import, accepted snapshot, diagnostics, provider-owned cash and REST schema 1 remain unchanged.
- No transfer, trading or new provider-authentication behavior is introduced.

## 1.35.0

- Aligns the Trade Republic App package with Portfolio Architect v1.35.0 provider-scoped funding; statement import, accepted snapshots, diagnostics and REST schema 1 remain unchanged.
- No transfer, trading or new provider-authentication behavior is introduced.

## 1.34.1

- Package/User-Agent alignment for Portfolio Architect v1.34.1 whole-portfolio allocation-presentation hotfix; Trade Republic statement import, private diagnostics, accepted snapshot and Gateway wire behavior remain unchanged.

## 1.34.0

- Package/User-Agent alignment for Portfolio Architect v1.34.0 generic target/presentation architecture; Trade Republic statement import, private diagnostics, accepted snapshot and Gateway wire behavior remain unchanged.

## 1.33.1

- Package/User-Agent alignment for the Portfolio Architect v1.33.1 recurring-schedule anchor hotfix; Trade Republic statement import, private diagnostics, accepted snapshot and Gateway wire behavior remain unchanged.

## 1.33.0

- Package/User-Agent alignment for Portfolio Architect v1.33.0 source-freshness and plan-schedule separation; Trade Republic statement import, private diagnostic state, accepted snapshot and Gateway wire behavior are unchanged.

## 1.32.0

- Persists the latest bounded Trade Republic statement-import outcome (`accepted`, `rejected`, or `internal_error`) in App-private mode-`0600` state so operator diagnostics survive Web UI reopen/App restart.
- Retains only allowlisted parser/form error text; unexpected exception text is replaced with a generic bounded message so document-derived private content cannot enter diagnostic state.
- Keeps uploaded PDFs memory-only and deliberately does not retain a PDF fingerprint; accepted provider-neutral snapshot behavior, verified HTTPS and Gateway wire contracts are unchanged.
## 1.31.2

- Package/version alignment for the v1.31.2 DKB FinTS capability-probe hardening release; Trade Republic statement import, private snapshot storage and Gateway wire behavior are unchanged.
## 1.31.1

- Package/version alignment for the v1.31.1 Home Assistant-side ISIN-only outside-scope holding validation hotfix; Trade Republic statement import, private snapshot storage and Gateway wire behavior are unchanged.

## 1.31.0

- Package/version alignment for v1.31.0 canonical Robotics-target and historical-exception correction; Trade Republic statement import, private snapshot storage and Gateway wire behavior are unchanged.

## 1.30.0

- Package/version alignment for v1.30.0 provider-aware local execution-policy planning; Trade Republic statement import, private snapshot storage and Gateway wire behavior are unchanged.

## 1.29.0

- Package/version alignment for the v1.29.0 native policy-dashboard presentation release; Trade Republic statement import, private-PKI HTTPS, schemas and read-only behavior are unchanged.

## 1.28.2

- Version alignment for Portfolio Architect v1.28.2 Dependabot workflow maintenance.
- Trade Republic statement import, persisted snapshot, verified HTTPS, schemas and runtime behavior are unchanged.

## 1.28.1

- Version alignment for Portfolio Architect v1.28.1 GitHub Actions runtime maintenance.
- Trade Republic statement import, persisted snapshot, verified HTTPS, schemas and runtime behavior are unchanged.

## 1.28.0

- Version alignment for Portfolio Architect v1.28.0.
- Trade Republic local statement-import behavior, persisted normalized snapshot, verified HTTPS and provider identity remain unchanged.
- No Trade Republic acquisition, parsing, TLS, schema or runtime contract changes.

## 1.27.4

- Version alignment for Portfolio Architect v1.27.4; Trade Republic statement import, persisted snapshot behavior, TLS trust, and bearer authentication are unchanged.

## 1.27.3

- Version alignment for Portfolio Architect v1.27.3; Trade Republic Gateway TLS and statement-import behavior are unchanged.
- The Home Assistant-side hotfix only corrects DKB Gateway-vs-CSV discovery identity suppression.

## 1.27.2

- Version alignment for the Portfolio Architect v1.27.2 Home Assistant discovery-flow migration fix.
- Trade Republic statement import, persisted snapshot semantics, HTTPS transport, REST schema 1 and health schema 6 are unchanged from v1.27.1.

## 1.27.1

- Release-engineering-only follow-up to v1.27.0; Trade Republic Gateway HTTPS/runtime behavior is unchanged.
- Aligns immutable-release Docker smoke validation with the Supervisor-aware protected PR validation path.

## 1.27.0

- Serves the accepted Trade Republic snapshot over the common verified-HTTPS/private-CA Gateway boundary and publishes only public trust through Supervisor discovery.
- Retains bearer authentication, statement-import validation, persisted snapshot behavior, REST schema 1 and health schema 6.
- The original statement PDF remains transient private input and no trading/write capability is added.

## 1.26.7

- Version alignment for Portfolio Architect 1.26.7.
- Inherits the common Gateway cached-snapshot quantity round-trip and HTTP validator-precedence fix.
- Statement import, persisted snapshot contract, startup behavior and REST/health schemas remain unchanged.

## 1.26.6

- Version alignment for Portfolio Architect 1.26.6.
- Statement import, persisted snapshot, startup behavior and REST schema are unchanged; the hotfix changes only Home Assistant-side source diagnostics.

## 1.26.5

- Version alignment for Portfolio Architect 1.26.5.
- Statement import, persisted snapshot and REST schema are unchanged; v1.26.5 changes only Home Assistant-side read-only date-domain presentation.

## 1.26.4

- Version alignment for Portfolio Architect 1.26.4.
- Statement import, persisted snapshot and REST schema are unchanged; v1.26.4 changes only Home Assistant native date-tile formatting.

## 1.26.3

- Version alignment for Portfolio Architect 1.26.3.
- Statement import, persisted snapshot and REST schema are unchanged; v1.26.3 changes only Home Assistant dashboard/presentation.

## 1.26.2

- Version alignment for Portfolio Architect 1.26.2.
- Statement import, persisted snapshot and REST schema are unchanged; v1.26.2 changes only Home Assistant presentation/diagnostics.

## 1.26.1

- Version alignment for Portfolio Architect 1.26.1.
- Statement import, persisted snapshot and REST schema are unchanged; Portfolio Architect now matches the existing ISIN-only snapshot correctly downstream.

## 1.26.0

- Version alignment for Portfolio Architect 1.26.0.
- The validated Trade Republic snapshot service now starts automatically so a configured Portfolio Architect REST consumer survives Home Assistant restarts.
- The local DEPOTAUSZUG import and REST schema remain unchanged.

## 1.25.0

- Adds admin-only local import of the supported German `DEPOTAUSZUG` text-PDF statement family.
- Parses PDFs in memory and persists only the validated provider-neutral holdings snapshot; the original PDF is not stored.
- Cross-checks statement date, creation timestamp, one ISIN per position, position count and EUR portfolio total; unsupported or ambiguous documents fail closed.
- Installs only this App's `pypdf 6.15.0` dependency from an exact wheel hash.
- Retains the isolated slug/private data volume, authenticated GET-only REST service and health schema 6 provider identity.

## 1.24.1

- Fixes startup of the isolated Trade Republic provider shell by removing an accidental runtime dependency on the Comdirect-only configuration module.
- Adds build-time startup-module import validation and protected container smoke testing.
- Keeps the App experimental, manual-only and fail-closed; Trade Republic statement import remains the next milestone.

## 1.24.0

- Creates the separate Trade Republic Home Assistant App identity.
- Adds isolated App-private storage and a provider-specific bounded health identity.
- Reuses the audited provider-neutral read-only Gateway runtime.
- Deliberately does not implement live Trade Republic acquisition yet.
