# Upgrade to v0.9.1

1. Back up `/config/portfolio-architect` and
   `/config/custom_components/portfolio_architect` outside the custom-components
   directory.
2. Extract the v0.9.1 HA drop-in archive into `/config`.
3. Verify that the integration manifest, integration constant, and engine
   `VERSION` file all report `0.9.1`.
4. Confirm that the active command-line sensor configuration includes:

   ```yaml
   json_attributes:
     - summary
     - holdings
     - recommendations
     - policy_findings
   ```

5. Run `ha core check`, then restart Home Assistant.
6. Update `sensor.portfolio_architect` and verify that `holdings` is present.
7. Replace the complete dashboard raw YAML with
   `dashboard/bilingual-dashboard.yaml`.

No entity migration, config-entry migration, or schema migration is required.
