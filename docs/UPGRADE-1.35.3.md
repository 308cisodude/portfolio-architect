# Upgrade to Portfolio Architect 1.35.3

Version 1.35.3 is a narrow Home Assistant options-menu presentation hotfix for the native
**Execution providers & funding** editor introduced in v1.35.2.

## Upgrade

1. Update Portfolio Architect through HACS to **1.35.3**.
2. Restart Home Assistant once.
3. Open **Settings → Devices & services → Portfolio Architect → Configure → Execution providers & funding**.
4. Confirm the four top-level entries are visibly labelled:
   - Execution evidence settings;
   - Execution providers;
   - Savings-plan routes;
   - Funding topology.
5. Open the provider, savings-plan and funding submenus and confirm their Add/Edit/Remove actions are
   labelled as applicable.
6. Do not save any broker change solely to accept this hotfix. Merely opening the menus is sufficient
   to prove the presentation correction.
7. Align the Comdirect, Trade Republic and DKB Apps to 1.35.3 in place when their updates are offered;
   their provider behavior is unchanged apart from normal package/User-Agent version alignment.

## Existing configuration

No configuration migration is required. Existing `broker.yaml`, portfolio/source configuration,
private Gateway state, bearer tokens, private CA trust, Comdirect OAuth/session state, selected
investment account and investment-cash authorization policy remain in place.

The v1.35.2 native broker editor continues to treat `broker.yaml` as authoritative. This release
changes only the missing menu labels and adds regression coverage for them.

## Keep cash reserve

The v1.35.2 **Keep cash reserve** policy is unchanged. If it has not yet been live-tested, first align
both the Portfolio Architect integration and the Comdirect App to 1.35.3, then choose an explicit
retained EUR amount and verify:

`authorized_eur = max(eligible_eur - retain_eur, 0)`.

A retained amount greater than eligible cash must authorize zero rather than fail.

## Rollback

A normal rollback to v1.35.2 requires no broker-file migration because this hotfix does not change
broker schemas or persisted integration options. If the Comdirect cash policy has been changed to the
v1.35.2 `retain` mode, return it to `all_available` or `capped` before rolling back to a pre-v1.35.2
Comdirect App, because older strict clients do not recognize `retain_eur`.
