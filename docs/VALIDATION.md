# v1.58.0 validation

Exact baseline: corrected, published and fully live-accepted v1.57.0 tracked source.

Validation requires:

- all integration/Gateway/App package versions aligned to v1.58.0;
- health schema 9 negotiated preferentially while schemas 1–8 remain accepted;
- bounded capability authority with holdings required, optional cash, known supported methods, ready authoritative methods and `fallback_policy: none`;
- Comdirect holdings/cash support for `live_api`/complete `csv`, with the explicitly active method authoritative and no automatic fallback;
- DKB CSV holdings/cash authority while FinTS remains `research_only` and authenticated FinTS remains disabled;
- Trade Republic PDF holdings/cash authority while live API remains unavailable;
- Generic Import fixed CSV holdings authority;
- Portfolio Architect read-only capability-authority presentation with no method-switch endpoint or automatic authority mutation;
- provider-source synchronization idempotence;
- complete regression, Python/JSON/YAML parsing, publication, repository/history privacy, OpenSSL floor and deterministic-release gates;
- independent source-release, Git-overlay and binary-patch replay from the exact v1.57.0 baseline.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI/OpenSSL image execution where Docker is unavailable in the preparation environment.
