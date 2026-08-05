# Upgrade to Portfolio Architect 1.19.0-rc2

Version 1.19.0-rc2 corrects the rc1 dashboard defects and incorporates the live
Comdirect acceptance findings. It remains an experimental prerelease; v1.18.0 stays
the stable known-good baseline.

## 1. Back up

Create a Home Assistant backup and retain the published v1.18.0 and rc1 integration,
Gateway App, and dashboard artifacts. Do not uninstall the Gateway App or remove
its App-private `/data` state.

## 2. Update the integration

Install the rc2 prerelease asset or extract
`portfolio-architect-v1.19.0-rc2-ha-dropin.zip` over `/config`.

Before restarting, verify:

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py
find /config/custom_components/portfolio_architect -type f -name manifest.json -print
```

All three markers must report `1.19.0-rc2`, and exactly one integration manifest
must exist. Then run:

```bash
ha core check && ha core restart
```

After restart, confirm the live portfolio, decision trace, and Gateway health entities
remain available.

## 3. Update the Gateway App in place

The rc2 App updates release metadata and the Ingress diagnostic wording. Preserve
credentials, OAuth/session state, cached snapshot, bearer token, and selected
investment account by updating in place.

```bash
ha apps stop local_portfolio_architect_gateway

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/gateway-v1.19.0-rc1-$stamp"
archive="/config/portfolio-architect-gateway-app-v1.19.0-rc2.zip"

mkdir -p -- "$backup"
cp -a -- /addons/portfolio_architect_gateway "$backup/portfolio_architect_gateway"
unzip -o "$archive" -d /addons

ha store reload
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
sleep 5
ha apps info local_portfolio_architect_gateway \
  | grep -E '^(stage|state|version|version_latest):'
ha apps logs local_portfolio_architect_gateway | tail -40
```

Expected:

```text
stage: experimental
state: started
version: 1.19.0-rc2
version_latest: 1.19.0-rc2
```

A new PhotoTAN bootstrap is required only if Comdirect rejects the existing session.

## 4. Replace the complete dashboard YAML

Replace the complete raw dashboard configuration with
`portfolio-architect-v1.19.0-rc2-bilingual-dashboard.yaml`. No restart is required.

Verify while at least one purchase is recommended:

```text
Normal tap on purchase tile:  opens the ISIN
Long press on purchase tile:  opens the purchase explanation
Order identifiers card:       lists only positive recommended buys
```

## 5. Optional fee-review metadata

Fee freshness remains disabled unless `fee_verification_max_age_days` is configured:

```yaml
broker:
  fee_verification_max_age_days: 90
```

A target instrument can record the last human-confirmed evidence:

```yaml
fee_pct: 1.5
fee_verified_at: 2026-08-04
fee_source: manual_comdirect_verification
```

The diagnostics never edit these values automatically.

## 6. Diagnostic interpretation

The instrument metadata operation is now labelled **Read instrument metadata and
venues**. Live rc1 acceptance found no usable distinction between a confirmed 0%
and a regular 1.5% savings-plan ETF in `fundFlags`, fund status, or surcharge fields.

The ex-ante operation remains available only as an ordinary-order cost diagnostic.
The page and JSON must state:

```text
No order is validated or submitted.
This is an ordinary BUY/MARKET order indication, not a savings-plan quotation.
```

Do not use either diagnostic to infer current ETF-Special or savings-plan promotion
status.

## 7. Safety verification

Confirm:

- `/api/v1/portfolio` and `/healthz` are unchanged;
- diagnostic data does not appear in Home Assistant entities or diagnostics;
- sanitized JSON contains no depot ID, venue ID, customer/account data, session
  material, or raw upstream response;
- scheduled refreshes do not execute diagnostics;
- no order validation, quote, TAN, submission, modification, or cancellation occurs.

## Rollback

Restore v1.18.0 or rc1 through its integration package, dashboard, and Gateway App
archive. Run `ha core check` and restart Home Assistant. No configuration, portfolio,
decision-trace, credential, session, selected-account, or REST-schema migration must
be reversed.
