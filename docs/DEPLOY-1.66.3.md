# v1.66.3 deployment workflow

1. On clean `stable`, fetch/pull. Keep the private `market-data-poc working files` stash untouched.
2. Create `release/v1.66.3`, extract the v1.66.3 Git overlay at the repository root, review changes, commit and publish the branch. The complete ZIP is the full release handoff; its source archive is a reference, not an overlay.
3. Open a PR into `stable` using the text below. Require green Validate release, Validate with HACS and Validate with hassfest checks. These include protected image builds and privacy scanning in CI.
4. Squash and merge. Switch Desktop to `stable`, fetch/pull, and verify `git status -sb` is clean and aligned. Delete the release branch after merge.
5. Publish immutable tag `v1.66.3` through the existing release workflow; verify all assets. Update the integration and all four Apps, and follow Home Assistant's restart prompt. No new dashboard YAML replacement is required.
6. Follow the upgrade guide: verify one TR uploader, import the combined PDF once, confirm the six Brokerage holdings, cash balance, crypto exclusion and conservative evidence clocks. Compare cash against the same-date standalone account statement. Confirm the new Marketplace page renders after the integration update.
7. Preserve DKB until the November 15 expiry/review trial. The two DKB checks are not prerequisites for this bounded TR compatibility release and remain explicitly pending.

## PR and squash title

Portfolio Architect v1.66.3 — unify Trade Republic statement imports

## PR description

## Summary

Support the new German TR combined net worth statement through one format-aware uploader, preserving legacy portfolio and cash statement compatibility. Include the already merged Marketplace presentation and CI action-pin updates.

## User-visible changes

One Import TR statement form detects combined net worth, legacy holdings or cash statements. Combined imports reconcile Brokerage and Cashkonto before updating both together; crypto is excluded. Separate holdings/cash statuses remain. The installed-release Marketplace README gains the compact overview and banner.

## Security and privacy impact

Uploaded PDFs remain transient and public tests are wholly synthetic. No private statement, account identifiers, credentials or crypto positions are added to release files. Combined publication uses one canonical atomic snapshot; failed validation/publication preserves previous evidence. Safe diagnostics retain fixed messages only. The existing exact-hash banner privacy rule remains intact.

## Compatibility

No entity, wire-schema, authority, DKB freshness or planner-policy change. Existing TR snapshots migrate by preferring canonical committed cash over the legacy sidecar. Date-only combined evidence is conservatively observed at local midnight. Older evidence is rejected. Restore an aligned backup before downgrade to avoid older code recovering stale legacy cash.

## AI assistance

AI assisted implementation, synthetic tests, documentation and release preparation. Maintainer review covers section isolation, cash semantics, atomic publication/restart, no-fallback and privacy boundaries.

## Validation

Review the supplied local validation result and require green release, HACS and hassfest PR checks before merging. Live combined-PDF/cash and Marketplace acceptance remain pending until installation. DKB live acceptance remains scheduled separately.
