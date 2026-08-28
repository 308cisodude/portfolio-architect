# Changelog

## 1.56.1

- Fix canonical App restart after a successful migration and fresh PhotoTAN bootstrap: the newly created canonical OAuth session is no longer misclassified as migrated state.
- Keep pre-cut-over OAuth state fail-closed. Post-cut-over session presence is accepted only with a valid preserved-CA TLS leaf for the exact canonical successor hostname.
- Preserve `oauth_session_transferred: false`, same-CA identity, bearer continuity, explicit cut-over, acquisition authority and `fallback_policy: none`.

## 1.56.0

Canonical provider-qualified App now displays simply as Comdirect; the temporary NEW label is retired with no slug/runtime/migration-security change.

## 1.55.1

- The provider-qualified migration target is version-aligned with the v1.55.1 hotfix. Its one-time fingerprint-pinned receiver, same-CA import, OAuth-session exclusion and explicit cut-over behavior are unchanged.

## 1.55.0

- Adds the provider-qualified `portfolio_architect_gateway_comdirect` App identity.
- Uses an explicit staged migration from the historical Comdirect App with no automatic trust replacement.
- Preserves the private CA, Gateway bearer token, selected account/policy, acquisition state, static CSV evidence and canonical snapshot.
- Deliberately excludes the Comdirect OAuth session; migrated live API requires fresh PhotoTAN authentication before discovery.
