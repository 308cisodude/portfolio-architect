# Portfolio Architect Gateway — Generic Import v1.55.1

Version 1.55.1: Version alignment only for the v1.55.1 Comdirect migration hotfix; Generic Import CSV behavior and experimental maturity are unchanged.

Version 1.55.0 keeps Generic Import's fixed `csv` method and transient mapped-CSV boundary unchanged. Accepted canonical CSV snapshots remain servable with their original evidence timestamp instead of expiring under a separate Gateway cache TTL; Portfolio Architect decides freshness.
Version 1.53.0 adds the provider-neutral health-schema-8 control-plane representation for the fixed `csv` acquisition method. Generic Import remains a single-method provider-neutral escape hatch; mapped-CSV parsing, transient raw input, canonical holdings-only persistence and verified private-PKI transport are unchanged.

The Generic Import Gateway is the provider-neutral escape hatch for holdings sources that do not have a dedicated Portfolio Architect provider Gateway. It accepts one explicitly mapped CSV through Home Assistant's admin-only Ingress UI and publishes only the resulting canonical schema-1 portfolio snapshot over the same authenticated verified-HTTPS boundary as the official provider Gateways.

The raw CSV is transient and is never persisted. Only normalized position facts, one bounded mapping configuration, import-time evidence, and privacy-safe operational diagnostics survive in the App-private `/data` volume. The provider identity is fixed to `generic_csv`; the Gateway cannot impersonate Comdirect, DKB, Trade Republic, or any other provider.

The importer supports the established mapped-CSV contract: bounded UTF-8/Latin-1-compatible encodings, comma/semicolon/tab delimiter selection or auto-detection, a bounded header row, comma/dot/auto decimal parsing, required identifier/name/value columns, and optional ISIN/type/currency columns. When a currency column is mapped every populated row must explicitly be EUR/€; no currency conversion is performed.

Because a generic CSV contains no authoritative institution-issued timestamp, the successful import dispatch time is the holdings evidence timestamp. Uploading a file is therefore an explicit operator attestation that the imported values represent the current source evidence.

This App is read-only toward Portfolio Architect. It has no bank credentials, live API, order, transfer, payment, transaction-history, sell, or withdrawal capability.
