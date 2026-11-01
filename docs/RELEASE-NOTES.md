# Portfolio Architect v1.66.2

The source diagnostic now describes instrument-type findings rather than calling them identity conflicts. When one source lacks a type, the dashboard shows a bounded summary such as **2 unspecified types**. If sources supply two different known types, the detail classifies that as a known-type conflict. The existing diagnostic entity ID and count remain available.

This presentation uses already validated source metadata, including older cached calculations. It does not change ISIN/WKN identity matching, portfolio values, planning, DKB FinTS authority or its 14-day evidence limit, or the user-set EUR 0 DKB investment-cash cap. No manual bank read or configuration migration is required. Replace the English, German or combined dashboard YAML to see the new label and summary. See the [full notes](RELEASE-NOTES-1.66.2.md) and [upgrade guide](UPGRADE-1.66.2.md).

When a source outage makes PA retain a prior calculation, the plan blocker now names the unavailable Gateway and clearly labels old dates as belonging to that retained calculation. An independently refreshed Gateway is no longer called stale based on the old calculation. A fresh DKB manual read is still required to restore planning after its FinTS evidence expires.
