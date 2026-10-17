# v1.66.1 deployment workflow

1. On `stable`, fetch/pull and confirm `git status -sb` is clean. Keep the `market-data-poc working files` stash untouched.
2. Create `release/v1.66.1`, extract the **v1.66.1 Git overlay zip** at the repository root, inspect the diff for unrelated or private files, then commit and publish the branch. The complete source zip has a top-level version directory and is a reference, not the Git overlay.
3. Open a PR to `stable`. Wait for **Validate release**, **Validate with hassfest**, and **Validate with HACS** to pass. Squash and merge, fetch/pull `stable`, and verify `git status -sb` shows a clean tracking branch. A leftover release-branch prompt in GitHub Desktop alone does not indicate a failed merge.
4. Publish the immutable `v1.66.1` tag and check its release assets. Update the integration and all four Apps, then replace the reference dashboard YAML to see the presentation changes.
5. Confirm FinTS authority and the DKB EUR 0 cap persist. Observe the label change at the next normal manual read; do not initiate a bank read solely for this UI release.

## PR and squash title

Portfolio Architect v1.66.1 — clarify DKB authority and plan blockers

## PR description

## Summary

Correct the transient DKB comparison labels and make existing source-age and policy blockers readable directly on the PA dashboard.

## User-visible changes

The DKB five-minute review marks the currently selected CSV or FinTS method as authoritative. The plan blocker shows stale source dates and limits and summarizes up to three error-level policy findings when no purchase is eligible. Zero cash authorization is explained in the reserve blocker.

## Security and privacy impact

No new bank access, stored credentials, raw responses, diagnostics or cash authority changes. Reuse bounded HA status fields; escape displayed source and policy strings. Preserve explicit no-fallback behavior and private normalized FinTS evidence.

## Compatibility

No config, wire-schema, entity-ID or cash-policy migration. Existing v1.66.0 FinTS selection, 14-day expiry and user-set EUR 0 DKB cap persist. Dashboard changes require replacing the reference YAML.

## AI assistance

Prepared with AI assistance under maintainer review. Check the authority labels in both acquisition modes, dashboard blockers in English and German, and the release diff before merging.

## Validation

Run the deterministic release pipeline, privacy gate, dashboard semantic tests, Hassfest and HACS checks. Offline tests cover both review labels and rendered blocker cases. Live wording acceptance can wait for the next normal manual FinTS read.
