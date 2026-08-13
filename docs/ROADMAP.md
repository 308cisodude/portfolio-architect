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

## Next milestone — provider-separated Gateway Apps

Split the provider boundary into distinct Home Assistant Apps for:

1. **Portfolio Architect Gateway — Comdirect**
2. **Portfolio Architect Gateway — DKB**
3. **Portfolio Architect Gateway — Trade Republic**

The Apps should share the provider-neutral Portfolio Architect REST contracts and
common hardened infrastructure where appropriate, while keeping provider-specific
authentication, parsing, persistence, failure handling, and operator UX isolated.
A provider App does not imply that every provider offers the same online API
capabilities; each App must expose only capabilities that can be supported safely
for that provider.

Migration from the existing Comdirect-specific Gateway App must preserve the
read-only boundary, cached-state safety, authorization semantics, and existing
Home Assistant configuration wherever technically possible.

## Following milestone — Trade Republic statement import

Add local import support for supported Trade Republic statement documents and map
the extracted holdings data into Portfolio Architect's provider-neutral source
model.

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
