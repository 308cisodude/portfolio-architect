# Upgrade to Portfolio Architect 1.31.1

Version 1.31.1 is a narrow Home Assistant-side hotfix for the v1.31 canonical Robotics
target migration. The v1.31.0 source remains immutable.

## Why this hotfix exists

Trade Republic portfolio snapshots may legitimately identify a holding by ISIN without
providing a WKN. After the v1.31 plan migration, the already-owned distributing Robotics
position `IE00BYWZ0333` becomes outside current plan scope. The engine preserved its
ISIN-only identity correctly, but the Home Assistant payload parser still required a
non-empty WKN and rejected the calculated payload with:

```text
Portfolio calculation failed: holdings[13].wkn is invalid
```

Version 1.31.1 accepts an empty WKN when the holding has a non-empty ISIN. It does not
invent a WKN, does not weaken duplicate checks for real identifiers, and still rejects a
holding with neither ISIN nor WKN.

## Recommended live recovery

If v1.31.0 is currently degraded in exactly this state:

1. Leave the migrated v1.31 plan files in place. Do not restore the old Robotics target.
2. Leave the Trade Republic snapshot and all provider App-private data untouched.
3. Update **Portfolio Architect through HACS to 1.31.1** and reload/restart Home Assistant
   as normally required by HACS.
4. Do not reauthenticate Comdirect, reimport Trade Republic, recreate the integration,
   change bearer tokens, or alter private-CA trust solely for this hotfix.
5. Confirm Portfolio Architect returns to live/healthy operation with:
   - seven active targets;
   - six active targets held;
   - accumulating Robotics `IE00BYZK4552` / `A2ANH0` missing/underweight;
   - distributing `IE00BYWZ0333` visible under Outside current plan scope;
   - accepted active exceptions `0`;
   - review-required exceptions `0`; and
   - no automatic sell instruction for the distributing holding.
6. Confirm the previous repair issue clears after a successful calculation.
7. After the integration is healthy, align the Comdirect, DKB and Trade Republic Gateway
   Apps to **1.31.1** in place. Their runtime behavior is unchanged by this hotfix.

If the installation never entered the v1.31.0 failure state, upgrade normally. No
configuration migration beyond the documented v1.31 plan migration is introduced by
v1.31.1. **No dashboard YAML migration is required** for this hotfix.

The DKB boundary is unchanged: the existing registration-gated anonymous FinTS probe may
inspect bank-level `HIWPDS` capability evidence only after Portfolio Architect receives its
own product registration number. It does not yet enable live DKB holdings. An authenticated user-capability/UPD gate remains required before any future holdings implementation.

## Preserved contracts

- v1.31 current-plan files: unchanged
- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged
- Gateway transport/authentication and provider acquisition: unchanged
- LKG matching rules: unchanged
- dashboard YAML: unchanged
- DKB registration-gated FinTS probe: unchanged
- advisory/read-only/no-trading boundary: unchanged
