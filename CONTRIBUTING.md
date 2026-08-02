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

GitHub pull requests must also pass HACS and hassfest validation after repository
publication metadata has been configured.

A change that affects the REST or Gateway health contract must retain backward
compatibility or include an explicit schema migration. Do not commit credentials,
OAuth material, bearer tokens, account identifiers, private snapshots, exported
CSV files, Home Assistant `.storage` data, or generated Python caches.

User-visible text must be provided in both English and German. Dashboard changes
must remain usable with native Home Assistant cards and without third-party
frontend dependencies.

## Release changes

- Patch releases repair defects without changing public contracts.
- Minor releases may add backward-compatible entities, diagnostics, workflows,
  adapters, or documentation.
- A major release is reserved for an intentional breaking configuration or schema
  change, not for arbitrary roadmap numbering.

Repository-specific publication metadata must be changed only through
`tools/configure_publication.py` and must pass
`python tools/check_publication.py --strict` before a release tag is created.
