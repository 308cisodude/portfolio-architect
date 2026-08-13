# Publishing checklist

## Repository gate

1. Create the final public GitHub repository.
2. Enable Issues, private vulnerability reporting, branch protection or a
   repository ruleset, and release immutability.
3. Set the repository Actions default token permission to read-only unless a
   workflow explicitly requests more.
4. Add a repository description and topics.
5. Run `tools/configure_publication.py` with the real repository and code owner.
6. Run `python tools/check_publication.py --strict`.
7. Confirm Validate release, Validate with HACS, and Validate with hassfest pass.

The configurator creates the active `.github/CODEOWNERS` file and removes
`.github/CODEOWNERS.example`. CODEOWNERS expresses ownership; GitHub enforces
approval only after the default branch is protected by a rule that requires code-
owner review.

## Immutable dependency policy

- Every external `uses:` reference must contain a full 40-character commit SHA.
  Keep the reviewed release/tag in a same-line comment so automated update pull
  requests remain understandable.
- Every GHCR image executed by a workflow must use
  `ghcr.io/OWNER/IMAGE@sha256:DIGEST`; mutable tags such as `main`, `master`, or
  `latest` are prohibited.
- `tools/check_publication.py` enforces both rules and runs in local validation and
  the release workflow.
- Dependabot updates GitHub Actions referenced through repository syntax. It does
  not update the HACS and hassfest OCI digest variables; review their official
  package pages and upstream changes before deliberately replacing a digest.
- A digest update is a security-relevant code change. Review it through the same
  pull-request and CODEOWNERS path as workflow changes.
- Validation and release jobs pin `ubuntu-24.04` and Python `3.14.6`. They install
  `requirements/ci-python-3.14-linux-x86_64.txt` with `--require-hashes`,
  `--no-deps`, and `--only-binary=:all:`. Every direct and transitive dependency
  must be listed with an exact version and reviewed wheel SHA-256.
- Do not hand-edit only a version number when updating the Python toolchain.
  Resolve the complete dependency set for CPython 3.14/Linux x86-64, record the
  exact wheel hashes from the package index, run the negative publication tests,
  and review the resulting dependency change as security-sensitive.
- `tools/check_publication.py` rejects a missing lock, unhashed or non-exact
  entries, a floating runner/Python version, an extra pip installation path, or a
  workflow that does not enforce the lock.
- The GitHub-hosted runner image and setup action's Python distribution are still
  managed external trust roots. The controls above remove avoidable floating
  package resolution; they do not make the hosted runner hermetic.

## Release gate

1. Review the MIT license, contributor attribution, support policy, and security
   reporting instructions.
2. Run `./tools/release_check.sh` from a clean checkout.
3. Verify the generated archives with `tools/verify_release.py`.
4. Review release notes, checksums, SPDX SBOM, integration drop-in, stable HACS
   archive, Gateway App archive, and complete source archive together.
5. Create and push the exact semantic-version tag.
6. Let `.github/workflows/release.yml` build, attest, upload, and publish the
   complete draft release.
7. Verify at least one release artifact with `gh attestation verify`.
8. Test installation in a clean Home Assistant instance and through HACS as a
   custom repository before announcing the release.

## Distribution boundaries

The integration can be distributed manually or through HACS. The Gateway App
must be published through a Home Assistant App repository or installed as a local
App. These are separate distribution channels and remain separate release
artifacts.

The Gateway is a local read-only bridge. Port 8787 must not be exposed to
untrusted networks.

## v1.22 privacy publication gate

Every publication candidate must pass `tools/check_privacy.py` on the repository and
on the built `dist/` artifacts. Protected GitHub validation additionally applies the
same Portfolio Architect-specific rules to complete reachable Git history. Protected GitHub validation additionally executes
`tools/run_gitleaks_ci.sh`, which scans the tracked tree, complete Git patch history,
and staged release contents with the reviewed immutable Gitleaks image.

Do not create a Gitleaks baseline for first-party Portfolio Architect source. The
expected state is zero unexplained secret findings. Do not suppress an attributable
account/identity finding merely because it appears in a fixture; public fixtures
must be wholly synthetic.

For a local maintainer-only exact check, place one known private literal per line in
a file **outside** the repository and run `tools/check_privacy.py` with
`--private-literals <path>`. Never commit that file.
