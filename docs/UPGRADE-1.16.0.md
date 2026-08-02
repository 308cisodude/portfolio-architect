# Upgrade to Portfolio Architect 1.16.0 release candidate

Version 1.16.0 adds opt-in cost-aware execution and an optional live investment
reserve supplied by the Comdirect Gateway App. Upgrade the integration and
Gateway App before enabling the new policy. Existing recommendation behavior is
unchanged until cost-aware execution is explicitly enabled.

## 1. Update the integration

Upload `portfolio-architect-v1.16.0-ha-dropin.zip` to `/config`, then run:

```bash
cd /config
stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.15.0-$stamp"
archive="/config/portfolio-architect-v1.16.0-ha-dropin.zip"

mkdir -p -- "$backup"
cp -a -- /config/custom_components/portfolio_architect "$backup/custom-component"
if [ -d /config/portfolio-architect ]; then
  cp -a -- /config/portfolio-architect "$backup/portfolio-data"
fi

unzip -o "$archive" -d /config \
  && rm -f -- "$archive"

grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py

ha core check && ha core restart
```

All three version markers must report `1.16.0`.

## 2. Update the Gateway App in place

The Gateway update is required for `gateway_balance` reserve mode. Do not
uninstall the App and do not remove its private data.

Upload `portfolio-architect-gateway-app-v1.16.0.zip` to `/config`, then run:

```bash
ha apps stop local_portfolio_architect_gateway

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/gateway-v1.15.0-$stamp"
archive="/config/portfolio-architect-gateway-app-v1.16.0.zip"

mkdir -p -- "$backup"
cp -a -- /addons/portfolio_architect_gateway "$backup/portfolio_architect_gateway"

unzip -o "$archive" -d /addons \
  && rm -f -- "$archive"

ha store reload
ha apps info local_portfolio_architect_gateway \
  | grep -E '^(state|stage|version|version_latest):'
```

Proceed when `version_latest: 1.16.0` appears:

```bash
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
sleep 5

ha apps info local_portfolio_architect_gateway \
  | grep -E '^(state|stage|version|version_latest):'
ha apps logs local_portfolio_architect_gateway | tail -40
```

## 3. Select the dedicated investment account

Open the **Portfolio Architect Gateway** Web UI.

1. Complete another PhotoTAN bootstrap when Comdirect requires it.
2. Select **Discover eligible EUR accounts**.
3. Identify the dedicated settlement account from its masked type and final four
   characters.
4. Select it explicitly.
5. Confirm the displayed conservative reserve. It is the lower of current cash
   balance and available cash, not an overdraft or credit limit.

The browser receives only a masked label, balance, timestamp, and a random
short-lived selection token. The public REST snapshot receives only the reserve
amount and timestamp.

## 4. Replace the dashboard YAML

Replace the complete raw dashboard configuration with
`portfolio-architect-v1.16.0-bilingual-dashboard.yaml`. No restart is required.

## 5. Enable cost-aware execution

Reload Portfolio Architect once, then open:

**Settings → Devices & services → Portfolio Architect → Configure → Execution and transaction costs**

Recommended initial acceptance settings:

```text
Cost-aware execution:       enabled
Execution policy:           Balanced
Maximum cost ratio:         1.50%
Maximum deferral periods:   3
Maximum orders:             1
Investment reserve source:  Selected Gateway account balance
```

Review the manual-order fee profile against the current broker conditions and
review every savings-plan fee in `broker.yaml`. The configured values are
estimates, not a broker order preview.

## 6. Verify

Confirm:

```text
Version:                    1.16.0
Source healthy:             on
Operating mode:             Live
Investment reserve source:  Gateway balance
Available reserve:          matches the selected account
Execution policy:           Balanced
Cash required:              principal + estimated fees
```

For a paid percentage savings plan, the displayed cash requirement is the gross
savings rate and the proposed buy is the net invested principal. For a manual
order, estimated fees are added to the proposed order principal.

Do not execute a recommendation while the source is unavailable or the reserve
cannot be confirmed. Treat this build as a release candidate until the live
account and recommendation semantics have been accepted.

## Rollback

Disable cost-aware execution first, restore the v1.15.0 component and dashboard,
run `ha core check`, and restart Home Assistant. Restore the Gateway source backup
only if required; do not delete App-private data.
