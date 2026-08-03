# Upgrade to Portfolio Architect 1.18.0

Version 1.18.0 adds a private two-evaluation Plan Delta & Decision Trace and one
new Home Assistant enum sensor. Portfolio calculations, source adapters,
configuration, target corridor, policy semantics, execution model, and Gateway
protocols remain compatible.

## 1. Update through HACS

Open **HACS → Integrations → Portfolio Architect**, install version `1.18.0`, and
wait for **Pending restart**.

Before restarting, verify:

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py
find /config/custom_components/portfolio_architect -type f -name manifest.json -print
```

All three markers must report `1.18.0`, and exactly one integration manifest must
exist. Then run:

```bash
ha core check && ha core restart
```

For a manual installation, extract
`portfolio-architect-v1.18.0-ha-dropin.zip` over `/config`, run the same checks,
and restart Home Assistant.

## 2. Establish the trace

After the first fresh validated evaluation,
`sensor.portfolio_architect_plan_change` reports `baseline_established`. The next
fresh evaluation compares against that baseline. A REST last-known-good replay
is deliberately ignored and cannot create a false change.

Do not edit the new private `.storage` document manually. It contains only two
bounded provider-neutral snapshots and is revalidated on every restore.

## 3. Replace the dashboard YAML

The existing v1.16.3-v1.17.2 dashboard remains operational. Replace the complete
raw dashboard configuration with
`portfolio-architect-v1.18.0-bilingual-dashboard.yaml` to add the conditional
**Changes since previous evaluation / Änderungen seit letzter Auswertung** tile.
No additional restart is required after saving the dashboard.

The tile is hidden for the initial baseline, unchanged evaluations, and
unavailable state. Selecting it opens the native more-info dialog with bounded
reason codes and previous/current decision values.

## 4. Gateway App

No Gateway update is required. Gateway App 1.16.1 and later remain compatible.
The v1.18.0 Gateway archive changes release metadata only. Do not uninstall the
App or remove App-private data.

## 5. Verify

Confirm:

- `sensor.portfolio_architect_version` reports `1.18.0`;
- `sensor.portfolio_architect_plan_change` exists;
- the first fresh evaluation establishes a baseline;
- a later fresh evaluation reports either `unchanged` or a bounded change state;
- live or last-known-good portfolio operation remains healthy;
- the dashboard is unchanged except for the optional conditional trace tile.

## Rollback

Redownload v1.17.2 through HACS or restore its manual integration backup, run
`ha core check`, and restart Home Assistant. Restore the previous dashboard YAML
or remove the new plan-change tile because v1.17.2 does not provide that entity.
No portfolio, Gateway, or configuration migration must be reversed.
