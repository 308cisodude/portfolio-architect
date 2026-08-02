# Upgrade to Portfolio Architect 1.16.2 release candidate

Version 1.16.2 replaces the failing v1.16.0/v1.16.1 execution options form with
an intentionally conservative two-step flow. It also contains all v1.16.1
reserve-transition and failure-classification corrections.

No Gateway reauthentication, account rediscovery, account reselection,
dashboard replacement, configuration migration, or entity migration is
required.

## 1. Update the integration

Upload `portfolio-architect-v1.16.2-ha-dropin.zip` to `/config`, back up the
current custom component and Portfolio Architect data directory, extract the
archive over `/config`, run `ha core check`, and restart Home Assistant.

After restart, open:

**Settings → Devices & services → Portfolio Architect → Configure → Execution and transaction costs**

The first form configures policy and reserve behaviour. Selecting **Next** opens
the manual-order cost model. The venue charge is entered in basis points:

```text
0.25 basis points = 0.0025%
```

The default values therefore reproduce the observed Comdirect Tradegate charge
without reducing stored precision.

## 2. Gateway App

The Gateway runtime and public REST contract are unchanged. The v1.16.2 App
archive exists for release parity only. Updating it in place is optional.

Do not uninstall the App or remove App data. The selected investment account and
all authentication state remain valid.

## 3. Dashboard

The v1.16.0 dashboard remains valid and does not need replacement.

## 4. Verify

Confirm:

- `sensor.portfolio_architect_version` reports `1.16.2`;
- both execution configuration steps open and save;
- source health returns to live operation after the integration reload;
- the available reserve matches the selected Comdirect account;
- estimated cash outlay does not exceed the reserve;
- no account identity appears in Home Assistant.

## Rollback

Disable cost-aware execution, restore the latest v1.16.0 or v1.16.1 integration
backup, run `ha core check`, and restart Home Assistant. No Gateway or data
rollback is required.
