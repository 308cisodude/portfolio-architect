# Portfolio Architect v1.65.2 — manual DKB Girokonto booked-balance research

The DKB Gateway can make one manual, read-only FinTS HKSAL balance request after banking-app approval. The administrator enters the final four digits of the intended Girokonto IBAN; the request proceeds only if exactly one EUR, balance-capable UPD account matches. No account identifier or suffix is stored or displayed.

The five-minute admin review shows the DKB CSV's explicit Kontostand and timestamp beside FinTS's booked amount, bank balance date, and observation time. These observations are presented for human review without an automatic match or plausibility verdict. A booked balance is not an available balance or investment authorization.

A complete EUR response replaces a bounded App-private shadow containing booked amount, currency, bank date, and observed UTC. The status exposes only recent/old observation state and dates; amounts remain private. A failed or incomplete refresh preserves the previous shadow. The research shadow survives an App restart and becomes old after 24 hours, independently of the bank balance date. Reconfiguring the FinTS registration clears it. Credentials, account IDs, TANs, and raw responses are not persisted.

DKB cash CSV remains the sole planner cash source. There is no automatic polling, source selection, money movement, or change to the holdings shadow. The Gateway UI still labels live FinTS acquisition unavailable and research only.
