# Upgrade to Portfolio Architect v1.60.0

v1.60.0 is an observability-only follow-up to the live-accepted v1.59.0 acquisition-authority UX. It adds authoritative evidence availability and UTC timestamps to the existing capability cards. It does not change provider acquisition, authority, fallback, freshness, portfolio calculations or the private transport boundary.

## Upgrade order

1. Update Portfolio Architect to v1.60.0 and perform the normal Home Assistant restart.
2. Update the installed canonical Comdirect, DKB and Trade Republic Gateway Apps to v1.60.0. Update Generic Import only if it is intentionally installed.
3. Open each Gateway Ingress page and inspect **Acquisition authority**.
4. Confirm the established authority remains unchanged and the new evidence rows match the canonical provider state:
   - Comdirect holdings/cash: authoritative `live_api` on the current production configuration; both capability cards should show available canonical live evidence. A prepared inactive CSV must remain merely READY and must not contribute an authoritative evidence timestamp.
   - DKB holdings/cash: authoritative `csv`; holdings and cash may show different timestamps because their evidence families are intentionally independent. `fints` remains `research_only`, inactive and not activatable.
   - Trade Republic holdings/cash: authoritative `pdf`; DEPOTAUSZUG holdings and KONTOAUSZUG cash may show different timestamps. `live_api` remains unavailable, inactive and not activatable.
   - Generic Import, if intentionally installed: fixed `csv`, holdings-only. With no CSV imported, **Authoritative evidence: NOT AVAILABLE** is expected and the Gateway remains degraded until a valid snapshot exists.
5. Confirm `fallback_policy: none`, the configured freshness policy and planner/cash-routing results remain unchanged.

## What the evidence rows mean

**Authoritative evidence** reports whether the currently published canonical Gateway snapshot contains evidence for that capability. **Evidence timestamp** is the UTC evidence clock carried by that same published snapshot.

The display intentionally does not inspect inactive staged method state. For example, Comdirect can have a complete CSV candidate ready for activation while `live_api` is authoritative. Until the operator explicitly activates CSV and the Gateway publishes the switched canonical snapshot, the capability cards continue to show the live snapshot clocks. This prevents staged evidence from looking like fallback or current authority.

Portfolio Architect freshness policy remains separate. A timestamp being visible does not make stale evidence actionable; the integration still evaluates the configured evidence-kind thresholds independently.

## No migration required

No source reconfiguration, bearer-token change, CA rotation, OAuth bootstrap, CSV/PDF re-import, freshness-threshold change, broker-policy change, or dashboard replacement is required solely because of v1.60.0.

Do not enable or advance authenticated DKB FinTS. The research-only gate is unchanged.

## Generic Import isolated-smoke caution

If Generic Import is installed only for its isolated experimental smoke, do **not** add its discovery card/source to the real Portfolio Architect production source set. That smoke must not alter the real source set; Generic Import should be uninstalled after this standalone smoke test unless it is intentionally being adopted.
