# Portfolio Architect v1.60.0

Portfolio Architect v1.60.0 is a narrow **capability-evidence observability** follow-up to the fully live-accepted v1.59.0 acquisition-authority UX. It does not change acquisition authority or any wire schema. Instead, each Gateway Ingress capability card now binds its authority presentation to the evidence clock of the canonical snapshot that is actually being published.

- The common read-only **Acquisition authority** renderer now shows **Authoritative evidence** availability and **Evidence timestamp** for every advertised capability.
- There is **no silent fallback** between acquisition methods; v1.60 adds observability only and does not alter `fallback_policy: none`.
- Evidence timestamps come only from the already-published canonical Gateway snapshot. Inactive staged evidence is deliberately excluded, so a ready alternative method cannot appear authoritative before an explicit provider-local transition publishes it.
- Holdings use the canonical snapshot `generated_at` clock. Cash uses the canonical `investment_cash.as_of` clock (or the legacy reserve timestamp only as compatibility input). Both are rendered in UTC with second precision.
- Comdirect continues to make the explicitly active `live_api` or complete `csv` method authoritative for both holdings and cash. A prepared inactive CSV remains only READY and its staged evidence is not shown as authoritative while live API remains active.
- DKB continues to keep `csv` authoritative for holdings/cash and `fints` research-only/non-activatable. Its independent holdings and Girokonto cash clocks are now visible directly in the authority cards.
- Trade Republic continues to keep `pdf` authoritative for holdings/cash and `live_api` unavailable/non-activatable. Its independent DEPOTAUSZUG and KONTOAUSZUG clocks are now visible directly in the authority cards.
- Generic Import remains experimental, fixed `csv`, holdings-only. Before the first import, the authority card explicitly shows canonical evidence as **NOT AVAILABLE** while the Gateway remains degraded because no snapshot exists.
- The DKB Ingress wording for the independent holdings/cash evidence families is grammatically corrected; semantics are unchanged.
- Health schema 9, health schemas 1–8 compatibility, REST portfolio schema 1, payload schema 8, config-entry schema 12, provider identities, evidence-kind freshness thresholds, LKG/anti-rollback/source-set atomicity, private-PKI HTTPS, bearer authentication, DNS pinning, planner economics and advisory-only boundaries are unchanged.
- No dashboard YAML replacement is required for v1.60.0.

The live-accepted effective authorities remain **Comdirect `live_api`**, **Trade Republic `pdf`**, and **DKB `csv`**. No trading, order, transfer, payment, or transaction-history capability is added. No sell or withdrawal capability is added. Authenticated DKB FinTS remains disabled.

## Retained compatibility contracts

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 9 current; schemas 1–8 remain supported
- config-entry schema 12: unchanged
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- `fallback_policy: none`: mandatory and unchanged
- authenticated DKB FinTS acquisition remains disabled
- verified private-PKI HTTPS, bearer authentication and DNS pinning: unchanged
- holdings/cash freshness evaluation and configured thresholds: unchanged
- historical Comdirect LEGACY package: removed from the active repository in v1.57.0 and remains withdrawn; canonical Comdirect retains the bounded migration receiver only
- Trade Republic statement/PDF parsing remains inside the provider Gateway; this release does not move PDF parsing into Portfolio Architect
- schemas 1–6 remain supported for the earlier health-negotiation compatibility covered by retained regressions
- the historical experimental `v1.19.0-rc2` brokerage probe is not promoted by this release and remains not included in stable runtime
- the v1.33.0 source-freshness and plan-schedule separation remains intact: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold
