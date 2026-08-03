# Portfolio Architect v1.18.0

Portfolio Architect is a Home Assistant-native portfolio overview, policy-check,
and deterministic investment-planning system. It supports provider-specific CSV
imports, multi-source consolidation, cost-aware recommendations, and a separate
read-only Gateway App for live Comdirect data.

Portfolio Architect is advisory software. It exposes no trading, order,
transfer, payment, or account-transaction capability.

## Highlights

- Native Home Assistant entities, configuration flows, diagnostics, repairs, and
  bilingual English/German reference dashboards.
- Deterministic allocation, policy, and cost-aware investment recommendations.
- Private two-evaluation Plan Delta & Decision Trace with bounded reason codes and recorder-safe attributes.
- Live Comdirect data through a local credential-isolated Gateway App.
- Comdirect, DKB, and generic mapped CSV sources with multi-source consolidation.
- Conservative investment-cash handling and explicit transaction-cost policies.
- Reproducible release archives, SHA-256 manifests, SPDX 2.3 SBOMs, and release
  provenance workflows.
- Immutable GitHub Action and validator-image dependencies, plus a hash-locked
  Python validation toolchain, enforced by local and release checks.
- DNS-pinned local REST transport that binds the validated private address set to
  the authenticated connection while preserving Host/SNI identity.

## Installation channels

### Manual installation

Extract the versioned Home Assistant drop-in over the Home Assistant configuration
folder so this directory exists:

```text
/config/custom_components/portfolio_architect
```

Restart Home Assistant, then add **Portfolio Architect** through
**Settings → Devices & services**.

### HACS publication

The repository contains a stable HACS release asset named
`portfolio_architect.zip`, HACS metadata, brand assets, HACS validation, and
hassfest workflows. Before the first public release, the repository owner must run
`tools/configure_publication.py` once to write the real GitHub repository URL and
code owner into the integration manifest. Placeholder or invented repository URLs
are deliberately not shipped.

See `docs/PUBLICATION-SETUP.md` and `docs/PUBLISHING.md`.

## Supported environment

- Home Assistant 2026.7.0 or newer
- Python 3.14 for source validation and Gateway builds
- Gateway App 1.16.1 or newer when using the established live Comdirect protocol

The current stable Portfolio Architect release and the immediately preceding
stable release receive security and correctness fixes while a documented upgrade
path exists. See `SUPPORT.md` and `docs/SUPPORTED-VERSIONS.md`.

## Privacy and security

Bank authentication remains inside the local Gateway App. Home Assistant receives
only the bounded provider-neutral portfolio and health contracts. The selected
investment account identifier, IBAN, account holder, transaction history, OAuth
material, qSession cookie, and bank credentials are not included in the public
portfolio snapshot or diagnostics.

Never expose the Gateway REST port to an untrusted network.

## Development and validation

```bash
python -m pip install \
  --disable-pip-version-check \
  --no-deps \
  --only-binary=:all: \
  --require-hashes \
  -r requirements/ci-python-3.14-linux-x86_64.txt
./tools/release_check.sh
```

The lock targets CPython 3.14.6 on Linux x86-64. The local pipeline compiles
Python, parses structured files, checks immutable publication contracts, runs the
complete regression suite, builds reproducible archives, and verifies checksums
and ZIP safety. Digest-pinned HACS and hassfest containers execute on
GitHub-hosted runners as the live external validation step.

## Documentation

- `docs/INSTALL.md`
- `docs/ARCHITECTURE.md`
- `docs/SOURCE-ADAPTERS.md`
- `docs/OPERATIONS.md`
- `docs/PRIVACY.md`
- `docs/SECURITY.md`
- `docs/PUBLISHING.md`
- `docs/QUALITY.md`
- `docs/DECISION-TRACE.md`
- `docs/UPGRADE-1.18.0.md`
