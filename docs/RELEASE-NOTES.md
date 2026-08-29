# Portfolio Architect v1.58.0

Portfolio Architect v1.58.0 introduces a provider-neutral capability-level acquisition-arbitration foundation while preserving the exact production authorities and fail-closed behavior live-accepted on v1.57.0.

- Gateway health schema 9 adds a bounded `acquisition_capabilities` inventory. Each capability names its authoritative acquisition method, the bounded set of methods that can support it, an explicit authority reason, and `fallback_policy: none`.
- Portfolio Architect consumes capability authority read-only for provenance, diagnostics, and operator visibility. It cannot activate or substitute a Gateway acquisition method.
- Comdirect declares both holdings and cash capability support for `live_api` and complete `csv`. The explicitly active Gateway method is authoritative for both capabilities. There is no silent fallback: a prepared CSV never replaces an unavailable configured live API source without an explicit operator method switch.
- DKB keeps `csv` authoritative for holdings and cash. `fints` remains `research_only`, cannot become authoritative, and authenticated DKB FinTS acquisition remains disabled.
- Trade Republic keeps `pdf` authoritative for holdings and cash. Its unavailable `live_api` method cannot become authoritative. This release does not move PDF parsing into Portfolio Architect.
- Generic Import remains an experimental fixed-`csv`, holdings-only Gateway.
- Health schemas 1–8 remain rolling-compatible. Schema 8 retains the established method-level control plane unchanged; capability authority is additive in schema 9.
- Provider acquisition implementations, private-PKI HTTPS, bearer authentication, DNS pinning, evidence clocks/freshness, LKG/anti-rollback behavior, source-set atomicity, and planner economics are unchanged.
- No dashboard YAML replacement is required for v1.58.0.

The live-equivalent authorities remain **Comdirect `live_api`**, **Trade Republic `pdf`**, and **DKB `csv`**. No trading, order, transfer, payment, or transaction-history capability is added. Authenticated DKB FinTS remains disabled.

## Retained compatibility contracts

The v1.58.0 capability-arbitration foundation does not alter the established portfolio/runtime compatibility surface:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 9 current; schemas 1–8 remain supported
- schemas 1–6 remain supported for the earlier health-negotiation compatibility covered by retained regressions
- config-entry schema 12 remains unchanged
- presentation schema 2 remains unchanged
- broker schemas 1/2/3 remain supported
- `fallback_policy: none` remains mandatory; there is no automatic live-to-static acquisition failover
- authenticated DKB FinTS acquisition remains disabled
- Trade Republic statement/PDF parsing remains inside the provider Gateway; this release does not move PDF parsing into Portfolio Architect
- verified private-PKI HTTPS, bearer authentication and DNS pinning are unchanged
- independent holdings/cash evidence clocks and configured freshness thresholds are unchanged
- the historical experimental `v1.19.0-rc2` brokerage probe is not promoted by this release and remains not included in stable runtime
- the historical Comdirect LEGACY package was removed from the active repository in v1.57.0 and remains withdrawn; the historical slug is not reused and canonical Comdirect retains the bounded migration receiver for already-installed supported Legacy instances
- the v1.33.0 source-freshness and plan-schedule separation remains intact: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold
