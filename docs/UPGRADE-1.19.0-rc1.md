# Upgrade to Portfolio Architect 1.19.0-rc1

Version 1.19.0-rc1 is an experimental release candidate for controlled Comdirect
fee probing. It is not a stable HACS update and must not replace v1.18.0 as the
known-good baseline until live acceptance is complete.

## 1. Back up

Create a Home Assistant backup and retain the published v1.18.0 integration,
Gateway App, and dashboard artifacts. Do not uninstall the Gateway App and do not
remove `/data` or its App-private authentication state.

## 2. Update the integration

Install the v1.19.0-rc1 integration from the prerelease asset or extract
`portfolio-architect-v1.19.0-rc1-ha-dropin.zip` over `/config`.

Before restarting, verify:

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py
find /config/custom_components/portfolio_architect -type f -name manifest.json -print
```

All three version markers must report `1.19.0-rc1`, and exactly one integration
manifest must exist. Then run:

```bash
ha core check && ha core restart
```

After restart, confirm Portfolio Architect remains live and the v1.18.0 decision
trace remains available.

## 3. Update the Gateway App in place

The Gateway update is required for both experimental probes. Update it in place so
credentials, OAuth/session state, cached snapshot, bearer token, and selected
investment account remain intact.

```bash
ha apps stop local_portfolio_architect_gateway

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/gateway-v1.18.0-$stamp"
archive="/config/portfolio-architect-gateway-app-v1.19.0-rc1.zip"

mkdir -p -- "$backup"
cp -a -- /addons/portfolio_architect_gateway "$backup/portfolio_architect_gateway"
unzip -o "$archive" -d /addons && rm -f -- "$archive"

ha store reload
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
sleep 5
ha apps info local_portfolio_architect_gateway \
  | grep -E '^(stage|state|version|version_latest):'
ha apps logs local_portfolio_architect_gateway | tail -40
```

Expected package state:

```text
stage: experimental
state: started
version: 1.19.0-rc1
```

A new PhotoTAN bootstrap is required only if Comdirect rejects the existing
bank-issued session.

## 4. Replace the dashboard YAML

Replace the complete raw dashboard configuration with
`portfolio-architect-v1.19.0-rc1-bilingual-dashboard.yaml`.

The new **Order identifiers / Orderkennungen** block appears only while at least one
purchase is recommended. It renders the current recommended-buy ISINs as selectable
text. The v1.18.0 decision-trace tile remains unchanged. No restart is required
after saving the dashboard.

## 5. Optional fee-review metadata

Fee freshness remains disabled unless `fee_verification_max_age_days` is present in
`broker.yaml`. A conservative initial value is 90 days:

```yaml
broker:
  fee_verification_max_age_days: 90
```

For every target instrument, record the last human-confirmed fee evidence:

```yaml
fee_pct: 1.5
fee_verified_at: 2026-08-03
fee_source: manual_comdirect_verification
```

The probe never edits these values automatically.

## 6. Run the controlled probes

Open the **Portfolio Architect Gateway** App Web UI.

For one ETF currently shown by Comdirect as promoted and one ETF shown with the
regular savings-plan fee:

1. enter the ISIN and select **Probe fundFlags and venues**;
2. inspect the opaque `fundFlags` and eligible public venues;
3. select a masked depot, venue, and a small positive unit quantity;
4. request the ex-ante ordinary-order cost indication;
5. open or save the sanitized JSON result;
6. clear the result before testing another instrument.

The page must always state:

```text
No order is validated or submitted.
This is an ordinary BUY/MARKET order indication, not a savings-plan quotation.
```

Do not use the result as evidence of ETF-Special status until promoted and regular
samples show a reproducible difference.

## 7. Verify the safety boundary

Confirm:

- `/api/v1/portfolio` and `/healthz` are unchanged;
- no probe data appears in Home Assistant entities or diagnostics;
- the sanitized result contains no depot ID, venue ID, customer/account data,
  session material, or raw upstream response;
- normal scheduled portfolio refreshes do not execute a probe;
- no order validation, quote, TAN, submission, modification, or cancellation occurs.

## Rollback

Restore v1.18.0 through HACS or its manual drop-in, restore the v1.18.0 dashboard,
and restore/update the Gateway App from the published v1.18.0 package. Run
`ha core check` and restart Home Assistant. No configuration, portfolio, decision-
trace, credential, session, selected-account, or REST-schema migration must be
reversed. Remove the optional fee-verification fields only if the additional policy
finding is not desired.
