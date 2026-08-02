# Quality and release policy

Portfolio Architect follows the Home Assistant integration quality principles
for user experience, translated entities, diagnostics, repairs, testing, and
safe reconfiguration, while remaining a community custom integration.

A release is accepted only when:

- Python compilation succeeds;
- JSON and YAML parse successfully;
- all integration and Gateway tests pass;
- integration, engine, Gateway, and App versions agree;
- package paths are safe and contain no duplicates;
- internal and external SHA-256 checksums verify;
- the generated release is reproducible from the same source and build inputs;
- no Python caches, credentials, portfolio exports, snapshots, or `.storage`
  content are present.

Patch releases repair defects without changing contracts. Minor releases may add
compatible entities, diagnostics, documentation, or tooling. A major release is
reserved for intentional breaking configuration or schema changes.
