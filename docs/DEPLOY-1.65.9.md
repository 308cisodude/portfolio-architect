# v1.65.9 deployment workflow

1. On `stable`, fetch/pull and check `git status -sb` for a clean tree. Leave the `market-data-poc working files` stash untouched.
2. Create `release/v1.65.9`, apply the complete source archive, review the diff, commit, and publish the branch. Do not include private research outputs.
3. Open a PR to `stable`, wait for **Validate release**, **Validate with hassfest**, and **Validate with HACS**, then squash and merge. Fetch/pull `stable` again and verify its status.
4. Run `publish immutable` for `v1.65.9`; verify the tag and assets.
5. Update the integration and four Apps; follow `docs/UPGRADE-1.65.9.md` one step at a time.

## PR and squash title

Portfolio Architect v1.65.9 — prepare manual DKB portfolio acquisition

## PR description

## Summary

Prepare the DKB Gateway for one selected EUR account, a combined manual read-only holdings/balance workflow, and investment cash authorization. Retire the anonymous BPD panel from Ingress.

## User-visible changes

Select an eligible account through short-lived masked choices; refresh the authorized depot and selected cash account. Set all-available, capped, or retained-reserve CSV investment cash authorization.

## Security and privacy impact

Save only a keyed private binding and masked suffix, excluding binding and key from HA backups. Keep credentials, TAN, inventory, and raw responses transient. Enforce exact account matching and a scheduled five-minute expiry on carried credentials. No trading capability is added.

## Compatibility

DKB CSV stays authoritative; default authorization stays all eligible cash. Existing shadows, old endpoints, HA schemas and other providers remain. v1.65.8 ignores a new cap/reserve after rollback. FinTS activation and 14-day freshness remain proposed.

## AI assistance

Prepared with AI assistance; review account binding, bank challenges, policy publication and privacy before live acceptance.

## Validation

Run release, privacy, Hassfest and HACS checks. Offline coverage includes account collisions and private permissions, manual workflow and credential timeout, CSV policy and retired BPD UI. Live DKB acceptance remains pending.
