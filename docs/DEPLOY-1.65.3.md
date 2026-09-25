# v1.65.3 deployment workflow

1. On the local `stable` branch, fetch/pull and check `git status -sb` is clean. Preserve unrelated untracked files or stashes.
2. Create `release/v1.65.3` from current `stable`. Extract `portfolio-architect-v1.65.3-git-overlay.zip` over the repository root; apply listed deletions if any. Review `git diff`, then commit and publish the branch.
3. Open a PR to `stable` using the title and description below. Wait for **Validate release**, **Validate with hassfest**, and **Validate with HACS** to pass. Squash and merge; delete the remote branch. Fetch/pull `stable` locally.
4. Run the repository's `publish immutable` workflow for `v1.65.3` from `stable` and check the release tag and assets. Do not run publication from a local unpublished release branch.
5. Update the PA integration and all four version-aligned Gateway Apps, then reload the integration if required. If using a manually installed dashboard, replace its YAML with the `v1.65.3` English, German, or combined artifact. Perform the acceptance steps in `docs/UPGRADE-1.65.3.md`.

## PR and squash title

Portfolio Architect v1.65.3 — visible plan and policy evidence

## PR description

## Summary

Present current plan blockers and policy evidence directly on the PA dashboard.

## User-visible changes

- Explain stale or unhealthy source evidence beside the investment plan and distinguish it from a current lack of eligible purchases, reserve unavailability, or execution cost deferral.
- Show each policy finding's fund, rule, observed value, and expected value in English and German; direct users to verify and date savings-plan route evidence.
- Keep individual native finding entities available for detailed review.

## Security and privacy impact

No new banking requests, credential handling, account data persistence, or source promotion. The DKB FinTS shadows remain App-private and research-only; CSV evidence remains authoritative. The dashboard reads existing bounded policy and source attributes.

## Compatibility

Config-entry and wire schemas remain unchanged. Update all four Gateway Apps for version alignment. Manually installed dashboard YAML needs to be replaced to show the new presentation.

## AI assistance

Prepared with AI assistance; maintainers should review the generated dashboard and release assets.

## Validation

`./tools/release_check.sh` passed, including privacy, publication-readiness, dashboard generation, the full test suite, archive verification and release checks. No live bank request was made during preparation. Verify the dashboard against a stale-source and an unverified-route case after deployment.
