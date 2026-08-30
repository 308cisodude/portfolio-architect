# Portfolio Architect v1.59.0

Portfolio Architect v1.59.0 turns the health-schema-9 acquisition authority introduced and live-accepted in v1.58.0 into a consistent **operator-facing Gateway Ingress presentation**. The release is presentation-only with respect to acquisition semantics: the provider Gateway remains authoritative, Portfolio Architect remains read-only, and no new provider method or fallback path is added.

- All four official Gateway Ingress UIs now render one common read-only **Acquisition authority** section directly from the validated provider-neutral `AcquisitionControl` model.
- Each capability card shows the authoritative method, authority reason, supported methods with current readiness/active state, and `fallback_policy: none`.
- A common method inventory distinguishes active/authoritative methods from ready-but-inactive alternatives and from unavailable/research-only methods. The established green / blue / amber acquisition-state semantics remain consistent.
- The presentation deliberately exposes no form, button, activation endpoint, or authority-mutating action. Existing Comdirect explicit operator switching remains in its existing provider-local control section and is not moved into the common presentation helper.
- Comdirect still supports holdings/cash through `live_api` and complete `csv`; the explicitly active method remains authoritative. A ready CSV is shown as a ready inactive alternative and cannot silently replace an unavailable live source.
- There is **no silent fallback** between provider acquisition methods.
- DKB still keeps `csv` authoritative for holdings/cash; `fints` remains `research_only`, inactive and non-activatable. Authenticated DKB FinTS acquisition remains disabled.
- Trade Republic still keeps `pdf` authoritative for holdings/cash; `live_api` remains unavailable, inactive and non-activatable.
- Generic Import remains experimental, fixed `csv`, holdings-only.
- Health schema 9, health schemas 1–8 compatibility, REST portfolio schema 1, payload schema 8, config-entry schema 12, provider identities, evidence clocks/freshness, private-PKI HTTPS, bearer authentication, DNS pinning, LKG/anti-rollback/source-set atomicity, planner economics and advisory-only boundaries are unchanged.
- No dashboard YAML replacement is required for v1.59.0.

The live-accepted effective authorities remain **Comdirect `live_api`**, **Trade Republic `pdf`**, and **DKB `csv`**. No trading, order, transfer, payment, or transaction-history capability is added. No sell or withdrawal capability is added.

## Retained compatibility contracts

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 9 current; schemas 1–8 remain supported
- config-entry schema 12: unchanged
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- `fallback_policy: none`: mandatory and unchanged
- authenticated DKB FinTS acquisition remains disabled
- Trade Republic statement/PDF parsing remains inside the provider Gateway; this release does not move PDF parsing into Portfolio Architect
- verified private-PKI HTTPS, bearer authentication and DNS pinning: unchanged
- holdings/cash evidence clocks and configured freshness thresholds: unchanged
- historical Comdirect LEGACY package: removed from the active repository in v1.57.0 and remains withdrawn; canonical Comdirect retains the bounded migration receiver only
- schemas 1–6 remain supported for the earlier health-negotiation compatibility covered by retained regressions
- the historical experimental `v1.19.0-rc2` brokerage probe is not promoted by this release and remains not included in stable runtime
- the v1.33.0 source-freshness and plan-schedule separation remains intact: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold
