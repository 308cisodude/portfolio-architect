# Changelog

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
