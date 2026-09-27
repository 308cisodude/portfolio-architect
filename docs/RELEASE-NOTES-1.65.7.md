# Portfolio Architect v1.65.7 — classify rejected DKB system ID

A successful v1.65.6 read on 2026-09-27 showed `load missing; capture invalid; save skipped; keyed fingerprint unavailable`. v1.65.7 classifies the transient `client.system_id` without disclosing it. The categories are `absent`, `zero_sentinel`, `non_string`, `empty`, `over_limit`, `non_alphanumeric`, and `valid`. The category is held only for the latest manual request in App memory and clears on restart. A later invalid callback cannot overwrite a valid capture.

Storage validation, 72-hour retention, mode 0600, backup exclusions, keyed fingerprint, and cash shadow behavior remain as in v1.65.6. No rejected value is hashed or persisted. FinTS stays read-only manual research; DKB CSV remains the only planner source. The change does not enable automatic cash acquisition or change any wire or dashboard schema.
