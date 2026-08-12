# v1.20.1 validation

The release pipeline validates:

- Python compilation for the integration, standalone Gateway, and Gateway App;
- JSON and YAML parsing for shipped configuration, workflow, and dashboard files;
- the complete deterministic regression suite;
- coordinator listener notification on LKG/live metadata transitions even when retained `PortfolioData` compares equal;
- fail-closed actionability-sensitive entities during LKG while informational holdings remain available;
- current-cycle integrity Repair semantics, with genuine timestamp/integrity failures preserved and unrelated degraded paths clearing stale integrity reasons;
- Gateway reauthentication health retaining cached snapshot timestamp, SHA-256 fingerprint, and position count;
- all v1.20.0 graceful-LKG retention, evidence-based refresh-overdue, and time-derived freshness contracts;
- v1.19 authorized-cash policy and server-authoritative capped-to-all-available transition;
- executable local REST DNS pinning and authenticated bounded health/portfolio transport;
- local publication-readiness metadata, immutable workflow dependencies, HACS/hassfest validation, and release-version alignment; and
- reproducible release builds, package manifests, SHA-256 files, SPDX 2.3 metadata, ZIP integrity, and archive path safety.

Run locally:

```bash
./tools/release_check.sh
```
