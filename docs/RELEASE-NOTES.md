# Portfolio Architect 1.41.1

Portfolio Architect v1.41.1 is a narrow live-acceptance hotfix for **provider-local cash preference**. v1.41.0 successfully added independent Trade Republic `KONTOAUSZUG` cash evidence, but live testing exposed one deterministic tie: sufficient Trade Republic local cash and a zero-fee/zero-business-day Comdirect → Trade Republic funding edge produced otherwise identical candidates, and the final lexical funding-provider ID tie-break selected Comdirect.

## Fixed routing tie

`choose_funded_route_for_cash()` keeps its established ordering for:

1. total route cost ratio;
2. funding settlement business days;
3. explicit execution-provider priority;
4. executable order amount; and
5. combined execution/funding fees.

Only after those fields are equal does v1.41.1 now prefer `funding_transfer_required == false` before arbitrary route/provider identifiers. Sufficient execution-provider-local cash therefore wins an otherwise identical transfer-funded candidate without changing cost-first routing or explicit user preference semantics.

Executable regression coverage reproduces the live zero-fee/zero-day parity case with fully synthetic provider and cash data and proves that local execution-provider cash is selected while the transfer edge remains unused.

## Trade Republic cash statements unchanged

The separate provider-isolated Trade Republic statement families introduced in v1.41.0 are unchanged:

- `DEPOTAUSZUG` → validated holdings snapshot;
- `KONTOAUSZUG` → validated provider-scoped cash snapshot.

Uploaded PDFs remain in-memory only. Transaction rows, transfer counterparties, IBAN/account identifiers, account holder/address data, and raw statement text are not retained. Holdings and cash remain independently persisted and independently freshness-gated. Trade Republic PDF parsing remains inside its provider-isolated Gateway App and does not move PDF parsing into Portfolio Architect.

## Security and provider boundaries

- No Trade Republic credentials are requested or stored.
- No private/undocumented Trade Republic API is contacted.
- No transaction-history model or transaction rows are persisted.
- Verified private-PKI HTTPS, bearer authentication, provider isolation and fail-closed provider behavior remain intact.
- The DKB anonymous FinTS capability probe and Comdirect live acquisition behavior are unchanged apart from normal 1.41.1 package/version alignment.
- DKB live Gateway acquisition remains a later gated milestone; this release does not infer authenticated holdings support from anonymous capability evidence.

## Presentation

The v1.39.0 colourful paired allocation Tile view was not included in v1.38.1; it arrived in v1.39.0 and remains unchanged here. The v1.38.1 signed drift presentation is likewise unchanged. The v1.41.1 bilingual reference dashboard is byte-identical to v1.41.0, so no dashboard YAML migration is required.

## Compatibility contracts retained

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- presentation schema 2 remains unchanged.
- broker schemas 1/2/3 remain unchanged.
- The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, and v1.41.1 does not change any configured freshness threshold.
- The historical v1.19.0-rc2 state remains historical and is not promoted by this release.
- No trading, order, transfer, payment, or transaction-history capability is introduced by v1.41.1.

## Upgrade

Update the integration and all three Gateway Apps in place to v1.41.1. Preserve existing private App state. No broker or dashboard migration is required. The Trade Republic `DEPOTAUSZUG` holdings and `KONTOAUSZUG` cash import behavior is unchanged from v1.41.0.
