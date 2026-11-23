# Portfolio Architect v1.66.4

- Runtime health shows **Retained calculation** when PA is using its last accepted calculation. Its freshness describes that calculation. **Source unavailable** continues to name the Gateway that needs attention.
- The DKB Gateway marks authoritative FinTS evidence **Expired** when its observation reaches 14 days. If an observation is still in range but the Gateway cannot serve the complete FinTS snapshot, its badge says **Not usable for planning**. The last published timestamps remain visible for reference.

This release changes presentation only. The FinTS authority choice, 14-day limit, cash authorization policy and no-fallback behavior remain as configured. See the [upgrade guide](UPGRADE-1.66.4.md) and replace the dashboard YAML to get the new Runtime health tile.
