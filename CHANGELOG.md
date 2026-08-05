# Changelog

## 1.19.0-rc2

- Corrects the recommended-buy tile actions: tap opens the copy-friendly ISIN and
  long press opens the purchase explanation.
- Corrects the conditional Order identifiers / Orderkennungen card to read the
  actual proposed-buy entities, so it no longer renders an empty title-only card.
- Records live acceptance against a confirmed 0% ETF and a regular 1.5% ETF: both
  returned empty `fundFlags`, null fund status, and zero surcharge fields.
- Records identical EUR 15.30 Tradegate ordinary-order purchase charges for both
  samples and confirms that no PhotoTAN challenge or pending/open order was created.
- Retains the instrument metadata read only as an opaque diagnostic and the ex-ante
  endpoint only as an ordinary-order cost diagnostic; neither is presented as a
  savings-plan promotion detector.
- Preserves all rc1 security boundaries, schemas, calculations, entities, fee-review
  metadata, and App-private state.

## 1.19.0-rc1

- Adds an admin-only instrument probe for documented `fundDistribution`, opaque
  `fundFlags`, and bounded eligible-venue metadata.
- Adds one hard-coded, non-submitting POST operation for
  `/api/brokerage/v3/orders/costindicationexante`.
- Keeps order prevalidation, validation, quote/TAN, submission, modification,
  cancellation, and generic brokerage POST capability absent.
- Sanitizes probe evidence and keeps internal depot/venue identifiers behind
  short-lived random Ingress tokens.
- Keeps probe state process-local and outside REST portfolio schema 1, Gateway
  health schema 5, Home Assistant entities, diagnostics, and scheduled refreshes.
- Adds opt-in fee-verification dates/sources with an informational stale-review
  policy finding; no probe result changes configured fees automatically.
- Adds a bilingual built-in Markdown block with selectable ISINs for current
  recommended purchases.
- Marks the Gateway App package experimental and publishes the release as a
  prerelease pending live Comdirect acceptance.
- Preserves v1.18.0 Plan Delta & Decision Trace and all established portfolio,
  allocation, execution, entity, and schema contracts.

## 1.17.2

- Fixes the HACS release asset so integration files are stored directly at the ZIP root.
- Retains the wrapped `custom_components/portfolio_architect/` layout for the manual Home Assistant drop-in.
- Adds release verification for channel-specific archive roots and complete payload equivalence after prefix normalization.
- Adds a regression test that rejects the v1.17.1 nested-HACS packaging failure.
- Preserves the v1.17.1 runtime, security hardening, portfolio behavior, entities, dashboards, and Gateway protocols.

## 1.17.1

- Supersedes the unpublished v1.17.0 publication candidate.
- Pins every reusable GitHub Action to a full 40-character commit SHA.
- Runs the HACS and hassfest validators from immutable GHCR image digests because
  their upstream wrapper actions currently delegate to mutable container tags.
- Adds fail-closed workflow checks that reject mutable action refs and container
  image tags.
- Pins validation and release jobs to Ubuntu 24.04 and Python 3.14.6, and installs
  every direct and transitive Python validation dependency from a version- and
  SHA-256-locked wheel list with hash enforcement and no dependency resolution;
  the set uses Pygments 2.20.0 rather than the vulnerable 2.19.2 release.
- Removes the local REST DNS validation/connection race by resolving once,
  validating every returned address, and binding the request to that exact
  address set while preserving the original Host header, TLS SNI, and certificate
  name validation.
- Disables redirects, environment proxies, and cookie persistence for authenticated
  local REST requests.
- Strengthens generated CODEOWNERS coverage for workflows, dependency automation,
  publication tooling, the integration, and both Gateway distributions; the
  inactive example file is removed after repository configuration.
- Adds executable regression tests for pinned DNS transport and immutable
  publication dependencies.
- Preserves the v1.16.3 portfolio calculation, entity, dashboard, fee, and Gateway
  protocol contracts.

Historical release details are retained in `docs/UPGRADE-*.md` and the source
history.
