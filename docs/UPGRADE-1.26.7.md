# Upgrade to Portfolio Architect 1.26.7

Version 1.26.7 is a narrow common-Gateway cold-restart integrity hotfix on top of
v1.26.6. It preserves optional position quantity when a cached REST snapshot is
reloaded and corrects HTTP conditional-validator precedence. Portfolio calculation,
provider acquisition, authentication and all wire schemas remain unchanged.

## Before upgrading

- Keep the existing Comdirect and Trade Republic Gateway configuration unchanged.
- Do not delete Gateway App data or persisted snapshots.
- Do not re-import the Trade Republic statement solely for this release.
- No copied/reference dashboard update is required.

## Upgrade

1. Update **Portfolio Architect Gateway — Comdirect** to 1.26.7 in place.
2. Update **Portfolio Architect Gateway — Trade Republic** to 1.26.7 in place.
3. If installed, update **Portfolio Architect Gateway — DKB** to 1.26.7 in place;
   it remains an experimental manual-only non-live shell.
4. Update Portfolio Architect to 1.26.7 through HACS.
5. Restart Home Assistant once after the HACS update.
6. Do not reauthenticate Comdirect, re-enter Gateway tokens, recreate the Portfolio
   Architect configuration, or re-import statements solely because of this update.

## What changes

The common Gateway cache parser now restores optional schema-1 position `quantity`
instead of dropping it. An unchanged quantity-bearing cached snapshot therefore
retains exactly the same serialized body, SHA-256 and ETag across restart.

The REST server also follows conditional-request precedence: a present
`If-None-Match` is authoritative. `If-Modified-Since` is evaluated only when no
ETag validator was supplied.

## Live acceptance

Start from a healthy 1.26.6 three-source / three-provider installation.

1. Confirm all installed packages report 1.26.7 and normal healthy operation is
   unchanged.
2. Wait for a fresh successful Comdirect refresh, then stop the Comdirect Gateway
   for only a few minutes and start it again before upstream authentication expires.
3. Confirm the Gateway reloads its cached snapshot without creating a new snapshot
   fingerprint or Portfolio Architect integrity Repair.
4. Confirm Portfolio Architect remains healthy/live after the next refresh and the
   `Snapshot verified` state remains coherent.
5. Confirm no `Not-modified REST response changed the snapshot fingerprint` error is
   produced by the controlled cold restart.

No dashboard YAML migration is required for v1.26.7.
