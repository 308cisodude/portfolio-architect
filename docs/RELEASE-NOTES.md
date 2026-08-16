# Portfolio Architect 1.28.2

Version 1.28.2 is a narrow release/dependency-automation maintenance update prepared
from the exact published and live-accepted v1.28.1 source baseline. It changes how
Dependabot proposes GitHub Actions **version updates**; it does not change any
production Portfolio Architect or provider Gateway behavior.

## Dependabot GitHub Actions grouping

The existing `.github/dependabot.yml` `github-actions` entry remains weekly with an
`open-pull-requests-limit` of five. It now contains one explicit version-update group:

```yaml
groups:
  github-actions-version-updates:
    applies-to: version-updates
    patterns:
      - "*"
```

This causes related GitHub Actions version updates discovered in the same Dependabot
cycle to be proposed together for one review and one protected validation path instead
of generating a separate version-update pull request for each action.

No `security-updates` group is added by this release. Security-update handling is not
made dependent on waiting for a broader version-update batch.

## Supply-chain invariants

The v1.28.1 action-runtime hardening remains unchanged:

- `actions/checkout` remains pinned to official v7.0.1 commit
  `3d3c42e5aac5ba805825da76410c181273ba90b1`;
- `actions/setup-python` remains pinned to official v7.0.0 commit
  `5fda3b95a4ea91299a34e894583c3862153e4b97`;
- all GitHub Actions remain pinned to immutable 40-character commit SHAs;
- validator container images remain digest pinned;
- Python CI dependencies remain hash locked; and
- the insecure Node-runtime compatibility escape remains forbidden.

## Preserved compatibility contracts

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- No trading, order, transfer, payment, or transaction-history capability is added.
- The historical `v1.19.0-rc2` experimental brokerage probe is not promoted by this release.

## Runtime behavior unchanged

Portfolio Architect integration runtime, provider acquisition and Gateway Apps are unchanged.
Private-PKI verified HTTPS, bearer authentication, DNS pinning, calculations, source
atomicity, LKG, entities and dashboards are unchanged.

DKB live Gateway acquisition remains a later authenticated milestone. The v1.28.0
DKB FinTS boundary is unchanged: the App remains experimental, manual-only and
non-live; `registration_required` remains the expected state until Portfolio Architect
receives its own FinTS product registration number, and any later positive `HIWPDS`
result remains research evidence only.

Trade Republic remains provider-isolated and this release does not move PDF parsing into Portfolio Architect.

No dashboard YAML migration is required. See `docs/UPGRADE-1.28.2.md`.
