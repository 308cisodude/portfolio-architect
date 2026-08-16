# v1.28.2 validation

Portfolio Architect v1.28.2 is a release/dependency-automation-only maintenance
release based on the published and live-accepted v1.28.1 runtime. Validation must
prove that Dependabot groups GitHub Actions version updates without weakening the
existing immutable-dependency or production-runtime contracts.

Release-specific validation must prove:

- integration, engine, common Gateway and all three App package versions are
  `1.28.2`;
- `.github/dependabot.yml` still configures exactly one `github-actions` ecosystem at
  directory `/` on the weekly schedule with `open-pull-requests-limit: 5`;
- one `github-actions-version-updates` group uses `applies-to: version-updates` and
  `patterns: ["*"]`, without configuring a security-update group;
- all four `actions/checkout` uses remain pinned to
  `3d3c42e5aac5ba805825da76410c181273ba90b1` (`v7.0.1`);
- the two `actions/setup-python` uses remain pinned to
  `5fda3b95a4ea91299a34e894583c3862153e4b97` (`v7.0.0`);
- every GitHub Action reference remains a full 40-character immutable SHA and the
  `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION` compatibility escape remains absent;
- existing pinned runner, Python 3.14.6, hash-locked dependencies, validator-image
  digests, source/history/artifact privacy gates and release workflow ordering remain
  unchanged;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- Comdirect OAuth/session maintenance, Trade Republic statement import, DKB v1.28.0
  registration/capability-probe gate, calculations, LKG, entities and dashboards
  remain unchanged; and
- no trading, order, transfer, payment or transaction-history capability is added.

The protected GitHub `Validate release` workflow remains authoritative for actual
hosted-runner action execution and provider-App Docker/TLS smoke validation.
