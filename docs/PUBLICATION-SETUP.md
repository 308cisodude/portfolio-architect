# First public repository setup

Portfolio Architect deliberately does not invent a GitHub owner, repository URL,
or code owner. Configure those values only after the final public repository
exists.

## 1. Create the repository

Create one public GitHub repository containing this complete source tree. Enable:

- Issues;
- private vulnerability reporting;
- release immutability for future releases;
- GitHub Actions with the minimum permissions declared by each workflow.

Add a concise repository description and relevant topics such as
`home-assistant`, `hacs`, `portfolio`, `etf`, and `personal-finance`.

Branch protection or a repository ruleset is configured after the first push,
when the workflow check names exist. Protect `main`, prevent force pushes and
branch deletion, require the validation checks, and enable **Require review from
Code Owners** when more than one eligible reviewer is available. A CODEOWNERS file
alone does not enforce approval.

## 2. Configure repository metadata

From the repository root, run:

```bash
python tools/configure_publication.py \
  --repository OWNER/REPOSITORY \
  --codeowner @GITHUB_HANDLE
```

Multiple `--codeowner` arguments are supported. The command writes:

- `documentation`, `issue_tracker`, and `codeowners` in `manifest.json`;
- `publication.json`;
- the active `.github/CODEOWNERS` file with explicit ownership of workflows,
  dependency automation, publication tooling, integration code, and Gateway code.

It also removes the inactive `.github/CODEOWNERS.example` file.

The configurator also removes root-level `PACKAGE-MANIFEST.json` and
`SHA256SUMS`. Those files authenticate the immutable downloaded source archive;
they would become stale after repository-specific metadata is written. Release
builds generate fresh copies inside every complete-source archive.

Validate the configured repository strictly:

```bash
python tools/check_publication.py --strict
```

Strict validation rejects mutable GitHub Action refs, workflow GHCR images without
SHA-256 digests, a floating or non-hash-enforcing Python validation toolchain,
missing privacy/Gitleaks publication gates, incomplete ownership rules, placeholder
repository metadata, and a lingering example CODEOWNERS file.

## 3. Validate before tagging

Wait for these checks to pass on the default branch:

- Validate release;
- Validate with HACS;
- Validate with hassfest.

Run the local pipeline from a clean checkout as an independent check:

```bash
./tools/release_check.sh
```

The local environment validates workflow structure, pinned references, privacy
contracts, and the Python wheel lock, but does not execute the external HACS,
hassfest, or Gitleaks OCI images or the exact GitHub-hosted Python 3.14.6
environment. Their GitHub-hosted runs are the authoritative external acceptance
check.

## 4. Publish

Create an annotated `v1.42.0` tag that points to the reviewed release commit and
push it. The release workflow verifies that the tag matches the integration
version, rebuilds all artifacts, generates attestations, creates a draft release,
uploads every asset, and publishes the completed release.

Release immutability must be enabled before publishing. It applies only to future
releases.

## 5. HACS

The release includes `portfolio_architect.zip`, which is the fixed filename
specified by `hacs.json`. Add the public repository to HACS as a custom repository
for acceptance testing. Submission to the HACS default repository list should be
a separate decision after public feedback and successful HACS/hassfest checks.
