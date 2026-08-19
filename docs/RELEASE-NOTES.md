# Portfolio Architect 1.35.3

Version 1.35.3 is a narrow Home Assistant options-menu presentation hotfix prepared on top of the
published v1.35.2 execution-policy UX release.

## Execution-policy menu labels restored

The v1.35.2 native **Execution providers & funding** editor introduced four list-based Home
Assistant menus, but the parent menu steps did not provide the required `menu_options` translation
mapping. Home Assistant therefore rendered clickable chevrons with no visible labels even though the
underlying broker configuration and menu routing were intact.

Version 1.35.3 adds complete English and German labels for every emitted option in all four broker
editor menus:

- **Execution providers & funding**;
- **Execution providers**;
- **Savings-plan routes**; and
- **Funding topology**.

The labels reuse the established child-step titles, so navigation terminology remains consistent.
A regression derives each menu's possible literal options from `config_flow.py` and requires both
English and German translations to provide a non-empty label for every emitted option.

## No execution-policy semantic change

This hotfix does not change the v1.35.2 broker editor's read/write behavior, `broker.yaml` schema,
route economics, tie-break semantics, promotional metadata, or retained-cash authorization. The
existing exact directed funding topology remains authoritative and no reverse transfer relationship
is inferred.

## Long-running compatibility contracts

- v1.33.0 source-freshness and plan-schedule separation remains preserved; v1.35.3 does not change any configured freshness threshold.
- Recurring scheduling remains anchored to the latest valid Portfolio Architect evaluation.
- v1.35.1 Comdirect session-maintenance resilience remains unchanged.

## Compatibility and security invariants

- Portfolio payload schema 8: unchanged.
- REST portfolio schema 1: unchanged, including the additive v1.35.2 `retain_eur` field.
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- Broker schemas 1/2/3 runtime compatibility: unchanged.
- v1.35.2 **Keep cash reserve** behavior: unchanged.
- v1.35.1 Comdirect connection-error classification and maintenance-worker containment: unchanged.
- This release does not move PDF parsing into Portfolio Architect; Trade Republic statement import/private diagnostics remain provider-side and unchanged.
- DKB live Gateway acquisition remains a later provider-specific milestone; DKB remains experimental, manual-only and non-live.
- Verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and
  no-plaintext fallback: unchanged.
- No trading, order, transfer, payment, or transaction-history capability is introduced; no automatic sell capability is added.
- No dashboard migration is required.
- Native dynamic portfolio presentation remains a separate future milestone.
- The historical `v1.19.0-rc2` brokerage probe remains excluded and is not promoted by this release.

See `docs/UPGRADE-1.35.3.md`.
