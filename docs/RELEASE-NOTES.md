# Portfolio Architect 1.45.0

Portfolio Architect v1.45.0 is the first provider-acquisition architecture migration release. It moves active DKB depot-CSV acquisition into **Portfolio Architect Gateway — DKB** while preserving the established single-entry Portfolio Architect architecture, canonical provider-neutral REST contract, verified private-PKI transport, and fail-closed source semantics.

## DKB CSV now belongs to the DKB Gateway

The DKB App now accepts an admin-only authoritative batch of up to eight current DKB depot CSV exports. Parsing is provider-specific and stays inside the DKB App. The importer preserves the established DKB semantics: strict UTF-8 semicolon format validation, exact Decimal valuation from price × quantity, newest-export selection per depot, same-date ambiguity rejection, ISIN-first consolidation, quantity preservation, and oldest-selected-export timestamp for conservative freshness.

Raw CSV bytes and DKB depot numbers are transient. They are never written to App-private storage, logs, REST payloads, health documents, Home Assistant entities, or diagnostics. Only the normalized canonical DKB snapshot is persisted with the common Gateway store's restrictive permissions.

Each accepted upload batch replaces the complete DKB holdings snapshot. Multiple depots therefore remain supported without retaining hidden per-depot identity between imports.

The experimental DKB App now auto-starts because its accepted snapshot is an active portfolio source that must survive Home Assistant restarts.

## Exact fail-closed legacy migration

Existing installations may still have HA-side `dkb_csv` supplemental paths. Supervisor discovery of `provider_id: dkb` now routes those installations into a dedicated migration flow instead of suppressing discovery or offering a duplicate source.

The migration requires all of the following before changing configuration:

- the existing primary Gateway is healthy and suitable for multi-Gateway operation;
- the discovered DKB endpoint validates with Supervisor-provided private-CA trust and the App-private bearer token;
- Gateway health schema 6 reports `provider_id: dkb`, healthy status and an available snapshot;
- the fetched REST snapshot matches health timestamp, position count and SHA-256 integrity metadata;
- the legacy DKB CSV files still resolve safely below `/config` and select deterministically;
- canonical WKN/ISIN/name/type/value/quantity holdings match exactly; and
- the DKB Gateway snapshot timestamp exactly matches the legacy aggregate's conservative oldest selected export timestamp.

Only after all checks pass does one config-entry mutation append the verified-HTTPS DKB Gateway and remove the legacy `dkb_csv` paths. A mismatch or any validation failure leaves the old configuration untouched. New PA-side legacy DKB CSV sources are no longer offered through Configure. The old parser remains in v1.45.0 only as the migration verifier and compatibility bridge; its retirement is deliberately deferred until this cut-over is live-proven.

## FinTS remains independent

The registered anonymous DKB FinTS BPD capability probe is unchanged in authority. It remains a research function inside the same DKB App and cannot refresh, replace, or silently fall back to the CSV-backed canonical snapshot. No DKB login name, PIN, TAN, authenticated UPD/holdings call, balance request, order, transfer, payment, debit, withdrawal, transaction-history or other write-capable operation is added.

A future authenticated FinTS acquisition path must still pass its own product-registration and authenticated user-capability gates; authenticated DKB FinTS acquisition remains disabled in v1.45.0.

## Compatibility and unchanged behavior

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported;
- presentation schema 2: unchanged;
- broker schemas 1/2/3: unchanged;
- Comdirect acquisition, OAuth/session maintenance and provider-scoped cash: unchanged;
- Trade Republic `DEPOTAUSZUG`/`KONTOAUSZUG` acquisition: unchanged; this release does not move PDF parsing into Portfolio Architect;
- allocation, drift, policy, recommendation, funding, route economics and execution-path presentation: unchanged;
- the v1.33.0 source-freshness and plan-schedule separation is unchanged: recurring scheduling remains anchored to the latest valid Portfolio Architect evaluation, and v1.45.0 does not change any configured freshness threshold;
- historical presentation sequencing remains documented: the v1.39 colourful allocation view was not included in v1.38.1;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- Home Assistant LKG remains bound to the exact configured source set, so the source-set change becomes authoritative only after successful migration/reload;
- No trading, order, transfer, payment, or transaction-history capability is introduced; sell and withdrawal capability likewise remain absent;
- Portfolio Architect remains advisory-only: no trade or money-movement capability is introduced;
- the historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release;
- the bilingual dashboard is unchanged; no dashboard YAML replacement is required.

## Release engineering

The DKB parser is explicitly registered as provider-specific source in the Gateway App synchronization contract so common-shell synchronization cannot delete it. Regression coverage proves legacy-parser equivalence, batch supersession, conflict rejection, normalized-only persistence, source-migration ordering, no new legacy-source creation, bilingual migration UX and the continuing FinTS boundary.

Protected GitHub workflows remain authoritative for actual provider-App Docker/private-PKI smoke execution when local Docker is unavailable.
