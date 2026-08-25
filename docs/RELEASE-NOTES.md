# Portfolio Architect 1.53.0

Portfolio Architect v1.53.0 adds the provider-neutral acquisition-method control plane discussed after the fully live-accepted v1.52.0 baseline. It does not create duplicate bank providers and does not give the Home Assistant integration authority to change provider acquisition.

## Provider identity is separate from acquisition method

Each Gateway continues to publish exactly one stable provider identity. Health schema 8 adds bounded read-only acquisition control metadata: the active method, the provider-defined method inventory, readiness/activation eligibility, `fallback_policy: none`, and privacy-safe last explicit operator switch metadata. Health schemas 1–7 remain accepted for compatibility.

Portfolio Architect consumes this state for diagnostics and source visibility only. Acquisition changes remain explicit provider-Gateway administration actions; no management POST/API is added to the Home Assistant integration.

## Comdirect is the first explicit dual-method switch implementation

The Comdirect Gateway keeps `live_api` and `csv` mutually exclusive. Inactive CSV holdings/cash can be staged without affecting the live canonical snapshot. When live API is active, CSV becomes `ready` for activation only after both supported static evidence families are present. Switching to live API performs a real provider read; switching to CSV validates the complete staged candidate.

Activation is atomic with respect to Gateway snapshot publication. The acquisition lock spans candidate validation, control-state persistence and canonical publication, so concurrent refreshes cannot observe a transient candidate method. A private pending-activation marker makes the transition crash-safe: if the App stops mid-switch, startup restores the exact prior control state and discards the ambiguous cached canonical snapshot before normal startup refresh. Failed publication likewise restores the pre-switch state, and expected activation failures return bounded Ingress feedback while the previous method remains authoritative.

Inactive staged CSV corruption is treated as `not_ready` and cannot disrupt an active live-API source. No automatic cross-method fallback is implemented.

A pre-v1.53 installation already active in holdings-only CSV mode remains readable for upgrade compatibility, but once another method is activated, returning to inactive CSV requires both current holdings and cash evidence.

## Other provider inventories

- DKB: `csv` is active/ready; `fints` is `research_only` and cannot be activated. The anonymous BPD probe remains **EXPERIMENTAL · RESEARCH ONLY** and authenticated DKB FinTS remains disabled.
- Trade Republic: `pdf` is active/ready; `live_api` is `unavailable` and cannot be activated.
- Generic Import: fixed single `csv` acquisition method.

This release does not advance DKB authenticated user/UPD probing and does not introduce an undocumented Trade Republic client.

## Preserved contracts

- config-entry schema 12: unchanged
- portfolio payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 8 current; schemas 1–7 remain supported
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- v1.48 acquisition-aware freshness and independent holdings/cash evidence clocks: unchanged
- provider-scoped cash, funding topology, execution path and planner economics: unchanged
- verified private-PKI HTTPS, bearer authentication, DNS pinning, configured-source atomicity and Home Assistant LKG: unchanged
- no automatic acquisition fallback
- no trading, order, transfer, payment, transaction-history, sell or withdrawal capability

No dashboard YAML replacement is required.

## Historical compatibility note

The former v1.19.0-rc2 brokerage probe remains historical only, is not present in the stable source tree, and is not promoted by this release.

No trading, order, transfer, payment, or transaction-history capability is introduced by v1.53.0; sell and withdrawal capability remain absent.

For historical compatibility, health schemas 1–6 remain supported unchanged within the wider schema-1-through-8 compatibility range.

authenticated DKB FinTS acquisition remains disabled; the anonymous BPD capability probe remains isolated research-only functionality.

Trade Republic provider-specific statement parsing remains in its Gateway; this release does not move PDF parsing into Portfolio Architect.

The later v1.39 colourful allocation view was not included in v1.38.1; that historical sequencing remains unchanged.

The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; v1.53.0 does not change any configured freshness threshold.
