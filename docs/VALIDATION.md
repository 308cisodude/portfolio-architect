# v1.60.0 validation

Exact baseline: published and fully live-accepted v1.59.0 tracked source.

Validation requires:

- all integration/Gateway/App package versions aligned to v1.60.0;
- Gateway health schema 9 and health schemas 1–8 compatibility unchanged;
- one common read-only acquisition-authority renderer synchronized into all official provider App build contexts;
- canonical holdings/cash evidence clocks derived only from the already-published Gateway snapshot;
- inactive staged provider evidence excluded from the authoritative evidence display;
- independent holdings/cash timestamps visible where canonical provider state carries separate clocks;
- missing capability evidence rendered explicitly without mutating method authority or fallback state;
- Comdirect explicit `live_api`/complete-`csv` switching semantics unchanged and provider-local only;
- DKB `csv` authority with FinTS still `research_only`, inactive and non-activatable; authenticated FinTS remains disabled;
- Trade Republic `pdf` authority with live API unavailable and non-activatable;
- Generic Import fixed CSV holdings-only and experimental;
- provider-source synchronization idempotence;
- complete regression, Python/JSON/YAML parsing, publication, repository/history privacy, OpenSSL floor and deterministic-release gates;
- independent source-release, Git-overlay and binary-patch replay from the exact v1.59.0 baseline.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI/OpenSSL image execution where Docker is unavailable in the preparation environment.
