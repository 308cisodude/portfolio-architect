# Portfolio Architect v1.66.3

Trade Republic now has one **Import TR statement** uploader. It recognizes the supported German `VERMÖGENSÜBERSICHT` net worth format, the legacy `DEPOTAUSZUG` portfolio statement, and the existing cash statement. The combined format publishes Brokerage holdings and the Cashkonto balance together only after section dates, position count, Brokerage subtotal, cash detail/overview and overall totals reconcile. Crypto is explicitly excluded. Standalone statements update their own capability only.

Combined date-only evidence is conservatively observed at the beginning of the statement day in Europe/Berlin, converted to UTC; document creation time does not invent an intraday balance time. Older capability evidence is rejected. Existing holdings/cash status remains separate. The canonical snapshot commits both capabilities in one atomic file replacement; existing separate cash state remains a legacy/bootstrap input, never an override of newer canonical cash.

The Marketplace README now has a compact overview and branded banner. Installation guidance covers Marketplace on HA 2026.11+ and HACS on older supported HA versions. Marketplace displays the README from the installed PA release, so the revised page appears after this update.

No DKB refresh, source-authority switch, new API access, order placement, money movement or credential retention is introduced. DKB's fixed 14-day expiry and configured zero cash cap remain unchanged. Uploaded PDFs and extracted text remain transient; only normalized provider snapshots persist. Public tests use synthetic documents only.
