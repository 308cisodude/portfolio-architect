# Portfolio Architect v1.64.2 upgrade and live acceptance

Install the integration and version-aligned Gateway Apps, then verify integration/engine/App versions. A Home Assistant restart is unnecessary if the integration has already reloaded and both version diagnostics show 1.64.2. No dashboard import or configuration migration is needed.

Confirm that DKB CSV holdings and cash remain authoritative and unchanged. In the DKB App's admin Ingress, enter the personal banking Anmeldename and banking password in **Read-only holdings retrieval research**. Approve the login in the banking app, then use **Check or complete bank approval**. A separate holdings challenge may require another approval. Make one attempt and report only the bounded outcome, failure stage/category, eligible depot count, holdings count, numeric codes and UTC time. Do not copy account or holdings details.

A `retrieved` outcome only means a list returned through the PyFinTS parser; it does not establish equivalence with CSV or authorize live acquisition. If it fails, review the bounded diagnostics before another bank login.
