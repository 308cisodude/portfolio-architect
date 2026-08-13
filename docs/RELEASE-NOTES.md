# Portfolio Architect 1.22.0

Version 1.22.0 makes confidentiality and privacy part of the same fail-closed
release discipline already used for tests, archive verification, immutable
dependencies, and reproducible packaging. Runtime portfolio behavior remains based
on the accepted 1.21.0 release.

## Publication and privacy gate

A new `tools/check_privacy.py` validates repository source, complete reachable Git history in protected CI, and built release artifacts. It rejects high-risk private-document/file classes, unexpected images,
unapproved CSV exports, valid IBANs, private-key material, and provider identity
literals that are not unmistakably synthetic. Findings report rule and location
without printing the matched private value.

The checker also rejects source symlinks, and release staging excludes local virtual-environment directories so local developer state cannot be pulled into a source archive accidentally.

The approved public data boundary remains deliberate: public instrument identifiers
such as ISINs, generic provider names, the generic CSV example, and the existing
sanitized/synthetic Comdirect and DKB fixtures are permitted. Real broker exports,
statements, credentials, account/depot/customer identifiers, and attributable
account-holder material are not.

Maintainers may additionally pass an exact private-literal file located outside the
repository. This provides a local check for known real identifiers without putting
the values into source control or CI configuration.

## Independent secret scanning

The protected validation and immutable-release workflows first repeat the Portfolio Architect-specific privacy scan across complete Git history, then use the official Gitleaks
v8.30.0 container by immutable SHA-256 digest. They scan:

- the exact tracked source tree;
- the complete Git patch history; and
- safely staged contents of every release artifact.

Git history is produced explicitly by Git and streamed to Gitleaks stdin, so the
pipeline does not rely on Gitleaks' internal `git log` execution. Gitleaks v8.30.1
is intentionally not used because its upstream release has reported silent-detection
and packaging regressions.

The release workflow completes both the Portfolio Architect privacy gate and
Gitleaks scan before artifact attestation or GitHub release publication.

## Dashboard ownership clarified

The supplied bilingual Lovelace dashboard remains a static reference configuration.
Once a user copies/imports it into Home Assistant, it is user-owned configuration.
HACS and Portfolio Architect do not overwrite it automatically. Version 1.22.0 does
not require a dashboard replacement after the accepted v1.21.0 dashboard update.

## Roadmap

The next planned architectural milestone is distinct Comdirect, DKB, and Trade
Republic Gateway Apps behind provider-neutral Portfolio Architect contracts. The
following milestone is local Trade Republic statement-document import using only
wholly synthetic public test material.

## Compatibility and safety

Payload schema 8, REST schema 1, Gateway health schema 5, entity IDs,
unique IDs, v1.21 actionability, authorized-cash semantics, LKG behavior, portfolio
calculations, recommendation logic, and the read-only Gateway API surface are
unchanged. The Gateway package is version-aligned to 1.22.0; its banking runtime
behavior is unchanged from 1.20.1.

No trading, order, transfer, payment, or transaction-history capability is added.

The historical `v1.19.0-rc2` tag remains a separate experimental brokerage-diagnostics branch. Stable 1.22.0 does **not** promote those experimental diagnostics or their probe code.
