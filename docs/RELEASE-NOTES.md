# Portfolio Architect 1.24.1

Version 1.24.1 is a focused startup hotfix for the distinct DKB and Trade Republic provider Apps introduced in 1.24.0. Portfolio calculations, Comdirect banking behavior, wire schemas and provider identities are unchanged.

## Provider-shell startup fix

Live acceptance of v1.24.0 found that the DKB shell exited before opening its Ingress page. The reduced DKB/TR packages intentionally omit Comdirect-specific modules, but the shared `server.py` still imported the Comdirect `GatewayConfig` type at runtime. That caused `ModuleNotFoundError: portfolio_architect_gateway.config` before either shell server could start.

Version 1.24.1 keeps `GatewayConfig` only as a type-checking import. Runtime `GatewayState` and `create_server()` continue to consume provider-neutral `ServerConfig`, so the architectural isolation introduced in v1.24.0 is preserved rather than weakened. The same latent defect is fixed for both DKB and Trade Republic.

## Stronger release gates

Regression coverage now imports `pending_app` from the exact reduced DKB/TR package layout with `config.py` absent. The shell Dockerfiles import the real startup module during image build, and protected validation starts both built shell containers and requires them to remain running with the Ingress and private REST listeners available before merge or immutable publication.

## Compatibility

- Portfolio payload schema 8: unchanged.
- REST portfolio schema 1: unchanged.
- Gateway health schema 6: unchanged; `provider_id` remains bounded provider provenance only, and schemas 1–5 remain supported.
- Existing entity IDs, actionability, authorized-cash and LKG semantics: unchanged.
- Existing Comdirect App slug/private state and authentication: unchanged.
- No DKB or Trade Republic acquisition runtime is shipped; both remain experimental, manual-only provider shells.
- Trade Republic statement-document import remains the next milestone.
- No trading, order, transfer, payment, or transaction-history capability is added.

## Experimental branch note

The historical `v1.19.0-rc2` brokerage-diagnostics tag remains separate experimental work. That experimental code is not promoted by this release.
