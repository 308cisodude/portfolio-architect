# Changelog

## 1.55.0

- Adds the provider-qualified `portfolio_architect_gateway_comdirect` App identity.
- Uses an explicit staged migration from the historical Comdirect App with no automatic trust replacement.
- Preserves the private CA, Gateway bearer token, selected account/policy, acquisition state, static CSV evidence and canonical snapshot.
- Deliberately excludes the Comdirect OAuth session; migrated live API requires fresh PhotoTAN authentication before discovery.
