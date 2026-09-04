# Portfolio Architect v1.62.5 release notes

v1.62.5 is a narrow Home Assistant coordinator-metadata hotfix on top of v1.62.4. LG clean-room acceptance proved the v1.62.4 immediate reload and private-CA async-hygiene fixes, then exposed a separate metadata bug: the initial setup correctly created the four established mandatory YAML documents, but coordinator fingerprint/LKG metadata accidentally treated optional `exceptions.yaml` as a fifth required file.

## Optional exceptions metadata is truly optional

Portfolio Architect has four required calculation documents: `portfolio.yaml`, `policy.yaml`, `instruments.yaml` and `broker.yaml`. `exceptions.yaml` is optional and is loaded as an empty exception set when absent.

Before v1.62.5, `configuration_files()` returned all four required paths plus `exceptions.yaml` unconditionally. The coordinator metadata path then rejected the directory whenever any returned path was absent, producing `Portfolio configuration files are unavailable` even though the first-run validator and calculator had already accepted the legitimate four-file configuration.

v1.62.5 keeps required paths in the metadata set unconditionally so a missing mandatory file still fails closed. Optional configuration paths participate only while the file actually exists. Therefore:

- four required files with no `exceptions.yaml` are valid;
- adding a real `exceptions.yaml` changes the configuration fingerprint and modification metadata;
- removing it returns metadata to the four-file state;
- deleting any required file still fails closed.

This completes the intended first-run path without creating or requiring a dummy exceptions file.

## Compatibility and preserved contracts

The v1.62.4 first-run unload/reload and private-CA event-loop fixes are unchanged. The v1.62.3 complete bounded German Trade Republic cash-date month matrix is unchanged. Trade Republic parsing/reconciliation, Generic multi-profile acquisition, Comdirect acquisition, DKB CSV acquisition and the DKB research-only FinTS probe are unchanged.

**Comdirect LEGACY remains removed from the active repository.** REST portfolio schema 1, payload schema 8, presentation schema 2, broker schemas 1/2/3, config-entry schema 13, Gateway health schemas 1–10, Supervisor discovery schemas 1/2, `fallback_policy: none`, evidence freshness, verified private-PKI HTTPS, bearer authentication, DNS pinning, LKG/anti-rollback/source-set atomicity and planner/funding semantics remain intact. **Authenticated DKB FinTS remains disabled** and research-only. There is **no silent fallback** between acquisition methods. No trading, order, transfer, payment, transaction-history, sell or withdrawal capability is introduced.

The v1.33.0 source-freshness and plan-schedule separation remains in force. No configured freshness threshold changes. Trade Republic provider-specific PDF parsing stays in its Gateway; this release does not move PDF parsing into Portfolio Architect. No dashboard YAML replacement is required.

## Preserved historical release invariants

For regression clarity, v1.62.5 explicitly preserves these established contracts:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 10 is current; schemas 1–9 remain supported
- config-entry schema 13: unchanged
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- setup states `source_required`, `plan_required`, `configured`: unchanged
- recurring schedule anchoring continues to use the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold.
- Trade Republic provider-specific PDF parsing stays in its Gateway; the complete v1.62.3 German cash-date matrix remains unchanged.
- authenticated DKB FinTS acquisition remains disabled and research-only.
- No trading, order, transfer, payment, or transaction-history capability is introduced.
- Comdirect LEGACY remains removed from the active repository and the historical slug is not reused.
- Acquisition remains explicit with no silent fallback.
- The v1.38.1 dynamic drift presentation is included through the established presentation schema; it is not included as a separate alternate calculation path.
- The historical `v1.19.0-rc2` brokerage-probe idea is not promoted by this release.
