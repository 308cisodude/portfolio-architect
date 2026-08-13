# Portfolio Architect roadmap

This roadmap records intended sequencing rather than a compatibility promise. Each
milestone remains subject to its own design, security review, tests, and live
acceptance before it becomes a stable release.

## v1.22.0 — publication and privacy hardening

- Make repository privacy hygiene a fail-closed release invariant.
- Scan the tracked source tree, complete Git history, and built release artifacts
  for secrets with an immutable Gitleaks image.
- Add Portfolio Architect-specific checks for attributable account material, raw
  broker documents, unexpected exports/screenshots, and unsafe release contents.
- Keep public security identifiers such as ISINs, generic provider names, and
  wholly synthetic fixtures publishable.
- Keep optional exact private-literal checks local to the maintainer; real private
  values are never committed merely to configure the scanner.
- Clarify that the supplied Lovelace dashboard is a reference configuration and is
  never overwritten automatically by HACS or the integration.

## v1.23.0 — provider-aware Gateway foundation

- Make the common Gateway server depend on a provider-neutral runtime protocol
  instead of `ComdirectClient`.
- Add bounded provider identity to Gateway health schema 6 while retaining schemas
  1 through 5 unchanged.
- Rename the visible existing App to **Portfolio Architect Gateway — Comdirect**
  while retaining the established `portfolio_architect_gateway` slug and private
  App data for in-place migration.
- Reserve distinct official App identities for DKB and Trade Republic without
  publishing non-functional provider runtimes.
- Keep Comdirect authentication, account selection, cash authorization and
  upstream failure handling isolated in the Comdirect provider implementation.

## Next milestone — distinct provider Gateway Apps

The provider boundary is one Home Assistant App per provider:

1. **Portfolio Architect Gateway — Comdirect**
2. **Portfolio Architect Gateway — DKB**
3. **Portfolio Architect Gateway — Trade Republic**

Comdirect is the established live provider and becomes explicitly provider-named in
v1.23.0. The DKB and Trade Republic Apps must become separately installable only
when each has a real, bounded and tested provider acquisition path. They share the
provider-neutral Portfolio Architect REST/server contracts and hardened common
infrastructure where appropriate, while keeping provider-specific authentication,
parsing, persistence, failure handling and operator UX isolated.

A provider App does not imply that every provider offers the same online API
capabilities. Each App exposes only what can be supported safely for that provider.
Migration from the existing Comdirect-specific Gateway App must preserve the
read-only boundary, cached-state safety, authorization semantics, and existing Home
Assistant configuration wherever technically possible.

## Following milestone — Trade Republic statement import

Add local import support for supported Trade Republic statement documents inside
the separate Trade Republic Gateway App and map the extracted holdings into
Portfolio Architect's provider-neutral source model.

Privacy is a hard design constraint for this work:

- real Trade Republic statements remain private input and are never committed;
- public tests use wholly synthetic documents/fixtures only;
- account-holder data, addresses, account/depot identifiers, tax identifiers, and
  other attribution fields are excluded from Portfolio Architect's public payloads,
  diagnostics, logs, and release artifacts;
- the importer must fail closed on unknown or ambiguous document structures rather
  than guessing financial data.

The exact supported statement families and import semantics will be fixed during
that milestone's design phase.
