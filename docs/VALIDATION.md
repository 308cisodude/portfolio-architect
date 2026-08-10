# v1.18.2 validation

The release pipeline validates:

- Python compilation for the integration, standalone Gateway, and Gateway App;
- JSON and YAML parsing for all shipped configuration, quality-audit, workflow,
  and dashboard files;
- the complete deterministic regression suite;
- Home Assistant monetary sensor metadata, including inherited monetary classes and
  rejection of invalid `measurement` state classes on advisory currency values;
- executable local REST DNS-pinning behavior, including exact-address connection
  and preservation of the original Host header;
- local publication-readiness metadata without invented repository URLs;
- strict publication configuration in an isolated test repository;
- full-SHA GitHub Action refs and SHA-256-pinned GHCR workflow images;
- fixed Ubuntu 24.04/Python 3.14.6 validation and release jobs;
- exact, SHA-256-locked direct and transitive Python validation wheels installed
  with dependency resolution disabled;
- rejection of deliberately introduced mutable workflow dependencies, unhashed
  Python requirements, and non-enforcing pip installation paths;
- active CODEOWNERS generation and explicit protection of security-sensitive
  repository paths;
- HACS metadata and the stable `portfolio_architect.zip` release asset;
- repository-root and integration-local brand assets;
- tag-to-version and release-workflow contracts;
- supported-version and security-reporting policy files;
- native dashboard contracts and all previously validated v1.16.3 behavior;
- strict two-evaluation decision-trace serialization, material-change thresholds,
  last-known-good replay exclusion, bilingual enum translations, and dashboard
  visibility contracts;
- Gateway/integration version alignment and App Dockerfile build label;
- reproducible release builds, package manifests, SHA-256 files, SPDX 2.3
  metadata, ZIP integrity, and archive path safety.

GitHub-hosted publication additionally installs the locked CPython 3.14 wheel set
and executes the digest-pinned HACS and hassfest validator images. The local build
environment validates their references, hashes, and workflow contracts, but does
not execute Docker or reproduce the exact GitHub-hosted Python 3.14.6 runner. The
first GitHub Actions run is therefore the live compatibility check for those
external execution environments.

The release workflow requires strict configured repository metadata, generates
artifact attestations, creates a draft release, uploads all artifacts, and then
publishes it.

Run locally:

```bash
./tools/release_check.sh
```
