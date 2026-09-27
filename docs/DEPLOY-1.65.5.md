# v1.65.5 deployment workflow

1. On local `stable`, fetch/pull and verify `git status -sb` is clean. Leave the `market-data-poc working files` stash untouched.
2. Create `release/v1.65.5` from updated `stable`. Extract the v1.65.5 Git overlay at repository root; review the diff and listed deletions. Commit and publish the branch.
3. Open a PR to `stable` using the title and description below. Wait for **Validate release**, **Validate with hassfest**, and **Validate with HACS** to pass. Squash and merge; delete the remote branch. Fetch/pull `stable` locally.
4. Run `publish immutable` for `v1.65.5` from `stable`, and verify the tag and assets.
5. Update the PA integration and all four version-aligned Gateway Apps. No dashboard YAML replacement is needed. Follow `docs/UPGRADE-1.65.5.md`, including the backup archive exclusion check before relying on persistence.

## PR and squash title

Portfolio Architect v1.65.5 — DKB private system-ID continuity

## PR description

## Summary

Retain one bounded DKB FinTS system ID across the Gateway App's daily cold-backup restart for a read-only manual cash research trial.

## User-visible changes

- A manual observation for the same banking user can reuse an ID after the App restarts.
- Admin Ingress continues to show only prior-ID reuse and bank-approval booleans. The fixed research window is 72 hours from the approved seed read.

## Security and privacy impact

The ID and product/user binding digest are stored in one App-private `0600` file with a 512-byte limit and strict schema. The file is excluded from HA backups. The ID is not rendered, logged, sent to PA, or included in status/diagnostics. No credentials, raw bank response, TAN, account details, or dialog state are persisted. Cold backups and CSV authority remain unchanged.

## Compatibility

No config-entry, wire, health, or dashboard schema change. Update all four Apps for version alignment. The v1.65.4 RAM-only ID cannot migrate; the existing cash/holdings shadows survive. Restoring a backup requires reseeding the excluded ID.

## AI assistance

Prepared with AI assistance; maintainers should review the storage boundary, exact backup exclusion, live bank interaction, tests, and release assets.

## Validation

Run `./tools/release_check.sh`, Hassfest and HACS PR checks. Offline tests cover restart reuse, fixed expiry, user isolation, file mode and backup configuration. Live acceptance must confirm an actual cold backup excludes the file and the next manual read reuses the ID. No live bank request was made during preparation.
