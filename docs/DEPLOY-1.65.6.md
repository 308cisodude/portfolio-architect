# v1.65.6 deployment workflow

1. On local `stable`, fetch/pull and verify `git status -sb` is clean. Leave the `market-data-poc working files` stash untouched.
2. Create `release/v1.65.6` from updated `stable`. Extract the Git overlay at repository root; review the diff. Commit and publish the branch.
3. Open a PR to `stable` with the title and description below. Wait for **Validate release**, **Validate with hassfest**, and **Validate with HACS**. Squash and merge, then fetch/pull `stable`.
4. Run `publish immutable` for `v1.65.6` from `stable`, and verify the tag and assets.
5. Update the integration and all four Apps. No dashboard YAML replacement is needed. Follow `docs/UPGRADE-1.65.6.md` for live acceptance.

## PR and squash title

Portfolio Architect v1.65.6 — bounded DKB system-ID diagnostics

## PR description

## Summary

Add bounded admin-only evidence for system-ID capture, private save, and reuse after an App restart.

## User-visible changes

- The manual DKB cash research view shows load/capture/save outcomes and a short keyed fingerprint for the latest request.
- The release update text is concise and links to historical notes.

## Security and privacy impact

A 256-bit random HMAC key stays in an App-private mode-0600 file, excluded from cold backups with the system-ID record. The HMAC fingerprint is short and admin-only; neither ID nor key is logged, sent to PA, or included in persistent status. Credentials and raw bank responses remain transient. CSV authority remains unchanged.

## Compatibility

No wire, health, config-entry, or dashboard schema change. Existing v1.65.5 shadow and ID files survive an in-place upgrade. An HA restore requires reseeding the backup-excluded private ID.

## AI assistance

Prepared with AI assistance; maintainers should review bounded diagnostics, key handling, backup exclusions, and live acceptance.

## Validation

Run `./tools/release_check.sh`, Hassfest and HACS PR checks. Offline tests cover keyed fingerprint stability, mode, restart, user isolation, expiry, and backup configuration. Live bank behavior and actual Supervisor backup exclusion remain to be accepted after publication.
