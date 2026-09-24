# Portfolio Architect v1.64.3 upgrade and live acceptance

Install the integration and aligned Gateway Apps. Confirm `integration_version` and `engine_version` both show `1.64.3` and all App versions align. A Home Assistant restart is unnecessary if the new integration has reloaded and both diagnostics show 1.64.3. No dashboard import or configuration migration is needed.

Confirm DKB CSV holdings and cash remain authoritative. Make exactly one read-only holdings research observation with the personal banking Anmeldename and password; approve the banking-app challenge and check completion in the Gateway. If a separate holdings challenge appears, follow its approval flow. Report only the bounded outcome, eligible-depot count, holdings count, numeric codes and, on failure, stage/category. Do not share account or position details.

A `retrieved` list does not establish numerical parity with CSV and does not authorize an acquisition switch. Review a failed result before any further bank login.
