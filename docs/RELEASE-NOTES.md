# Portfolio Architect v1.61.0 release notes

v1.61.0 completes the Configure UX consistency work around **destructive selected-object actions**. Editing has shown immutable context since the earlier Configure UX pass; removal now receives the same protection and adds an explicit confirmation boundary before mutation.

## Two-step removal confirmation

The following actions now separate object selection from mutation:

- supplemental REST Gateway removal;
- execution-provider removal;
- savings-plan-route removal;
- directed funding-transfer removal.

After selection, a dedicated confirmation form identifies the exact immutable object being removed. Merely choosing an item can no longer remove it.

The confirmation context is provider/endpoint for supplemental Gateways, provider name/ID for execution providers, provider/ISIN for savings-plan routes, and the exact directed provider edge for funding transfers.

Execution-provider confirmation also makes the existing model consequence explicit: removing the provider removes its nested savings-plan routes, while a provider referenced by a funding edge remains fail-closed and cannot be removed until that edge is removed.

## Source-model consistency

Portfolio Architect continues to have exactly one primary source stored in the config entry. The primary REST Gateway remains identity-preserving and reconfigurable but is not a removal target. Add/Edit/Remove remains scoped to supplemental REST Gateways only; removing one supplemental Gateway does not modify the primary source, Gateway App, or Gateway private state.

## Unchanged contracts

v1.61.0 is Home Assistant-side UX/safety hardening only. The historical **Comdirect LEGACY** App was removed from the active repository in v1.57.0; canonical Comdirect retains only the bounded migration receiver for already-installed supported Legacy instances.

The preserved compatibility contracts are:

- Portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 9 current; schemas 1–8 remain supported;
- historical early compatibility remains explicit: schemas 1–6 remain supported;
- presentation schema 2: unchanged;
- broker schemas 1/2/3: unchanged;
- config-entry schema 12: unchanged;
- acquisition authority and `fallback_policy: none`: unchanged;
- canonical capability evidence clocks and freshness: unchanged;
- private-PKI HTTPS, bearer authentication and DNS pinning: unchanged;
- LKG, anti-rollback and source-set atomicity: unchanged;
- planner economics, funding-route semantics and advisory-only boundary: unchanged;
- authenticated DKB FinTS acquisition remains disabled;
- no dashboard YAML replacement is required.

No trading, order, transfer, payment, or transaction-history capability is introduced. Sell and withdrawal capability also remain absent.

## Historical compatibility notes retained

The historical v1.19.0-rc2 brokerage probe remains historical, is not included in this stable release, and is not promoted by this release. The v1.39 colourful allocation view was not included in v1.38.1; that historical sequencing remains documented and unchanged.

Trade Republic provider-specific statement parsing remains inside its Gateway; v1.61.0 does not move PDF parsing into Portfolio Architect.

The v1.33.0 source-freshness and plan-schedule separation remains intact: recurring scheduling remains anchored to the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold. Acquisition authority remains explicit with `fallback_policy: none`; there is no silent fallback between methods.
