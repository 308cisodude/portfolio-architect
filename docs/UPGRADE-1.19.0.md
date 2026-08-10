# Upgrade to Portfolio Architect 1.19.0

Version 1.19.0 introduces Gateway-side authorization of investment cash. Existing
Comdirect installations preserve their previous behavior automatically: when no
cash-policy file exists, the Gateway uses `all_available` and authorizes all
eligible non-borrowed cash.

## Recommended update order

1. Update the Portfolio Architect Gateway App to 1.19.0 through **Settings → Apps**.
2. Update Portfolio Architect to 1.19.0 through HACS.
3. Restart Home Assistant when HACS reports **Pending restart**.

The REST extension is additive, so the opposite order is also safe.

## Configure the Gateway policy

Open the Portfolio Architect Gateway App Web UI and review **Investment cash
authorization**.

For the existing Comdirect use case, leave:

```text
Authorization policy: All eligible cash
```

To restrict a Gateway to a fixed amount, select **Cap eligible cash** and enter a
canonical EUR amount such as `100` or `100.00`. A capped policy with a missing or
invalid cap is rejected; malformed persisted policy state fails closed during
snapshot refresh.

Changing the policy triggers a live refresh. No PhotoTAN reauthentication or
investment-account reselection is required merely because of this upgrade.

## Expected Home Assistant result

The existing entity ID remains:

```text
sensor.portfolio_architect_available_investment_reserve
```

Its display name becomes **Authorized investment cash**. With Gateway 1.19.0 it
also exposes attributes for:

- selected account balance;
- eligible investment cash;
- authorization policy;
- optional authorization cap.

The sensor state itself is the amount Portfolio Architect may allocate. It is
never the unrestricted raw balance when a cap is active.

## Compatibility and rollback

REST schema remains version 1 and Gateway health remains schema 5. The legacy
`investment_reserve.available_eur` value is retained and equals the authorized
amount. This allows a 1.19.0 Gateway to work with the immediately preceding
Portfolio Architect release and allows Portfolio Architect 1.19.0 to work with
older supported Gateways.

Rollback to 1.18.2 ignores the additive authorization metadata. If a capped policy
has been configured in Gateway 1.19.0, the Gateway continues publishing the capped
authorized amount through the legacy reserve field while that Gateway version is
running.

DKB CSV imports are unaffected because they do not supply investment cash.
