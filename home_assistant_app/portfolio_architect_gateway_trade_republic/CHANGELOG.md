# Changelog

## 1.24.1

- Fixes startup of the isolated Trade Republic provider shell by removing an accidental runtime dependency on the Comdirect-only configuration module.
- Adds build-time startup-module import validation and protected container smoke testing.
- Keeps the App experimental, manual-only and fail-closed; Trade Republic statement import remains the next milestone.

## 1.24.0

- Creates the separate Trade Republic Home Assistant App identity.
- Adds isolated App-private storage and a provider-specific bounded health identity.
- Reuses the audited provider-neutral read-only Gateway runtime.
- Deliberately does not implement live Trade Republic acquisition yet.
