# v1.56.0 validation

Portfolio Architect v1.56.0 is prepared from the exact fully published and fully live-accepted v1.55.1 tracked-source baseline. It is intentionally limited to operator-facing UX, discovery lifecycle hygiene, deterministic timestamp presentation, naming, and routine log-noise reduction.

Release validation must establish that:

- all integration/common Gateway/all five published App version markers align to 1.56.0 while historical release documentation remains historical;
- the DKB probe timestamp remains UTC-canonical in persisted/status data and renders deterministically with `ZoneInfo("Europe/Berlin")` plus authoritative UTC;
- the DKB runtime contains Alpine `tzdata`, while authenticated DKB FinTS remains disabled and CSV remains authoritative;
- Generic Import persists only its Supervisor discovery UUID, removes only that exact UUID during graceful shutdown, retains it for later reconciliation if Supervisor cleanup fails, and never republishes a duplicate while retained cleanup is unresolved;
- Generic Import bearer material is below the normal operational/import content and hidden behind an explicit collapsed disclosure control;
- canonical Comdirect is displayed without `NEW`, historical Comdirect is visibly `LEGACY` and is the only App marked `stage: deprecated`; v1.56.x is its final published line before planned v1.57.0 repository withdrawal, while both slugs/security migration contracts are unchanged;
- successful routine Ingress request-completion logging is DEBUG-only while meaningful lifecycle/acquisition/error messages retain their existing levels;
- the bilingual reference dashboard has one consolidated attention reason/action tile and one LKG snapshot-state presentation without removing the underlying entities;
- `git diff --check`, Python compilation, structured JSON/YAML parsing, the complete 779-test regression suite, strict publication/privacy checks, provider-source synchronization, deterministic release builds, release verification, artifact privacy, and exact v1.55.1→v1.56.0 overlay/patch replay pass before handoff.
