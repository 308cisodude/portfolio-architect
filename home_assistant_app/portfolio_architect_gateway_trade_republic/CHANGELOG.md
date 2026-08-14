# Changelog

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
