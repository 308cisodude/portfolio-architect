# v1.66.4 deployment workflow

1. Fetch and pull a clean `stable` in GitHub Desktop. This overlay was prepared against `97b155e48d0664a7d23bbfac09fab0c7c1b2a002` (v1.66.3).
2. Create `release/v1.66.4` from `stable`. Extract only the Git overlay ZIP at the repository root, review the diff, then commit and publish the branch.
3. Open a PR into `stable`. Wait for **Validate release**, **Validate with HACS** and **Validate with hassfest** to pass, then squash and merge.
4. Switch back to `stable`, fetch and pull, and verify `git status -sb`. Tag the merged commit `v1.66.4` and push the tag. The tag workflow validates, builds and publishes the immutable release.
5. Update the integration, installed Apps and dashboard YAML using the [upgrade guide](UPGRADE-1.66.4.md).

## PR and squash title

Portfolio Architect v1.66.4 — clarify retained and DKB evidence freshness

## PR description

```markdown
## Summary

Apply the two presentation fixes found during the November 18 DKB live trial.

## User-visible changes

Runtime health uses a dedicated Retained calculation tile during last known good operation. DKB FinTS badges distinguish expired observations from a complete usable snapshot and a snapshot the Gateway cannot serve.

## Security and privacy impact

The DKB badge uses the same read guard as the Gateway API. It shows only the existing evidence timestamps and fixed status labels. No new persisted data or network calls.

## Compatibility

No entity IDs, schemas, source authority, freshness rules or planner behavior change. Replace the Home Assistant dashboard YAML to pick up the new tile.

## AI assistance

AI assisted implementation, regression tests, documentation and release packaging. Review the source selection, no-fallback and evidence freshness invariants.

## Validation

Run the three protected PR checks before merging. Check normal operation after installation and the retained and expired UI on the next natural expiry.
```
