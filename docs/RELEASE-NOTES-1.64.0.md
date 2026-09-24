# Portfolio Architect v1.64.0 release notes

v1.64.0 extends only the DKB Gateway research gate with one-shot authenticated FinTS dialog and bounded UPD/user-capability observation. Credentials are transient in the App; only sanitized capability evidence persists. A DKB app confirmation or login TAN can complete the authenticated dialog; pending or failed approval remains inconclusive. The DKB CSV acquisition path remains authoritative and FinTS remains research-only, with no business transaction operation.

The prior anonymous BPD 29 observation is retained as a sanitized fixture. Other Gateway Apps and Portfolio Architect runtime are version-aligned without behavioral changes. All established schemas, trust, privacy, planner, freshness and source-arbitration contracts remain unchanged. See `docs/UPGRADE-1.64.0.md` for the live checkpoint.
