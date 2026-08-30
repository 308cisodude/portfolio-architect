# v1.59.0 validation

Exact baseline: published and fully live-accepted v1.58.0 tracked source.

Validation requires:

- all integration/Gateway/App package versions aligned to v1.59.0;
- Gateway health schema 9 and health schemas 1–8 compatibility unchanged;
- one common read-only acquisition-authority/status renderer synchronized into all official provider App build contexts;
- holdings/cash capability authority, authority reason, supported-method state and `fallback_policy: none` visible without adding any common activation form, button or endpoint;
- established acquisition-state colours retained: green active/authoritative, blue ready inactive, amber unavailable/not-ready/research-only;
- Comdirect `live_api`/complete-`csv` explicit switching semantics unchanged and provider-local only;
- DKB CSV authority with FinTS still `research_only`, inactive and non-activatable; authenticated FinTS remains disabled;
- Trade Republic PDF authority with live API unavailable and non-activatable;
- Generic Import fixed CSV holdings-only and experimental;
- provider-source synchronization idempotence;
- complete regression, Python/JSON/YAML parsing, publication, repository/history privacy, OpenSSL floor and deterministic-release gates;
- independent source-release, Git-overlay and binary-patch replay from the exact v1.58.0 baseline.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI/OpenSSL image execution where Docker is unavailable in the preparation environment.
