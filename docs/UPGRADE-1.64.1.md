# Portfolio Architect v1.64.1 — DKB read-only holdings research

This release adds an isolated, one-shot HKWPD holdings retrieval to DKB admin Ingress after the v1.64.0 authenticated UPD observation succeeded in live acceptance. Enter the **DKB banking Anmeldename and banking password**, not the product registration number or DKB app PIN. Approve login or a separate holdings challenge in the DKB app when prompted; a transient session expires after five minutes.

The request runs only for exactly one UPD-authorized depot. Zero or multiple eligible depots stop without a holdings command. Only the bounded outcome, eligible-depot count, returned-holdings count, numeric return codes and UTC observation time are retained. Raw holdings, identifiers, quantities, values, UPD, account details, credentials, challenges and session cache are not stored or included in status/logs. This is **research only**: no DKB CSV authority, planner input, REST/health schema, fallback policy or other provider changes.

Live acceptance: verify the existing CSV holdings/cash and source authority first; run one holdings observation; record only the bounded fields. A `retrieved` result confirms that the request and library parser returned a list, but does not establish numerical equivalence with the CSV or authorize a future acquisition switch. A second challenge may require a separate approval. If the observation fails, do not repeat bank logins without reviewing the bounded outcome and codes.

Source conflict normalization, the dashboard's direct freshness/execution-evidence blocker explanation, Tactical Tilt and Trade Republic combined CSV remain separate work. v1.65.0 remains the intended conflict-normalization milestone once provider evidence is available.
