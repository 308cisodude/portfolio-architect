# Changelog

## 1.62.5

- Version-align this App with Portfolio Architect v1.62.5. Provider acquisition, private state, wire schemas, verified private-PKI/bearer trust and no-fallback behavior are unchanged; the runtime hotfix is Home Assistant integration-only.

## 1.62.4

- Version-align with Portfolio Architect v1.62.4. The v1.62.3 bounded German cash-date month matrix and all Trade Republic acquisition/reconciliation behavior remain unchanged; the hotfix is Home Assistant integration-only.

## 1.62.3

- Accept the complete bounded German abbreviated month-label matrix in the authoritative `BARMITTELÜBERSICHT` cash as-of line (`Jan.`, `Feb.`, `März`, `Apr.`, `Mai`, `Juni`, `Juli`, `Aug.`, `Sept.`, `Okt.`, `Nov.`, `Dez.`) while preserving previously accepted aliases.
- Distinguish a missing/unsupported cash as-of date from true multi-date ambiguity with bounded privacy-safe feedback.
- Preserve Cashkonto arithmetic/custody reconciliation, creation/as-of chronology, atomic rejected-import behavior, independent holdings/cash evidence, private-PKI transport and advisory-only boundaries.

## 1.62.2

- Version-align with Portfolio Architect v1.62.2. Provider acquisition/runtime behavior is unchanged; the first-run explicit-choice fix is Home Assistant integration-only.

## 1.62.1

- Version-align with Portfolio Architect v1.62.1. Provider acquisition/runtime behavior is unchanged; first-run service initialization is owned by the Home Assistant integration.

## 1.62.0

- Add backward-compatible health schema 10 `provider_name` metadata and align package version with the Generic Import graduation release. Supported PDF holdings/cash acquisition is unchanged and no live trading/API acquisition is introduced.

## 1.61.2

- Version 1.61.2 aligns package metadata with Portfolio Architect's Home Assistant-side primary-Gateway identity-context hotfix; App runtime, provider acquisition, authority, evidence clocks, wire/security contracts and fallback behavior are unchanged from v1.61.1.

## 1.61.1

- Version 1.61.1 aligns package metadata with Portfolio Architect's Home Assistant-side provider-neutral Supervisor-discovery lifecycle hotfix; App runtime, provider acquisition, authority, evidence clocks, wire/security contracts and fallback behavior are unchanged from v1.61.0.

## 1.61.0

- Version 1.61.0 aligns package metadata with Portfolio Architect's Home Assistant-side Configure removal-confirmation release; provider acquisition, authority, evidence clocks, wire/security contracts and fallback behavior are unchanged from v1.60.0.

## 1.60.0

- Version 1.60.0 adds canonical authoritative holdings/cash evidence availability and independent UTC timestamps. PDF remains authoritative; live API remains unavailable and non-activatable.

## 1.59.0

- Version 1.59.0 adds common read-only capability authority and method-status cards. PDF remains authoritative; live API remains unavailable and non-activatable.

## 1.58.0

- Version 1.58.0 adds health-schema-9 holdings/cash capability authority. Trade Republic `pdf` remains authoritative; `live_api` remains unavailable and cannot become authoritative. PDF acquisition behavior is unchanged.

## 1.57.0

- Version alignment only for the historical Comdirect App withdrawal; Trade Republic acquisition and freshness behavior are unchanged from v1.56.1.

## 1.56.0

Routine successful Ingress request-completion logging moves from INFO to DEBUG; acquisition and statement semantics are unchanged.

## 1.55.1

- Version alignment only for the v1.55.1 Comdirect migration hotfix; Trade Republic PDF/statement acquisition is unchanged.

## 1.55.0

- Version-aligns the Trade Republic App with the Comdirect App-identity migration release.
- DEPOTAUSZUG/KONTOAUSZUG acquisition, static evidence timestamps, verified HTTPS and freshness behavior are unchanged from v1.54.0.

## 1.54.0

- Standardizes the active statement acquisition card to green and unavailable live acquisition to amber.
- Removes the misleading user-facing Gateway cache/freshness option for static PDF acquisition; Portfolio Architect remains authoritative for evidence freshness.
- Replaces the brittle exact Alpine OpenSSL package revision pin with branch-current installation plus a protected CI security floor.

## 1.53.1

- Refresh the pinned Alpine 3.24 OpenSSL runtime CLI dependency to `3.5.8-r0` after repository package rotation; private-PKI generation and TLS behavior are unchanged.
- Keep accepted DEPOTAUSZUG/KONTOAUSZUG PDF snapshots servable independently of the legacy Gateway cache-age setting; Portfolio Architect's imported-statement freshness policy remains authoritative.
- Preserve PDF parsing, evidence timestamps, provider identity and health-schema-8 method inventory unchanged.

## 1.53.0

- Add health-schema-8 acquisition control metadata: `pdf` active/ready and `live_api` unavailable/non-activatable.
- Keep DEPOTAUSZUG/KONTOAUSZUG parsing and persistence unchanged.

## 1.52.0

- Graduate the App-level Trade Republic Gateway stage from experimental to stable for the live-proven DEPOTAUSZUG holdings and KONTOAUSZUG cash PDF acquisition paths.
- Statement parsing, evidence timestamps, private persistence, verified HTTPS and REST behavior are unchanged from v1.51.1.

## 1.50.0

- align package metadata with Portfolio Architect v1.50.0 source-management UX
- Trade Republic DEPOTAUSZUG/KONTOAUSZUG acquisition and live/static Ingress semantics are unchanged from v1.49.0

## 1.49.0

- align package metadata with Portfolio Architect v1.49.0
- provider acquisition/runtime behavior is unchanged from v1.48.2; this release retires only the completed Home Assistant-side legacy Comdirect CSV migration surface

## 1.48.2

- align package metadata with Portfolio Architect v1.48.2
- provider acquisition/runtime behavior is unchanged; the hotfix is in Home Assistant coordinator source-summary propagation

## 1.48.1

- align package metadata with Portfolio Architect v1.48.1
- provider acquisition/runtime behavior is unchanged from v1.48.0; freshness classification is applied by the Home Assistant integration using health-schema-7 acquisition mode

## 1.48.0

- Package/version alignment plus optically distinct static statement and unavailable live-acquisition sections; Trade Republic DEPOTAUSZUG/KONTOAUSZUG semantics are unchanged.
- Common health schema 7 reports bounded acquisition mode `pdf`; schemas 1–6 remain compatible.

## 1.47.0

- Package/version alignment for DKB provider-scoped cash evidence. Trade Republic DEPOTAUSZUG/KONTOAUSZUG acquisition is unchanged.

## 1.46.0

- Package/version alignment for v1.46.0; removes the now-unused DKB migration-only common-server endpoint. Trade Republic runtime semantics are unchanged.

## 1.45.1

- Package/version alignment for the v1.45.1 DKB migration hotfix.
- Common Gateway health now reports expired cached snapshots as schema-consistent unavailable state. The DKB-only migration endpoint remains disabled in the Trade Republic App; statement acquisition is unchanged.

## 1.45.0

- Package/version alignment for the DKB Gateway CSV acquisition release; Trade Republic holdings/cash statement acquisition is unchanged.


## 1.44.0

- Package/version alignment for Portfolio Architect v1.44.0 Configure edit-context UX consistency; Trade Republic DEPOTAUSZUG/KONTOAUSZUG acquisition is unchanged.

## 1.43.0

- Package/version alignment for Portfolio Architect v1.43.0 route-level execution evidence and native funding-edge editing; Trade Republic DEPOTAUSZUG/KONTOAUSZUG acquisition is unchanged.

## 1.42.0

- Package/version alignment for Portfolio Architect v1.42.0 execution-path presentation; Trade Republic DEPOTAUSZUG/KONTOAUSZUG acquisition is unchanged.

## 1.41.1

- Package/version alignment for Portfolio Architect v1.41.1 local-cash routing tie-break hotfix; Trade Republic DEPOTAUSZUG holdings and KONTOAUSZUG cash import behavior is unchanged from v1.41.0.

## 1.41.0

- Adds a separate local `KONTOAUSZUG` cash-statement import beside the established `DEPOTAUSZUG` holdings import, with independently persisted bounded private cash state and fail-closed reconciliation.
- Raw PDFs, transaction rows, counterparties and account/identity data are not persisted; no Trade Republic credentials/private API, trading, transfer, payment or order capability is introduced.

## 1.40.1

- Package/version alignment for the Portfolio Architect v1.40.1 Home Assistant Configure-menu compatibility hotfix; Trade Republic local statement import/private diagnostics are unchanged.
- Provider runtime, verified HTTPS/private CA trust, bearer authentication and the read-only/no-money-movement boundary remain unchanged.

## 1.40.0

- Package/version alignment for Portfolio Architect v1.40.0 evidence-backed advisory funding-transfer modelling; Trade Republic local statement import/private diagnostics are unchanged.
- No provider App gains transfer, payment, order-placement or other write capability; verified HTTPS/private CA trust and bearer authentication remain unchanged.

## 1.39.0

- Package/version alignment for Portfolio Architect v1.39.0 dynamic colourful current/target allocation presentation; Trade Republic statement import and private diagnostics are unchanged.
- Preserves verified HTTPS/private CA trust, bearer authentication, local/private statement processing and the read-only boundary; no cash or transaction-history acquisition is added.

## 1.38.1

- Package/version alignment for Portfolio Architect v1.38.1 native dynamic allocation-drift presentation; Statement import and private diagnostics are unchanged; no cash or transaction-history acquisition is added.
- Preserves the v1.38.0 cash/ISIN presentation work; the v1.37 shared human-input helper remains unused by statement parsing and no transfer or trading capability is added.

## 1.38.0

- Package/version alignment for Portfolio Architect v1.38.0 native dashboard usability polish; statement import and private diagnostics are unchanged.
- The v1.37 shared human-input helper remains unused by statement parsing, and no Trade Republic cash, transaction-history, transfer or trading capability is added.

## 1.37.0

- Package/common-runtime alignment for the shared human-numeric validation foundation; Trade Republic statement import does not opt into locale numeric normalization.
- Statement import/private diagnostics remain unchanged and no Trade Republic cash, transaction-history, transfer or trading capability is added.

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
