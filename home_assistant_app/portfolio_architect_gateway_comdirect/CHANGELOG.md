# Changelog

## 1.58.0

- Version 1.58.0 adds health-schema-9 holdings/cash capability authority for `live_api` and complete `csv`. The explicitly active Comdirect acquisition method remains authoritative for both capabilities, with `fallback_policy: none`; no automatic fallback or provider runtime behavior changes.

## 1.57.0

- Historical `portfolio_architect_gateway` is no longer published; canonical Comdirect remains stable and retains bounded migration-receiver compatibility for already-installed supported v1.55/v1.56 Legacy instances. Runtime, acquisition and migration-security semantics are unchanged from v1.56.1.

## 1.56.0

Canonical provider-qualified App now displays simply as Comdirect; the temporary NEW label is retired with no slug/runtime/migration-security change.

## 1.55.1

- The provider-qualified migration target is version-aligned with the v1.55.1 hotfix. Its one-time fingerprint-pinned receiver, same-CA import, OAuth-session exclusion and explicit cut-over behavior are unchanged.

## 1.55.0

- Adds the provider-qualified `portfolio_architect_gateway_comdirect` App identity.
- Uses an explicit staged migration from the historical Comdirect App with no automatic trust replacement.
- Preserves the private CA, Gateway bearer token, selected account/policy, acquisition state, static CSV evidence and canonical snapshot.
- Deliberately excludes the Comdirect OAuth session; migrated live API requires fresh PhotoTAN authentication before discovery.
