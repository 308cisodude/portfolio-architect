# Upgrade to Portfolio Architect v1.62.0

v1.62.0 graduates **Portfolio Architect Gateway — Generic Import** to stable multi-profile operation. Native provider acquisition is unchanged.

## Existing Generic Import users

Existing experimental state is migrated without changing its provider identity. If the old Generic snapshot/mapping/diagnostic state exists, the migrated profile remains `generic_csv` and keeps the established `/api/v1/portfolio` endpoint. Do not remove/re-add that source merely because of the upgrade.

After upgrading the App, open Generic Import Ingress and confirm the existing source appears as one profile with its previous normalized holdings. Its human name can be changed later without changing `provider_id`.

## New Generic Import users

1. Install/update **Portfolio Architect Gateway — Generic Import v1.62.0**.
2. Open its Ingress UI and create a source profile using a human name for the unsupported bank/broker.
3. Configure the mapped CSV columns and import a current holdings CSV. Raw CSV bytes are parsed transiently and are not persisted.
4. Optionally record provider-local available investment cash in EUR. Cash has its own evidence timestamp and is not required for holdings-only overview use.
5. Once validated holdings exist, the profile becomes discoverable through Supervisor.
6. If Portfolio Architect is not configured yet, that ready Generic profile may bootstrap the single PA config entry. If PA already exists, adopt the profile under **Configure → Portfolio sources → Additional REST Gateways → Add discovered REST Gateway** using the Generic App's private bearer token.
7. Repeat **Add source** only when another otherwise unsupported institution should be represented independently.

## Multi-profile rules

- One Generic App supports at most eight profiles.
- Each new profile receives an immutable generated `generic_<stable-id>` provider ID. The user-editable name is presentation only.
- Each profile has independent mapping, normalized holdings, optional cash and evidence clocks.
- A failed import affects only the attempted profile and retains its prior valid canonical snapshot.
- A profile is not discovered until validated holdings are available.
- Remove an adopted Generic provider from Portfolio Architect before deleting its profile in the Generic App. The App deliberately has no HA API permission and cannot do that automatically.

## Compatibility

Portfolio Architect v1.62.0 requests Gateway health schema 10 but retains compatibility with schemas 1–9. Fixed provider Apps remain valid through the established discovery transport schema 1; Generic multi-profile discovery uses additive schema 2 for exact provider-specific paths and human names.

REST portfolio schema 1, payload schema 8 and config-entry schema 12 are unchanged. No dashboard replacement or broker-plan migration is required.

## Live acceptance

For an existing production installation:

1. Update the HACS integration to v1.62.0 and restart Home Assistant.
2. Align installed official Gateway Apps to v1.62.0.
3. Confirm existing Comdirect/DKB/Trade Republic sources remain healthy and unchanged.
4. Open Generic Import and confirm its App badge is no longer Experimental.
5. Create a **synthetic/disposable** Generic profile, import a synthetic holdings CSV and optionally set synthetic cash. Verify holdings/cash evidence timestamps are independent.
6. Confirm the new ready profile appears only as an internal **Add discovered REST Gateway** candidate while the existing PA entry remains the sole integration entry. Do not adopt it into the production source set merely for smoke testing.
7. Rename the profile and confirm the provider ID stays unchanged and the candidate name updates after discovery reconciliation.
8. Delete the disposable profile after confirming it was never adopted. Confirm the discovery candidate disappears and existing production providers remain unchanged.

A destructive standalone-first-install test is not required against a real production config entry; executable regression covers Generic-only bootstrap and multi-profile discovery lifecycle.
