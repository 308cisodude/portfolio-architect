# Upgrade to Portfolio Architect v1.2.0

v1.2.0 adds a native Home Assistant investment-plan editor and schedule-aware
freshness while preserving payload schema 8 and existing entity IDs.

## 1. Back up and install

Upload `portfolio-architect-v1.2.0-ha-dropin.zip` to `/config`, then run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.1.1-$stamp"

mkdir -p "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o /config/portfolio-architect-v1.2.0-ha-dropin.zip -d /config
```

The drop-in archive contains only
`custom_components/portfolio_architect/...`; it does not overwrite the CSV or
local portfolio configuration.

## 2. Verify before restarting

```bash
echo '--- manifest ---'
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json

echo '--- integration constant ---'
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py

echo '--- engine version ---'
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py
```

All three values must report `1.2.0`.

Then run:

```bash
ha core check
ha core restart
```

## 3. Configure the investment plan

After Home Assistant has restarted, open:

**Settings → Devices & services → Integrations → Portfolio Architect → Configure
→ Investment plan**

The current `portfolio.yaml` plan is used to preselect instruments and target
weights. Choose:

- plan name;
- budget amount;
- whether the budget applies per period or per execution;
- weekly, monthly, quarterly, or yearly frequency;
- whether to configure an execution schedule;
- 1–32 instruments in scope;
- target weight and purchase eligibility for each instrument.

When scheduling is enabled, also choose the execution days and review lead time.
Weekly schedules use weekdays. Monthly schedules use days 1–28. Quarterly
schedules use one month within each quarter plus days 1–28. Yearly schedules use
one month plus days 1–28.

The flow validates the complete calculated payload before saving. Target weights
must total exactly 100%; the final review step can explicitly normalise them
proportionally.

## 4. Verify schedule-aware freshness

Use Developer Tools → Template:

```jinja
plan_budget:
  {{ states('sensor.portfolio_architect_plan_budget') }}

frequency:
  {{ states('sensor.portfolio_architect_plan_frequency') }}

executions_per_period:
  {{ states('sensor.portfolio_architect_executions_per_period') }}

schedule_configured:
  {{ states('binary_sensor.portfolio_architect_review_schedule_configured') }}

data_fresh:
  {{ states('binary_sensor.portfolio_architect_data_fresh') }}

freshness_mode:
  {{ state_attr('binary_sensor.portfolio_architect_data_fresh', 'freshness_mode') }}

fresh_through:
  {{ state_attr('binary_sensor.portfolio_architect_data_fresh', 'fresh_through') }}
```

With a valid recurring schedule, `freshness_mode` should be `review_schedule`.
The snapshot remains fresh through the calculated review date and becomes stale
on the following local day if no newer CSV evaluation is available.

## 5. Dashboard

The v1.1.1 dashboard remains functional. Replacing the complete raw dashboard
configuration with the v1.2.0 bilingual dashboard adds native tiles for plan
budget, frequency, contribution per execution, and executions per period.

The supplied dashboard is a static native Lovelace reference. Entities for newly
selected instruments are created automatically, but the fixed instrument cards
and Distribution-card entity lists must be updated when the plan scope changes.

## Rollback

Restore the backed-up custom component, run `ha core check`, and restart Home
Assistant. Existing v1.1.1 entities ignore the additional plan options, but do
not edit `.storage` manually.
