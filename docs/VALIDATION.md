# v1.28.1 validation

Portfolio Architect v1.28.1 is a release-engineering-only maintenance release based
on the published v1.28.0 runtime. Validation must prove both that the GitHub Actions
runtime refresh is complete and that production behavior remains unchanged.

## Required source invariants

- integration, engine, common Gateway and all three App package versions are
  `1.28.1`;
- every `actions/checkout` use in `.github/workflows` is pinned to
  `3d3c42e5aac5ba805825da76410c181273ba90b1` (`v7.0.1`);
- every `actions/setup-python` use is pinned to
  `5fda3b95a4ea91299a34e894583c3862153e4b97` (`v7.0.0`);
- action references remain full 40-character SHAs rather than mutable major tags;
- `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION` is absent;
- validator containers and Python dependency locks remain unchanged; and
- validate/release provider-shell smoke-test parity remains intact.

## Preserved production contracts

- payload schema 8;
- REST portfolio schema 1;
- Gateway health schema 6;
- private-PKI hostname-verified HTTPS plus bearer authentication;
- Supervisor trust discovery and fail-closed migration;
- request-scoped DNS pinning and local-source validation;
- Comdirect acquisition, PhotoTAN and v1.27.4 session maintenance;
- Trade Republic local statement import;
- v1.28.0 DKB registration-gated anonymous BPD probe with no live holdings;
- portfolio calculations, source atomicity, LKG, entities and dashboard behavior;
- no trading, order, transfer, payment or transaction-history capability.

## Publication acceptance

Local preparation validates source structure, compilation, JSON/YAML parsing,
publication/privacy gates, regression tests, deterministic release construction and
artifact integrity. Docker is unavailable in the preparation environment, so the
protected GitHub `Validate release` workflow remains authoritative for the actual
GitHub-hosted Node.js 24 action execution, three provider-App Docker builds and
provider-shell TLS smoke tests.

After publication, no special live migration is required beyond ordinary in-place
version alignment. No dashboard YAML migration is required.
