# Changelog

## 1.58.0

- Version 1.58.0 adds health-schema-9 holdings/cash capability authority. DKB `csv` remains authoritative; `fints` remains `research_only`, cannot become authoritative, and authenticated FinTS remains disabled.

## 1.57.0

- Version alignment only for the historical Comdirect App withdrawal; DKB acquisition and anonymous-probe behavior are unchanged from v1.56.1.

## 1.56.0

DKB probe dispatch time is rendered deterministically in Europe/Berlin plus authoritative UTC; tzdata is installed and authenticated FinTS remains disabled. Routine Ingress request-completion logs move to DEBUG.

## 1.55.1

- Version alignment only for the v1.55.1 Comdirect migration hotfix; DKB CSV acquisition and the anonymous FinTS research gate are unchanged.

## 1.55.0

- Version-aligns the DKB App with the Comdirect App-identity migration release.
- DKB CSV holdings/cash, anonymous FinTS research gate, verified HTTPS and freshness behavior are unchanged from v1.54.0.

## 1.54.0

- Standardizes the active DKB CSV acquisition card to green and research-only FinTS cards to amber.
- Removes the misleading user-facing Gateway cache/freshness option for static CSV acquisition; Portfolio Architect remains authoritative for evidence freshness.
- Replaces the brittle exact Alpine OpenSSL package revision pin with branch-current installation plus a protected CI security floor.

## 1.53.1

- Refresh the pinned Alpine 3.24 OpenSSL runtime CLI dependency to `3.5.8-r0` after repository package rotation; private-PKI generation and TLS behavior are unchanged.
- Keep accepted DKB CSV holdings/cash snapshots servable independently of the legacy Gateway cache-age setting; Portfolio Architect's CSV/static freshness policy remains authoritative.
- Keep `csv` active and `fints` research-only/non-activatable; no authenticated FinTS behavior changes.

## 1.53.0

- Add health-schema-8 acquisition control metadata: `csv` active/ready and `fints` research-only/non-activatable.
- Keep DKB CSV holdings/cash acquisition unchanged and keep authenticated FinTS disabled.

## 1.52.0

- Graduate the App-level DKB Gateway stage from experimental to stable for the live-proven depot-CSV holdings and Girokonto cash-CSV acquisition paths.
- Keep the anonymous FinTS BPD capability probe explicitly labelled `EXPERIMENTAL · RESEARCH ONLY`; authenticated FinTS remains disabled and cannot replace/fall back from CSV evidence.
- Provider acquisition, evidence timestamps, probe transport/fingerprints and private-PKI behavior are otherwise unchanged from v1.51.1.

## 1.50.0

- add a persisted server-side `Last probe sent` timestamp to the anonymous BPD research UI and bounded status document
- keep DKB CSV holdings/cash acquisition, response fingerprinting and the authenticated-FinTS gate unchanged; align package metadata with Portfolio Architect v1.50.0

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

- Package/version alignment plus optically distinct static DKB CSV and live FinTS sections; authenticated FinTS remains unavailable/research-only and CSV acquisition semantics are unchanged.
- Common health schema 7 reports bounded acquisition mode `csv`; schemas 1–6 remain compatible.

## 1.47.0

- Adds a separate bounded DKB Girokonto `Umsatzliste` CSV importer for provider-scoped cash beside the existing depot-CSV holdings importer.
- Persists only normalized balance/date evidence; account identifiers, transaction rows, counterparties, references and raw CSV bytes remain transient.
- Keeps holdings and cash timestamps independent, clamps negative balances to zero eligible cash, and never infers overdraft/credit availability.
- Leaves the anonymous FinTS probe isolated and authenticated FinTS disabled.

## 1.46.0

- Removes the temporary migration-only canonical-snapshot endpoint after the PA-side legacy DKB CSV bridge was live-proven and retired. DKB CSV acquisition and FinTS probing are unchanged.

## 1.45.1

- Adds the authenticated read-only migration snapshot endpoint used only to compare an old legacy DKB CSV after the normal serving-age limit has expired.
- Keeps `/api/v1/portfolio` fail-closed for the same expired snapshot; raw CSV, depot identity and FinTS state remain inaccessible.
- Fixes expired health-document metadata consistency without changing DKB CSV parsing or authenticated-FinTS gating.

## 1.45.0

- Adds bounded authoritative DKB depot-CSV batch acquisition inside the DKB Gateway; raw CSV and depot identity remain transient and only the normalized canonical snapshot persists.
- Auto-starts the experimental DKB App so its verified-HTTPS REST source survives Home Assistant restarts.
- Keeps the anonymous FinTS capability probe isolated; authenticated FinTS acquisition, PIN/TAN, trading and money movement remain disabled.


## 1.44.0

- Package/version alignment for Portfolio Architect v1.44.0 Configure edit-context UX consistency; DKB remains experimental/manual-only and its anonymous capability probe is unchanged.

## 1.43.0

- Package/version alignment for Portfolio Architect v1.43.0 route-level execution evidence and native funding-edge editing; DKB remains experimental/manual-only and its anonymous capability probe is unchanged.

## 1.42.0

- Package/version alignment for Portfolio Architect v1.42.0 execution-path presentation; DKB remains experimental/manual-only and its anonymous capability probe is unchanged.

## 1.41.1

- Package/version alignment for Portfolio Architect v1.41.1 local-cash routing tie-break hotfix; DKB remains experimental/manual-only and its anonymous FinTS capability probe is unchanged.

## 1.41.0

- Package/version alignment for Portfolio Architect v1.41.0 Trade Republic cash-statement acquisition; DKB remains experimental/manual-only and its anonymous FinTS capability probe is unchanged.
- No DKB login, holdings, transfer, payment or order capability is added.

## 1.40.1

- Package/version alignment for the Portfolio Architect v1.40.1 Home Assistant Configure-menu compatibility hotfix; DKB remains experimental/manual-only and the anonymous FinTS capability-probe behavior is unchanged.
- Provider runtime, verified HTTPS/private CA trust, bearer authentication and the no-login/no-trading boundary remain unchanged.

## 1.40.0

- Package/version alignment for Portfolio Architect v1.40.0 evidence-backed advisory funding-transfer modelling; DKB remains experimental/manual-only; FinTS capability-probe behavior is unchanged.
- No provider App gains transfer, payment, order-placement or other write capability; verified HTTPS/private CA trust and bearer authentication remain unchanged.

## 1.39.0

- Package/version alignment for Portfolio Architect v1.39.0 dynamic colourful current/target allocation presentation; DKB capability-probe behavior is unchanged.
- DKB remains experimental, manual-only and non-live; registered capability probing, verified HTTPS/private CA trust and the no-login/no-trading boundary are unchanged.

## 1.38.1

- Package/version alignment for Portfolio Architect v1.38.1 native dynamic allocation-drift presentation; The anonymous registered FinTS probe is unchanged; DKB remains experimental, manual-only and non-live.
- Preserves the v1.38.0 cash/ISIN presentation work; the v1.37 shared human-input helper remains unused by exact FinTS registration/probe fields.

## 1.38.0

- Package/version alignment for Portfolio Architect v1.38.0 native dashboard usability polish; the anonymous registered FinTS probe is unchanged.
- DKB remains experimental, manual-only and non-live; the v1.37 shared human-input helper remains unused by exact FinTS registration/probe fields.

## 1.37.0

- Package/common-runtime alignment for the shared human-numeric validation foundation; DKB does not opt its FinTS registration/probe fields into locale numeric normalization.
- The anonymous registered FinTS probe remains experimental, manual-only and non-live with no authenticated holdings, transfer, payment or trading capability.

## 1.36.1

- Package/version alignment for the Portfolio Architect v1.36.1 Home Assistant dashboard hotfix; the anonymous registered FinTS probe is unchanged.
- DKB remains experimental, manual-only and non-live with no authenticated holdings, transfer, payment or trading capability.

## 1.36.0

- Package/version alignment for Portfolio Architect v1.36.0 native dynamic presentation. DKB provider acquisition/runtime behavior is unchanged.
- Preserves verified HTTPS/private CA trust, bearer authentication, established provider-specific state and the read-only/advisory boundary.

## 1.35.4

- Package/User-Agent alignment for the Comdirect cash-input localization hotfix; DKB probe behavior and evidence handling are unchanged.
- DKB remains experimental, manual-only and non-live with no authenticated holdings, transfer, payment or trading capability.

## 1.35.3

- Package/User-Agent alignment for Portfolio Architect v1.35.3; the Home Assistant-only broker-editor menu-label fix does not change DKB probe behavior.
- DKB remains experimental, manual-only and non-live with no authenticated holdings, transfer, payment or trading capability.

## 1.35.2

- Package/common-runtime alignment for Portfolio Architect v1.35.2; DKB probe behavior remains unchanged.
- DKB remains experimental, manual-only and non-live with no authenticated holdings, transfer, payment or trading capability.

## 1.35.1

- Package/User-Agent alignment for Portfolio Architect v1.35.1; the v1.35.0 raw/decoded anonymous FinTS probe fingerprinting remains unchanged.
- DKB remains experimental, manual-only and non-live with no authenticated acquisition or transaction capability.

## 1.35.0

- Fingerprints the exact bounded anonymous FinTS HTTP response body before normalization/base64 decoding and persists only its SHA-256 plus byte count alongside the existing decoded-response fingerprint.
- Keeps exact raw/decoded response bytes ephemeral, preserves legacy probe-state readability, and leaves DKB experimental/manual-only/non-live with no authenticated holdings or transaction capability.

## 1.34.1

- Package/User-Agent alignment for Portfolio Architect v1.34.1 whole-portfolio allocation-presentation hotfix; DKB FinTS probe behavior remains unchanged and experimental/manual-only/non-live.

## 1.34.0

- Package/User-Agent alignment for Portfolio Architect v1.34.0 generic target/presentation architecture; DKB FinTS probe behavior remains unchanged and experimental/manual-only/non-live.

## 1.33.1

- Package/User-Agent alignment for the Portfolio Architect v1.33.1 recurring-schedule anchor hotfix; DKB FinTS probe behavior remains unchanged and experimental/manual-only/non-live.

## 1.33.0

- Package/User-Agent alignment for Portfolio Architect v1.33.0 source-freshness and plan-schedule separation; DKB FinTS probe behavior is unchanged and remains experimental/manual-only/non-live.

## 1.32.0

- Package/version alignment for Portfolio Architect v1.32.0 provider freshness/diagnostics foundation.
- The live-accepted v1.31.2 DKB FinTS registration, Ingress and persisted sanitized probe-diagnostic behavior is unchanged; DKB remains experimental, manual-only and non-live.
## 1.31.2

- Requires the project's issued FinTS product registration ID to be exactly 25 alphanumeric characters and transmits it only in `HKVVB`'s product-designation field.
- Fixes Home Assistant Ingress POST redirects so Store/Probe actions remain inside the DKB App instead of navigating the iframe to absolute `/`.
- Persists sanitized probe outcomes across Web UI reloads, including bounded `bank_rejected`, HTTP, transport and protocol failure states.
- Retains bounded `HIRMG`/`HIRMS` return codes plus bounded sanitized operator-message text from valid FinTS responses, redacts the configured product ID if echoed, and discards arbitrary payload/raw response bytes after recording a decoded-response SHA-256 and byte count.
- Keeps the DKB App experimental, manual-only, fail-closed and non-live; no DKB credential, holdings, order, transfer, payment or transaction-history operation is added.
## 1.31.1

- Package/version alignment for the v1.31.1 Home Assistant-side ISIN-only outside-scope holding validation hotfix; the DKB App remains experimental, manual-only and non-live with the unchanged registration-gated anonymous FinTS capability probe.

## 1.31.0

- Package/version alignment for v1.31.0 canonical Robotics-target and historical-exception correction; the DKB App remains experimental, manual-only and non-live with the unchanged registration-gated anonymous FinTS capability probe.

## 1.30.0

- Package/version alignment for v1.30.0 provider-aware local execution-policy planning; the DKB App remains experimental, manual-only and non-live with the unchanged registration-gated anonymous FinTS capability probe.

## 1.29.0

- Package/version alignment for the v1.29.0 native policy-dashboard presentation release; the v1.28 DKB FinTS registration/capability-probe gate remains experimental, manual-only and non-live.

## 1.28.2

- Version alignment for Portfolio Architect v1.28.2 Dependabot workflow maintenance.
- The v1.28.0 registration-gated anonymous FinTS capability probe is unchanged; DKB remains experimental, manual-only and non-live.

## 1.28.1

- Version alignment for Portfolio Architect v1.28.1 GitHub Actions runtime maintenance.
- The v1.28.0 registration-gated anonymous FinTS capability probe is unchanged; DKB remains experimental, manual-only and non-live.

## 1.28.0

- Adds a registration-gated anonymous DKB FinTS 3.0 BPD capability probe against the fixed documented DKB endpoint.
- Stores only the project's own validated FinTS product registration number and sanitized BPD capability metadata in App-private state.
- Detects `HIWPDS` only as bank-level research evidence; authenticated user-capability validation remains required before any future holdings implementation.
- Requests no DKB login name, PIN or TAN and sends no holdings, order, transfer, payment, debit or transaction-history business transaction.
- Remains experimental, manual-only and fail-closed as a Portfolio Architect source.
- Preserves provider identity `dkb`, private-PKI verified HTTPS, bearer authentication and the existing `dkb` versus `dkb_csv` collision boundary.

## 1.27.4

- Version alignment for Portfolio Architect v1.27.4; DKB Gateway behavior remains experimental/manual-only/fail-closed with no live acquisition.
- No DKB authentication, transport, schema, or runtime behavior change.

## 1.27.3

- Version alignment for Portfolio Architect v1.27.3.
- The DKB App continues to publish provider ID `dkb`; Portfolio Architect now correctly treats configured DKB CSV (`dkb_csv`) as already-represented scope and suppresses the stray discovery Add card.
- The App remains experimental, manual-only and fail-closed with no live DKB acquisition.

## 1.27.2

- Version alignment for the Portfolio Architect v1.27.2 Home Assistant discovery-flow migration fix.
- The DKB App remains the same experimental manual-only fail-closed HTTPS provider shell; no live DKB acquisition capability is added.

## 1.27.1

- Release-engineering-only follow-up to v1.27.0; DKB provider-shell HTTPS/runtime behavior is unchanged.
- Aligns immutable-release Docker smoke validation with the Supervisor-aware protected PR validation path.

## 1.27.0

- Inherits the common persistent private-PKI HTTPS server and Supervisor public-trust discovery boundary.
- Retains bearer authentication and the provider-neutral GET-only REST/health runtime.
- DKB remains experimental, manual-only and fail-closed with no live acquisition path.

## 1.26.7

- Version alignment for Portfolio Architect 1.26.7.
- Inherits the common Gateway cached-snapshot round-trip and HTTP validator-precedence fix.
- DKB remains an experimental manual-only fail-closed provider shell with no acquisition path.

## 1.26.6

- Version alignment for Portfolio Architect 1.26.6.
- DKB remains an experimental manual-only fail-closed provider shell with no acquisition path; the hotfix changes only Home Assistant-side source diagnostics.

## 1.26.5

- Version alignment for Portfolio Architect 1.26.5.
- DKB remains an experimental manual-only fail-closed provider shell with no acquisition path; v1.26.5 changes only Home Assistant-side date presentation.

## 1.26.4

- Version alignment for Portfolio Architect 1.26.4.
- DKB remains an experimental manual-only fail-closed provider shell with no acquisition path; v1.26.4 changes only Home Assistant native date-tile formatting.

## 1.26.3

- Version alignment for Portfolio Architect 1.26.3.
- DKB remains an experimental manual-only fail-closed provider shell with no acquisition path; v1.26.3 changes only Home Assistant dashboard/presentation.

## 1.26.2

- Version alignment for Portfolio Architect 1.26.2.
- DKB remains an experimental manual-only fail-closed provider shell with no acquisition path; v1.26.2 changes only Home Assistant presentation/diagnostics.

## 1.26.1

- Version alignment for Portfolio Architect 1.26.1.
- DKB remains an experimental manual-only fail-closed provider shell with no acquisition path.

## 1.26.0

- Version alignment for Portfolio Architect 1.26.0.
- DKB remains an experimental manual-only fail-closed provider shell.

## 1.25.0

- Version alignment for Portfolio Architect 1.25.0.
- DKB remains an experimental manual-only fail-closed provider shell; no DKB acquisition path is introduced.
- Trade Republic statement parsing remains isolated in the separate Trade Republic App.

## 1.24.1

- Fixes startup of the isolated DKB provider shell by removing an accidental runtime dependency on the Comdirect-only configuration module.
- Adds build-time startup-module import validation and protected container smoke testing.
- Keeps the App experimental, manual-only, fail-closed and without live DKB acquisition.

## 1.24.0

- Creates the separate DKB Home Assistant App identity.
- Adds isolated App-private storage and a provider-specific bounded health identity.
- Reuses the audited provider-neutral read-only Gateway runtime.
- Deliberately does not implement live DKB acquisition yet.
