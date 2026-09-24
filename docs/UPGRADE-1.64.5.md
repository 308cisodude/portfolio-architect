# Portfolio Architect v1.64.5 upgrade and live acceptance

Update the integration and version-aligned Gateway Apps. Confirm integration, engine and App versions are 1.64.5. A Home Assistant restart is unnecessary if the integration reloads and diagnostics advance. No dashboard import or configuration migration is needed.

With a current DKB CSV import, perform one read-only holdings research request through DKB Gateway admin Ingress. Approve the bank challenge, then use the Gateway's check button. Within five minutes, inspect the stacked CSV and FinTS tables. In particular, record whether the parsed ISIN is absent, what the bounded bank instrument field actually contains, and whether the total-value currency was captured. The unit price currency is a different field. A missing or unfamiliar identifier remains unresolved; do not infer it from the matching quantity or close numeric values. Share only general observations, not raw position details.

CSV remains the sole authoritative holdings and cash source. The transient view disappears after five minutes or App restart; no FinTS acquisition switch is authorized by this review.
