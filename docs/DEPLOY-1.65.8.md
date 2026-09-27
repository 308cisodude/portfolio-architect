# v1.65.8 deployment workflow

1. On local `stable`, fetch/pull and verify `git status -sb` is clean. Leave the `market-data-poc working files` stash untouched.
2. Create `release/v1.65.8` from updated `stable`. Extract the Git overlay at repository root, review the diff, commit, and publish the branch.
3. Open a PR to `stable` with the title and description below. Wait for **Validate release**, **Validate with hassfest**, and **Validate with HACS**. Squash and merge, then fetch/pull `stable`.
4. Run `publish immutable` for `v1.65.8` from `stable` and verify the tag and assets.
5. Update the integration and all four Apps. Follow `docs/UPGRADE-1.65.8.md` one step at a time. No dashboard YAML replacement is needed.

## PR and squash title

Portfolio Architect v1.65.8 — accept bounded printable DKB system IDs

## PR description

## Summary

Accept the decoded FinTS customer system ID within its 30-character bound when printable, fixing the v1.65.7 ASCII-only capture rejection.

## User-visible changes

Manual DKB cash research can store a bounded bank ID for a restart reuse trial. Control-character rejection reports `non_printable`.

## Security and privacy impact

Escaped JSON prevents content from changing the private state schema. HMAC fingerprints use UTF-8 and the existing App-private key. ID and key files remain mode 0600 and excluded from backups. No ID value, balance, credential, or raw bank response enters logs or HA states.

## Compatibility

The existing schema and 72-hour expiry remain. Prior ASCII-only files still load. No wire, health, config-entry, or dashboard schema change. CSV remains authoritative for planning.

## AI assistance

Prepared with AI assistance; maintainers should review the bounded ID validator and private serialization before the live DKB trial.

## Validation

Run the release, privacy, Hassfest, and HACS checks. Offline tests cover punctuation and non-ASCII roundtrips, control-character rejection, private permissions, fingerprinting, restart reuse, identity binding, and fixed expiry. Live restart behavior remains unaccepted until the manual trial.
