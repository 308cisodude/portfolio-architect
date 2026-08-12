# v1.20.0 validation

The release pipeline validates:

- Python compilation for the integration, standalone Gateway, and Gateway App;
- JSON and YAML parsing for shipped configuration, quality-audit, workflow, and
  dashboard files;
- the complete deterministic regression suite;
- graceful LKG retention with a bounded maximum age and configuration binding;
- rejection of timestamp-regressed or integrity-inconsistent incoming snapshots
  without replacement of the previously validated calculation;
- separation of informational stale holdings from actionability-sensitive cash,
  proposed-purchase, fee, outlay, and execution-state entities;
- evidence-based refresh-overdue logic that rejects stale pre-deadline health
  observations as proof of a missed refresh;
- locally derived snapshot age and expiry telemetry, including minute-tick entity
  updates;
- AI-assisted-development disclosure and publication-accountability contracts;
- Home Assistant monetary sensor metadata and the v1.19 authorized-cash policy,
  including the server-authoritative capped-to-all-available transition;
- executable local REST DNS pinning and authenticated bounded health/portfolio
  transport;
- local publication-readiness metadata without invented repository URLs;
- full-SHA GitHub Action refs and SHA-256-pinned GHCR workflow images;
- fixed Ubuntu 24.04/Python 3.14.6 validation and release jobs;
- exact SHA-256-locked direct and transitive Python validation wheels installed
  without dependency resolution;
- HACS metadata, hassfest validation, brand assets, supported-version policy, and
  security-reporting files;
- Gateway/integration version alignment and App Dockerfile build label; and
- reproducible release builds, package manifests, SHA-256 files, SPDX 2.3
  metadata, ZIP integrity, and archive path safety.

GitHub-hosted publication additionally executes the reviewed immutable HACS and
hassfest validator images. The release workflow requires strict configured
repository metadata, generates artifact attestations, creates a draft release,
uploads all artifacts, and then publishes it.

Run locally:

```bash
./tools/release_check.sh
```
