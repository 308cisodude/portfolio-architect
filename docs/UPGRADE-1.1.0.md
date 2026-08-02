# Upgrade to v1.1.0

v1.1.0 replaces the command-line transport with a calculation engine bundled
inside the custom integration.

## Safe upgrade order

1. Back up:
   - `/config/configuration.yaml`
   - `/config/custom_components/portfolio_architect`
   - `/config/portfolio-architect`
   - `/config/portfolio/depot.csv`
2. Extract the v1.1.0 HA drop-in into `/config`.
3. Verify the integration, constant, and bundled-engine version markers all
   report `1.1.0`.
4. Run `ha core check` and restart Home Assistant.
5. The existing config entry migrates automatically to:

   ```text
   source_type: local_files
   csv_path: portfolio/depot.csv
   config_directory: portfolio-architect
   ```

6. Verify these entities:
   - `binary_sensor.portfolio_architect_source_healthy` is on;
   - `sensor.portfolio_architect_payload_schema_version` is 8;
   - `sensor.portfolio_architect_version` is 1.1.0.
7. Open the source-health entity and confirm its `source_type` attribute is
   `local_files`.
8. Only after step 7 succeeds, remove the obsolete command-line sensor and old
   external engine files using `CLEANUP-1.1.0.md`.

The dashboard does not need to be replaced. All existing clean entity IDs and
payload schema 8 remain stable.

If automatic migration cannot find the default files, the integration retains
the deprecated source-sensor mode. Use **Settings → Devices & services →
Portfolio Architect → Reconfigure** to select valid local paths, then continue
with cleanup.
