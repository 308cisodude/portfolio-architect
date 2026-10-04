# v1.66.0 deployment workflow

1. On `stable`, fetch/pull and confirm the only local edits are the previously prepared `README.md` and `docs/INSTALL.md` documentation changes. Keep the `market-data-poc working files` stash untouched.
2. Create `release/v1.66.0` with those two edits carried into the branch. Extract the **v1.66.0 Git overlay zip** at the repository root, review the resulting diff for unexpected/private files, then commit and publish the branch. The complete source zip is a release reference with a top-level version directory, not the Git overlay.
3. Open a PR to `stable`; wait for **Validate release**, **Validate with hassfest**, and **Validate with HACS**. Squash and merge. Fetch/pull `stable` and verify `git status -sb` again.
4. Publish the immutable `v1.66.0` tag and verify its release assets. Update the integration and all four Apps.
5. Follow `docs/UPGRADE-1.66.0.md` one step at a time. Keep CSV selected until the new combined FinTS read and explicit authority switch are live-accepted.

## PR and squash title

Portfolio Architect v1.66.0 — explicit DKB FinTS authority with 14-day expiry

## PR description

## Summary

Add an operator-confirmed DKB CSV/FinTS source switch for holdings and selected-account cash. Stage new, complete FinTS evidence with independent clocks and a fixed 14-day limit.

## User-visible changes

DKB admin Ingress shows current authority, a confirmation control, and bounded readiness. The PA plan consumes FinTS only after explicit selection. Expired FinTS evidence blocks planning until another manual read or explicit CSV switch.

## Security and privacy impact

Keep credentials, TANs, full account inventory and raw bank responses transient. Persist only normalized, bounded private evidence tied to the keyed account selection; exclude new FinTS evidence and canonical cache from App backups. No automatic fallback, background bank access, or money movement.

## Compatibility

CSV remains the upgrade default. Independent CSV holdings and FinTS canonical files prevent source reinterpretation on restart or downgrade. The 24-hour research status and five-minute review remain separate. Switch back to CSV before downgrading to v1.65.9.

## AI assistance

Prepared with AI assistance under maintainer review. Review provenance, source isolation, expiry, privacy and live bank behavior before accepting FinTS authority.

## Validation

Run release, privacy, Hassfest and HACS checks. Offline tests cover explicit switches, restart recovery, account binding, independent expiry, missing evidence, and lack of fallback. Live authority and planner acceptance remain pending.
