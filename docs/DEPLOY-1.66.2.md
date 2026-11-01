# v1.66.2 deployment workflow

1. On `stable`, fetch/pull and confirm `git status -sb` is clean. Keep the `market-data-poc working files` stash untouched.
2. Create `release/v1.66.2`, extract the **v1.66.2 Git overlay zip** at the repository root, inspect the diff for unrelated or private files, then commit and publish the branch. The complete source zip has a top-level version directory and is a reference, not the Git overlay.
3. Open a PR to `stable`. Wait for **Validate release**, **Validate with hassfest**, and **Validate with HACS** to pass. Squash and merge, fetch/pull `stable`, and verify `git status -sb` shows a clean tracking branch. A leftover release-branch prompt in GitHub Desktop alone does not indicate a failed merge.
4. Publish the immutable `v1.66.2` tag and check its release assets. Update the integration and all four Apps, then replace the reference dashboard YAML.
5. In Runtime health, verify the **Instrument types** tile shows **2 unspecified types** for the cached source evidence. While DKB remains expired, verify the plan blocker names DKB as the current unavailable Gateway and labels the TR October 17 date as retained calculation evidence. Then perform the normal manual DKB read when ready to restore the plan; check FinTS authority and the EUR 0 cap remain set.

## PR and squash title

Portfolio Architect v1.66.2 — clarify source instrument types

## PR description

## Summary

Correct the misleading “Identity conflicts” diagnostic and the v1.66.1 blocker wording seen when PA retains a stale whole-portfolio calculation after a source expires.

## User-visible changes

The English and German dashboards show a bounded instrument-type finding summary. The October 17 DKB and TR type observations appear as two unspecified types; known ETF versus stock disagreements remain explicit. When DKB is unavailable, the plan blocker names that Gateway and separates old retained-calculation dates from current Gateway evidence.

## Security and privacy impact

No new bank reads, credentials, raw responses, or persisted diagnostics. Presentation uses bounded source status and older cached calculations without publishing a partial plan.

## Compatibility

Keep the existing diagnostic entity ID and numeric state, payload schema, acquisition authority, 14-day FinTS limit, no-fallback policy, cash authorization and planner calculations. Replace the dashboard YAML to get the new label and summary.

## AI assistance

Prepared with AI assistance under maintainer review. Inspect the source diff and verify both language variants and the classification of unspecified and contradictory known types before merging.

## Validation

Run the deterministic release pipeline, privacy gates, targeted source-diagnostic and retained-calculation dashboard tests, and the GitHub Hassfest/HACS workflows. The blocker wording can be accepted against the existing expired DKB state; a manual DKB read is needed to restore planning.
