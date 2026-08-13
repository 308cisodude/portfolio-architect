# v1.22.0 validation

Portfolio Architect v1.22.0 retains the complete functional regression suite and
adds fail-closed publication/privacy validation.

The deterministic release pipeline validates:

- Python compilation and JSON/YAML parsing;
- local publication-readiness and immutable dependency contracts;
- repository privacy hygiene before tests/build;
- the complete regression suite, including v1.21 execution/actionability semantics
  and all v1.20/v1.20.1 LKG safety contracts;
- reproducible release builds, archive layout, ZIP safety, source-symlink rejection,
  virtual-environment exclusion, checksums, manifests and SPDX metadata;
- privacy hygiene again against the exact built release files and every ZIP member.

GitHub-hosted validation additionally:

- checks out complete history (`fetch-depth: 0`);
- applies Portfolio Architect-specific path/content privacy rules to all reachable
  historical paths and textual patches;
- stages the exact tracked tree with `git archive`;
- scans that tree with the immutable Gitleaks v8.30.0 image;
- streams `git log -p --all --no-ext-diff --text` to Gitleaks stdin under shell
  `pipefail`, after proving that reachable history is non-empty;
- safely stages all generated release artifacts and scans their extracted contents
  with the same immutable Gitleaks image.

The immutable release workflow repeats the same privacy/secret gates after building
artifacts and before attestation or GitHub release publication.

Run the deterministic release pipeline in a POSIX/Linux validation environment with:

```bash
./tools/release_check.sh
```

Native Windows is not the authoritative environment for the complete shell/test
pipeline: executable-bit, POSIX file-mode, and directory-fsync assertions can differ
there even when the release source is correct. Windows maintainers may use GitHub
Desktop/web for the normal branch/PR workflow and rely on the protected GitHub
**Validate release** job for the authoritative Linux regression/publication run. Do
not weaken POSIX security contracts merely to make a native Windows run green.

The external Gitleaks container scan is intentionally a GitHub/Linux publication
control and is not required for ordinary Windows maintenance. The protected GitHub
Validate release, HACS, and hassfest workflows remain the authoritative hosted
acceptance checks.
