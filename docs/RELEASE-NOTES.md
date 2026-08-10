# Portfolio Architect 1.19.0

Version 1.19.0 adds **provider-owned authorized investment cash** while preserving
Portfolio Architect's provider-neutral allocation role.

## Authorized Cash Policy

The Gateway now separates four concepts for the explicitly selected investment
account:

- the bank-reported booked account balance;
- eligible investment cash, conservatively limited to the lower of booked balance
  and available cash and clamped at zero;
- the Gateway authorization policy; and
- the amount Portfolio Architect is actually authorized to allocate.

The Comdirect Gateway supports two policies through its admin-only Ingress UI:

- `all_available` — authorize all eligible cash; this is the default and preserves
  the behavior of existing installations;
- `capped` — authorize no more than a configured EUR cap.

A capped policy fails closed if its cap is missing or invalid. Policy state is
non-secret, stored atomically in App-private data, and does not expose an account
identifier.

## REST compatibility

The Home Assistant payload remains **payload schema 8**, REST remains **REST schema 1**, and Gateway health remains **Gateway health schema 5**. No schema-version bump is required because the cash metadata is additive and optional.

REST schema 1 remains the wire-contract version. The established
`investment_reserve.available_eur` field now carries the **authorized** amount.
A new optional additive `investment_cash` object can expose the bounded account
balance, eligible cash, authorized cash, policy, optional cap, and timestamp.
Portfolio Architect cross-checks the new object against the legacy reserve before
using it.

This is deliberately bidirectionally compatible:

- Portfolio Architect 1.19.0 still accepts older Gateways that publish only
  `investment_reserve`;
- older Portfolio Architect releases ignore the additive `investment_cash` object
  and continue to consume the authorized amount through `investment_reserve`.

## Home Assistant semantics

The existing `sensor.portfolio_architect_available_investment_reserve` entity ID
is retained, but its display name is now **Authorized investment cash**. When the
new Gateway metadata is available, the entity also exposes the selected account
balance, eligible investment cash, authorization policy, and optional cap as
bounded attributes.

No trading, order, transfer, payment, or transaction-history capability is added.
Portfolio Architect still decides allocation; the Gateway only decides how much
cash it is allowed to offer to the allocator.

## Provider scope

The implementation is provider-neutral at the REST and calculation boundaries,
but the released live Gateway remains Comdirect-specific. DKB supplemental CSV
sources do not provide cash balances and are therefore unchanged. A future DKB
Gateway can apply the same authorization contract, for example with a capped cash
policy, without changing Portfolio Architect's allocation engine.

## Experimental branch note

The historical `v1.19.0-rc2` tag belongs to the separate experimental brokerage-
diagnostics work. Stable 1.19.0 is based on the accepted 1.18.2 stable line and
does **not** promote those experimental diagnostics.
