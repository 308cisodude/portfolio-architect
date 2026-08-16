# Changelog

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
