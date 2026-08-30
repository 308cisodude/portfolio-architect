# Upgrade to Portfolio Architect v1.59.0

v1.59.0 is an operator-UX release on top of the live-accepted health-schema-9 capability authority from v1.58.0. It does not change provider acquisition, authority, fallback, freshness, portfolio calculations or the private transport boundary.

## Upgrade order

1. Update Portfolio Architect to v1.59.0 and perform the normal Home Assistant restart.
2. Update the installed canonical Comdirect, DKB and Trade Republic Gateway Apps to v1.59.0. Update Generic Import only if it is intentionally installed.
3. Open each Gateway Ingress page and confirm the new **Acquisition authority** section appears.
4. Confirm the capability and method presentation matches the established authority:
   - Comdirect holdings/cash: authoritative `live_api` on the current production configuration; complete `csv` may be ready but remains inactive unless explicitly selected by the operator; fallback `none`.
   - DKB holdings/cash: authoritative `csv`; `fints` remains `research_only`, inactive and not activatable; fallback `none`.
   - Trade Republic holdings/cash: authoritative `pdf`; `live_api` remains unavailable, inactive and not activatable; fallback `none`.
   - Generic Import, if intentionally installed: fixed `csv`, holdings-only.
5. Confirm Portfolio Architect remains healthy with the same configured provider set, freshness policy and planner/cash-routing results.

## What the new presentation means

The common section is deliberately **read-only**. “Supported” means that a method belongs to the provider capability model; it does not mean that the method is currently ready, active or authoritative. Read the method-state badge and the capability's **Authoritative method** together.

Green means active/authoritative, blue means ready but inactive, and amber means unavailable, not-ready or research-only. `Automatic fallback: none` remains the operative safety rule.

Comdirect retains its existing explicit provider-local method activation controls. The common authority section does not add another switch path and Portfolio Architect itself cannot remotely activate acquisition methods.

## No migration required

No source reconfiguration, bearer-token change, CA rotation, OAuth bootstrap, CSV/PDF re-import, freshness-threshold change, broker-policy change, or dashboard replacement is required solely because of v1.59.0.

Do not enable or advance authenticated DKB FinTS merely because the UI now shows the research-only method alongside CSV. Real provider capability evidence remains the gate for any future authenticated method.

## Generic Import isolated-smoke caution

If Generic Import is installed only for its isolated experimental smoke, do **not** add its discovery card/source to the real Portfolio Architect production source set. That smoke must not alter the real source set; Generic Import should be uninstalled after this standalone smoke test unless it is intentionally being adopted.
