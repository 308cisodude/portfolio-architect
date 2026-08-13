# Portfolio Architect 1.23.0

Version 1.23.0 establishes the provider-aware Gateway foundation needed for
separate Comdirect, DKB and Trade Republic Home Assistant Apps without changing
the portfolio calculation or the read-only financial boundary.

## Provider-neutral Gateway runtime contract

The hardened Gateway server now consumes a minimal `PortfolioProvider` protocol
rather than importing `ComdirectClient`. A provider supplies only a bounded
machine-readable provider identity, its validated refresh cadence and a validated
provider-neutral snapshot.

The released implementation remains Comdirect. `ComdirectClient` now implements
that protocol explicitly while its OAuth/bootstrap, account discovery, selected
account, cash authorization and upstream API behavior remain provider-specific.

## Gateway health schema 6

Health schema 6 adds exactly one provider field:

```json
{
  "provider_id": "comdirect"
}
```

The value is bounded and non-secret. Account IDs, depot IDs, IBANs and authentication
material are not exposed. Health schemas 1 through 5 remain available unchanged.
Portfolio Architect 1.23.0 negotiates schema 6 first and includes older health
media types as fallbacks, preserving rich recovery telemetry with older supported
Gateway versions.

The Gateway status entity and privacy-conscious diagnostics expose `provider_id`
when schema 6 is available.

## Distinct Comdirect App identity without migration

The existing App is now visibly named **Portfolio Architect Gateway — Comdirect**.
Its existing slug remains `portfolio_architect_gateway`, deliberately preserving
its Home Assistant identity and App-private data. No credential, OAuth/session,
API-token, account-selection, cash-policy or cached-snapshot migration is needed.

The reserved future App identities are documented as:

- Portfolio Architect Gateway — DKB (`portfolio_architect_gateway_dkb`)
- Portfolio Architect Gateway — Trade Republic (`portfolio_architect_gateway_trade_republic`)

No DKB or Trade Republic acquisition runtime is shipped in 1.23.0. This release
creates the clean common boundary first rather than publishing non-functional
provider Apps.

## Compatibility and safety

- Payload schema 8 is unchanged.
- REST portfolio schema 1 is unchanged.
- Gateway health schema 6 is additive; schemas 1–5 remain supported.
- Portfolio calculations, allocation corridors, policy, cost-aware execution,
  authorized investment cash, v1.20/v1.20.1 LKG behavior, v1.21 actionability and
  v1.22 publication/privacy controls are unchanged.
- Existing Home Assistant entity IDs and unique IDs are unchanged.
- The v1.21 reference dashboard remains current; no dashboard replacement is required.
- No trading, order, transfer, payment, or transaction-history capability is added.

The historical `v1.19.0-rc2` brokerage-diagnostics branch remains separate and is
not promoted by this release.
