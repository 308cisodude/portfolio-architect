# Portfolio Architect 1.17.1

Version 1.17.1 is the security-hardened replacement for the unpublished v1.17.0
publication candidate. It retains the HACS/publication milestone while addressing
three pre-publication review findings. Portfolio calculations, cost-aware
execution, source schemas, entities, and dashboard behavior remain unchanged from
the validated v1.16.3 baseline.

## Immutable workflow dependencies

- Every `uses:` dependency is pinned to a full 40-character commit SHA with a
  human-readable version comment.
- HACS and hassfest run from explicit `ghcr.io/...@sha256:...` image digests.
  This is intentional: their upstream wrapper actions currently delegate to
  mutable container tags, so pinning only the wrapper commit would not make the
  executed validator immutable.
- The local publication checker rejects action tags, action branches, mutable
  container tags, and GHCR images without a SHA-256 digest.
- GitHub Actions permissions remain explicitly bounded per workflow.
- Dependabot continues to propose updates for repository-syntax GitHub Actions.
  HACS and hassfest image-digest updates require deliberate maintainer review.

## Hash-locked Python validation toolchain

- Validate and release jobs use the fixed `ubuntu-24.04` runner label and exact
  Python `3.14.6`.
- Every direct and transitive Python validation dependency is version-pinned and
  bound to the reviewed wheel SHA-256 in
  `requirements/ci-python-3.14-linux-x86_64.txt`.
- CI installs only those wheels with `--require-hashes`, `--no-deps`, and
  `--only-binary=:all:`; it no longer performs a floating pip upgrade or an
  unconstrained package install.
- The lock uses pytest 9.0.3 and Pygments 2.20.0, and explicitly lists
  pytest's Linux dependencies, PyYAML, and Pillow. Publication validation rejects
  unhashed entries or workflows that stop enforcing the lock.
- GitHub's hosted runner image and the Python distribution delivered by the
  pinned setup action remain externally managed trust roots; the release does not
  claim a hermetic or fully reproducible runner environment.

## Local REST DNS pinning

- Each authenticated local REST request performs one operating-system DNS
  resolution immediately before connecting.
- Every returned address must be loopback, link-local, or private; a mixed local
  and public answer fails closed.
- A request-scoped resolver returns only that already validated address set to
  `aiohttp`, eliminating the prior validation/connection re-resolution window.
- The original hostname remains in the request URL, preserving the HTTP Host
  header, TLS SNI, and certificate-name validation.
- Redirect following, environment-proxy use, cookie persistence, DNS caching, and
  connection reuse are disabled for this boundary.

## Active ownership contract

- `tools/configure_publication.py` writes the active `.github/CODEOWNERS` file and
  removes `.github/CODEOWNERS.example`.
- Workflows, Dependabot configuration, publication scripts, integration code,
  standalone Gateway code, and Gateway App code receive explicit ownership rules.
- Strict publication validation fails when the active file or any protected path
  is missing.
- GitHub branch protection or a repository ruleset must separately require code-
  owner review for those rules to be enforced during pull requests.

## Compatibility

- No configuration migration.
- No payload, REST portfolio, Gateway health, allocation-overview, or cost-model
  schema change.
- No entity-ID or unique-ID change.
- No dashboard replacement required.
- Gateway App 1.16.1 and later remain protocol-compatible.
