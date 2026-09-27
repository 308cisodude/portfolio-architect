# v1.65.7 deployment workflow

1. On local `stable`, fetch/pull and verify `git status -sb` is clean. Leave the `market-data-poc working files` stash untouched.
2. Create `release/v1.65.7` from updated `stable`. Extract the Git overlay at repository root; review the diff. Commit and publish the branch.
3. Open a PR to `stable` with the title and description below. Wait for **Validate release**, **Validate with hassfest**, and **Validate with HACS**. Squash and merge, then fetch/pull `stable`.
4. Run `publish immutable` for `v1.65.7` from `stable`, and verify the tag and assets.
5. Update the integration and all four Apps. No dashboard YAML replacement is needed. Follow `docs/UPGRADE-1.65.7.md` for one manual acceptance read.

## PR and squash title

Portfolio Architect v1.65.7 — classify rejected DKB system IDs

## PR description

## Summary

Add a bounded reason for DKB FinTS system-ID capture rejection without changing the storage gate.

## User-visible changes

The admin-only manual cash research view reports a fixed capture-reason category for the latest request.

## Security and privacy impact

No ID value, partial characters, length, type name, credentials, balance, or raw bank response is added to logs, state, or diagnostics. Rejected IDs remain neither hashed nor persisted. Existing App-private HMAC key and ID backup exclusions remain.

## Compatibility

No wire, health, config-entry, or dashboard schema change. Existing DKB shadows and private files survive an in-place upgrade; CSV authority remains unchanged.

## AI assistance

Prepared with AI assistance; maintainers should review the diagnostic category boundary and live bank trial.

## Validation

Run `./tools/release_check.sh`, Hassfest and HACS PR checks. Offline tests cover every category, no persistence for rejected values, and valid-capture precedence. Live acceptance requires one manual read to identify the category. Restart reuse and actual backup exclusion remain unaccepted.
