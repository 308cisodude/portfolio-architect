# Portfolio Architect v1.65.0 upgrade and live acceptance

Update the integration and four version-aligned Gateway Apps. Confirm `integration_version`, `engine_version` and App versions read `1.65.0`. A full Home Assistant restart is unnecessary when the integration reloads and both version diagnostics advance. No dashboard import or data migration is required.

In DKB Gateway admin Ingress, use **Refresh read-only shadow snapshot**. Provide your banking login, approve the DKB app challenge, then use the Gateway's Check button. Within five minutes, inspect the FinTS card for a normalized ISIN, quantity, EUR total value, identity evidence and observation UTC time. Compare it yourself with the independent CSV card, accounting for the CSV's date-only export and any intervening price change or trade. Do not copy private position data into PRs or public issues.

After five minutes, confirm that detail expires and the page asks for a manual refresh; the bounded outcome/time may remain. On a failed or ambiguous attempt, confirm no new shadow detail appears. The CSV source must remain the active holdings and cash source throughout. This research acceptance does not authorize automated refresh, credential storage or a source switch.
