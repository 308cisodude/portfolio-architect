# Portfolio Architect 1.24.0

Version 1.24.0 turns the v1.23 provider identities into three separately installable Home Assistant App packages while preserving the established Comdirect runtime and all portfolio semantics.

## Three provider App identities

- **Portfolio Architect Gateway — Comdirect** keeps the historical `portfolio_architect_gateway` slug, stable channel, and existing private state.
- **Portfolio Architect Gateway — DKB** is published under `portfolio_architect_gateway_dkb`.
- **Portfolio Architect Gateway — Trade Republic** is published under `portfolio_architect_gateway_trade_republic`.

No DKB or Trade Republic acquisition runtime is shipped by v1.24.0. DKB and Trade Republic are experimental, manual-only provider shells in this release. They establish Supervisor identity, isolated private storage, a persistent local API token, provider health identity and an in-place upgrade path. They deliberately do not provide live portfolio acquisition yet.

## Shared hardened runtime

The common Gateway state/server path now consumes provider-neutral `ServerConfig` directly. Server configuration and secret-file handling are separated from the Comdirect-specific configuration model. DKB/TR packages contain only the audited provider-neutral runtime subset; they do not contain `ComdirectClient`, the Comdirect transport, OAuth/bootstrap UI or cash-policy implementation.

A synchronization tool and regression contract require the App build-context copies to remain byte-identical with the canonical `gateway/src` sources.

## Release packaging

The immutable release now publishes three distinct Gateway App archives: the historical Comdirect asset plus DKB and Trade Republic App ZIPs. Source/history/artifact privacy scans and Gitleaks cover all of them before publication.

## Compatibility and safety

- Payload schema 8: unchanged.
- REST portfolio schema 1: unchanged.
- Gateway health schema 6: unchanged; schemas 1–5 remain supported for backward compatibility.
- Existing entity IDs and unique IDs: unchanged.
- Comdirect credentials/session, selected account, authorized-cash policy, API token and cached snapshot: retained in place.
- v1.20/v1.20.1 LKG behavior and v1.21 schedule/actionability semantics: unchanged.
- DKB/TR shells do not claim live acquisition.
- Trade Republic statement-document parsing is not included; it remains the v1.25.0 milestone.
- The experimental v1.19.0-rc2 brokerage-diagnostic code is not promoted by this release and remains excluded from stable.
- No trading, order, transfer, payment, or transaction-history capability is added.
