# Portfolio Architect 1.28.1

Version 1.28.1 is a narrow release-engineering maintenance update prepared from the
exact published v1.28.0 source baseline. It refreshes Portfolio Architect's
JavaScript-based GitHub Actions from Node.js-20-era major versions to current
Node.js-24-capable major versions while retaining immutable full-SHA pinning.

## GitHub Actions refresh

All four workflow uses of `actions/checkout` now use the official v7.0.1 commit:

`3d3c42e5aac5ba805825da76410c181273ba90b1`

The two validation/publication uses of `actions/setup-python` now use the official
v7.0.0 commit:

`5fda3b95a4ea91299a34e894583c3862153e4b97`

The existing workflow inputs remain unchanged. `validate.yml` and `release.yml`
continue to use Ubuntu 24.04, Python 3.14.6, the hash-locked pip dependency set and
the same deterministic release pipeline. HACS and hassfest continue to use their
separately digest-pinned validator containers.

The checkout refresh deliberately covers `hacs.yml` and `hassfest.yml` as well as
`validate.yml` and `release.yml`, so no Portfolio Architect workflow retains the old
checkout v4.4.0 Node.js 20 action runtime.

## Supply-chain invariants

The major-version refresh does not weaken the v1.22 publication model:

- every GitHub Action remains pinned to a 40-character immutable commit SHA;
- no mutable `@v7`, branch or `@main` action reference is introduced;
- validator container images remain digest pinned;
- Python validation dependencies remain hash locked;
- the temporary `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION` compatibility escape is
  forbidden by regression coverage; and
- protected GitHub validation remains authoritative for the real hosted-runner and
  Docker execution path.

## Preserved compatibility contracts

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- No trading, order, transfer, payment, or transaction-history capability is added.
- The historical `v1.19.0-rc2` experimental brokerage probe is not promoted by this release.

## Runtime behavior unchanged

Portfolio Architect integration runtime, provider acquisition and Gateway Apps are unchanged.
The preserved wire contracts are **REST portfolio schema 1**, **Gateway health schema 6**
and **payload schema 8**. Private-PKI verified HTTPS, bearer authentication, DNS
pinning, calculations, source atomicity, LKG, entities and dashboards are unchanged.

The historical experimental brokerage probe from `v1.19.0-rc2` remains excluded from
the stable source and release artifacts.

DKB live Gateway acquisition remains a later authenticated milestone.

Trade Republic remains provider-isolated and this release does not move PDF parsing into Portfolio Architect.

The v1.28.0 DKB FinTS boundary is also unchanged: DKB remains experimental,
manual-only and non-live; the anonymous BPD probe still requires Portfolio
Architect's own FinTS product registration number and a positive `HIWPDS` result
would remain research evidence only. No DKB login, PIN/TAN, holdings, order,
transfer, payment or transaction-history operation is added.

No dashboard YAML migration is required. See `docs/UPGRADE-1.28.1.md`.
