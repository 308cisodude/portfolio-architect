# Upgrade to v1.0.0

1. Back up `/config/portfolio-architect` and
   `/config/custom_components/portfolio_architect` outside the custom-components
   directory.
2. Extract the v1.0.0 HA drop-in archive into `/config`.
3. Verify that the integration manifest, integration constant, and engine
   `VERSION` file all report `1.0.0`.
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
8. Open **Settings → Devices & services → Portfolio Architect → Configure**.
9. Enter the actual savings-plan execution day (1–28) and leave the review lead
   time at 2 days unless a different lead time is intended.

Until step 9 is completed, Portfolio Architect deliberately leaves the planned
execution and next review unavailable and shows that the review schedule is not
configured. No portfolio, policy, entity-ID, or config-entry migration is
required.
