# v1.63.0 validation

The v1.63.0 preparation contract starts from the exact v1.62.5 tracked-source baseline and changes only static reference-dashboard authoring/generation, dashboard presentation, release packaging, documentation, and package version alignment. Provider acquisition, config/runtime schemas, freshness/LKG, planner/funding behavior, and private-PKI security contracts must remain unchanged.

Required gates include:

- all integration/Gateway/App package versions aligned to v1.63.0;
- the existing v1.62.5 optional-`exceptions.yaml` coordinator regression remains green;
- exactly nine shared dashboard sections are authored once under `dashboard/src/shared/`;
- EN and DE catalogs contain the same 100 keys, every `$i18n` marker resolves, and no `__TODO__` value is accepted;
- English technical overlay is empty and German technical localization remains bounded to the reviewed overlay set;
- EN, DE, and combined dashboard generation is deterministic and semantically locked to the accepted v1.62.5 reference behavior including the zero-exception review correction;
- `dashboard/bilingual-dashboard.yaml` is byte-identical to the generated combined output;
- generated dashboards contain only ordinary static Lovelace YAML with no `$i18n`, include, custom-card, or JavaScript dependency;
- release construction regenerates dashboard artifacts and fails if committed outputs are stale;
- release output contains EN-only, DE-only, and combined dashboard artifacts plus the established integration, Gateway App, source, release-note, upgrade-guide, SBOM, and checksum artifacts;
- complete Python test suite, Python compilation, JSON/YAML parsing, `git diff --check`, strict publication-readiness, repository privacy, provider-source synchronization, release verification, and release-artifact privacy pass;
- three independent release builds are byte-identical;
- source ZIP, Git overlay workflow, and binary patch independently reproduce the final tracked tree from the exact v1.62.5 baseline including executable modes;
- protected GitHub workflows remain authoritative for actual four-App Docker/Supervisor/private-PKI smoke, resolved OpenSSL-floor evidence, complete-history secret scanning, and immutable publication.
