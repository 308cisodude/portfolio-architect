# v1.65.4 deployment workflow

1. On local `stable`, fetch/pull and verify `git status -sb` is clean. Leave the separate `market-data-poc working files` stash untouched.
2. Create `release/v1.65.4` from updated `stable`. Extract the v1.65.4 Git overlay at repository root; review the diff and listed deletions. Commit and publish the branch.
3. Open a PR to `stable` using the title and description below. Wait for **Validate release**, **Validate with hassfest**, and **Validate with HACS** to pass. Squash and merge; delete the remote branch. Fetch/pull `stable` locally.
4. Run `publish immutable` for `v1.65.4` from `stable`, and check the release tag and assets.
5. Update the PA integration and all four version-aligned Gateway Apps. Restart only the DKB App to start a clean in-memory trial. No dashboard YAML replacement is needed. Follow `docs/UPGRADE-1.65.4.md`.

## PR and squash title

Portfolio Architect v1.65.4 — DKB system-ID research

## PR description

## Summary

Add a bounded, research-only DKB FinTS system-ID reuse trial for manual booked-balance observations.

## User-visible changes

- In DKB admin Ingress, report whether a previous bank system ID was reused and whether the bank requested approval.
- The first successful observation after an App restart seeds the in-memory trial; the second for the same user tests reuse.

## Security and privacy impact

The system ID is bound to product registration and banking user in App memory and never rendered, logged, persisted, sent to PA, or included in diagnostics. Credentials are entered for each manual request and never persisted. No background request or source promotion; CSV remains authoritative.

## Compatibility

No config-entry, wire, health, or dashboard schema change. Update all four Gateway Apps for version alignment. Existing private cash and holdings shadows survive the update; an App restart clears only the new in-memory trial ID.

## AI assistance

Prepared with AI assistance; maintainers should review the bank interaction, privacy boundary, tests, and release assets.

## Validation

Run `./tools/release_check.sh`, Hassfest and HACS PR checks. The offline fake-bank test verifies one approved read seeds the ID, a subsequent manual read reuses it for the same user, and another user or App restart cannot reuse it. Live DKB approval behavior is unknown until post-deployment acceptance; no real bank request is made during preparation.
