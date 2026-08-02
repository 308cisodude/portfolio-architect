# Upgrade to v0.9.0

1. Back up `/config/portfolio-architect`, the custom component and dashboard YAML.
2. Extract the v0.9.0 drop-in archive into `/config`.
3. Add `holdings` to the command-line sensor `json_attributes` list:

   ```yaml
   json_attributes:
     - summary
     - holdings
     - recommendations
     - policy_findings
   ```

4. Verify `manifest.json`, `const.py` and `portfolio-architect/VERSION` all report
   `0.9.0`.
5. Restart Home Assistant and update `sensor.portfolio_architect`.
6. Confirm `sensor.portfolio_architect_portfolio_value` equals the complete depot
   value and `sensor.portfolio_architect_outside_scope_position_count` is available.
7. Replace the complete dashboard YAML with the v0.9.0 bilingual dashboard.

The drop-in archive does not overwrite local portfolio, policy, broker, instrument,
exception or depot files.

Existing zero-target rows in `portfolio.yaml` may remain temporarily: v0.9.0 treats
them as outside current plan scope. Removing them later is recommended because the
positive-weight allocation list is now the complete plan definition.
