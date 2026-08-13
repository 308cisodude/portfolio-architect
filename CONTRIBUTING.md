# Contributing

Changes should preserve deterministic calculations, strict input validation,
and the separation between Home Assistant and banking authentication.

## Development checks

Before submitting a change, run:

```bash
python -m pip install \
  --disable-pip-version-check \
  --no-deps \
  --only-binary=:all: \
  --require-hashes \
  -r requirements/ci-python-3.14-linux-x86_64.txt
./tools/release_check.sh
```

The lock targets CPython 3.14.6 on Linux x86-64. Dependency updates must retain
exact versions and reviewed wheel hashes for the full direct and transitive set.

The complete local shell pipeline is designed for a POSIX/Linux execution
environment. Native Windows can legitimately differ on executable bits, POSIX file
modes, and directory fsync behavior; do not change security semantics merely to make
those platform-specific assertions pass locally. For Windows maintainers, the
protected GitHub **Validate release** workflow is the authoritative full regression
and publication check.

GitHub pull requests must also pass HACS and hassfest validation after repository
publication metadata has been configured. The protected validation workflow runs
the v1.22 privacy gate and immutable Gitleaks source/history/artifact scan before
release artifacts are accepted.

A change that affects the REST or Gateway health contract must retain backward
compatibility or include an explicit schema migration. Do not commit credentials,
OAuth material, bearer tokens, account identifiers, private snapshots, raw broker
documents, unapproved exported CSV files, Home Assistant `.storage` data, or
generated Python caches. Public broker fixtures must be wholly synthetic.

User-visible text must be provided in both English and German. Dashboard changes
must remain usable with native Home Assistant cards and without third-party
frontend dependencies.

## AI-assisted contributions

Read `AI_POLICY.md` before submitting AI-assisted work. Material AI assistance
should be disclosed in the pull request. Contributors remain responsible for the
changes they submit; autonomous publication is not accepted. Architecture- and
security-sensitive changes should explain the human-reviewed invariants, trust
boundaries, and validation evidence.

## Release changes

- Patch releases repair defects without changing public contracts.
- Minor releases may add backward-compatible entities, diagnostics, workflows,
  adapters, or documentation.
- A major release is reserved for an intentional breaking configuration or schema
  change, not for arbitrary roadmap numbering.

Repository-specific publication metadata must be changed only through
`tools/configure_publication.py` and must pass
`python tools/check_publication.py --strict` before a release tag is created.
