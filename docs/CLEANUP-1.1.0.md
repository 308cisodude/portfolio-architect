# Home Assistant cleanup after v1.1.0

Perform this cleanup only after the Portfolio Architect source-health entity
reports `source_type: local_files` and the dashboard is populated.

## 1. Back up the current configuration

```bash
stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "/config/portfolio-architect-backups/v1.1-cleanup-$stamp"
cp -a /config/configuration.yaml \
  "/config/portfolio-architect-backups/v1.1-cleanup-$stamp/"
cp -a /config/portfolio-architect \
  "/config/portfolio-architect-backups/v1.1-cleanup-$stamp/portfolio-architect"
```

## 2. Remove the active command-line sensor

Edit `/config/configuration.yaml` and remove only the complete Portfolio
Architect item below the existing `command_line:` key. Do not remove unrelated
command-line entities.

The obsolete item is the one containing:

```yaml
name: Portfolio Architect
unique_id: portfolio_architect
```

If it was the only item, remove the now-empty `command_line:` key as well.

## 3. Remove obsolete supporting configuration

The following file was a reference copy and can be deleted:

```bash
rm -f /config/configuration/command-line-sensor.yaml
```

Remove the Recorder exclusion for `sensor.portfolio_architect` if it exists and
was used only for the old source sensor. The native Portfolio Architect entities
are small and Recorder-safe.

## 4. Remove the old external engine, keep the data YAML

```bash
rm -rf /config/portfolio-architect/portfolio_architect
rm -f \
  /config/portfolio-architect/run.py \
  /config/portfolio-architect/VERSION \
  /config/portfolio-architect/requirements.txt \
  /config/portfolio-architect/error.log
```

Keep these user-owned files:

```text
portfolio.yaml
policy.yaml
instruments.yaml
broker.yaml
exceptions.yaml
```

## 5. Validate and restart

```bash
ha core check
ha core restart
```

After restart, the obsolete `sensor.portfolio_architect` command-line entity may
remain as an unavailable registry entry. It can be removed from **Settings →
Devices & services → Entities** after confirming no automation uses it.

## Optional consolidation

To keep all Portfolio Architect data in one folder, first copy the CSV:

```bash
cp -a /config/portfolio/depot.csv /config/portfolio-architect/depot.csv
```

Then use **Portfolio Architect → Reconfigure** and set the CSV path to:

```text
portfolio-architect/depot.csv
```

Verify a successful refresh before deleting the old `/config/portfolio`
directory. Never move or delete a source file before reconfiguring and testing
the integration.
