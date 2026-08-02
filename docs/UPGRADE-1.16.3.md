# Upgrade to Portfolio Architect 1.16.3

Version 1.16.3 is a Home Assistant integration and dashboard UX update. It preserves
the v1.16.2 cost-aware execution configuration, selected Comdirect investment
account, recommendation logic, payload schema 8, and all existing entity IDs.

## 1. Update the integration

Upload `portfolio-architect-v1.16.3-ha-dropin.zip` to `/config`, back up the existing
custom component and Portfolio Architect data directory, extract over `/config`, run
`ha core check`, and restart Home Assistant.

## 2. Replace the dashboard YAML

Replace the complete raw Portfolio Architect dashboard configuration with
`portfolio-architect-v1.16.3-bilingual-dashboard.yaml`. No restart is required.

The dashboard now displays a precise execution state instead of the ambiguous
**Plan not ready** tile and uses the terms **Available investment cash** and
**Cash after recommended purchases**.

## 3. Gateway

No Gateway update is required. The Gateway runtime and REST contract are unchanged;
an installed Gateway App v1.16.1 or later remains compatible. Do not rediscover or
reselect the dedicated investment account.

## 4. Verify

With cost-aware execution enabled and insufficient account cash, expect:

```text
Execution state: Waiting for investment cash
Available investment cash: current usable account balance
Additional investment cash required: positive amount
Purchases: 0
```

When a recommendation becomes executable, the state changes to **Ready to invest**
and **Cash after recommended purchases** shows the projected remaining cash.
