# Portfolio Architect v1.64.2 — DKB research diagnostics

The first live v1.64.1 HKWPD attempt completed its DKB app approval but returned a generic `request_failed`, `eligible depots: 0`, and no return codes. Those fields could not distinguish failure during approval, UPD account discovery or the holdings request. In particular, zero was a placeholder, not evidence that no depot was eligible.

This DKB-only correction persists fixed, allowlisted `failure_stage` and `failure_kind` values for a failed read-only holdings observation. Eligible depots is `not determined` until account discovery succeeds. Numeric return codes remain bounded to 32 four-digit codes. Existing v1.64.1 observations remain readable. No exception message, bank response text, credentials, challenge, account identifier, position, value, or raw UPD is persisted or logged.

The exact exception cause in the previous attempt cannot be recovered. Perform only one new research observation after upgrading, and share the bounded stage, category, eligible count and codes. DKB CSV stays the sole authoritative holdings/cash source. No planner, acquisition mode, REST/health wire schema, fallback behavior or dashboard logic changes.
