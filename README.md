# Portfolio Architect v1.19.0-rc2

Portfolio Architect is a Home Assistant-native portfolio overview, policy-check,
and deterministic investment-planning system. It supports provider-specific CSV
imports, multi-source consolidation, cost-aware recommendations, and a separate
credential-isolated Gateway App for live Comdirect data.

Portfolio Architect is advisory software. It cannot validate, submit, modify, or
cancel trades, transfer money, initiate payments, or read account transactions.
The v1.19.0-rc2 Gateway adds one explicitly bounded experimental call to Comdirect's
documented non-submitting ex-ante cost-indication endpoint.

## Highlights

- Native Home Assistant entities, configuration flows, diagnostics, repairs, and
  bilingual English/German reference dashboards.
- Deterministic allocation, policy, and cost-aware investment recommendations.
- Private two-evaluation Plan Delta & Decision Trace with bounded reason codes and
  recorder-safe attributes.
- Live Comdirect data through a local credential-isolated Gateway App.
- Experimental admin-only Comdirect instrument metadata and ordinary-order cost
  diagnostics with hard-coded endpoints and sanitized, process-local results.
- Comdirect, DKB, and generic mapped CSV sources with multi-source consolidation.
- Conservative investment-cash handling and explicit transaction-cost policies.
- Optional fee-verification freshness checks and copyable recommended-buy ISINs.
- Reproducible release archives, SHA-256 manifests, SPDX 2.3 SBOMs, and release
  provenance workflows.
- Immutable GitHub Action and validator-image dependencies, plus a hash-locked
  Python validation toolchain, enforced by local and release checks.
- DNS-pinned local REST transport that binds the validated private address set to
  the authenticated connection while preserving Host/SNI identity.

## Release-candidate status

Version 1.19.0-rc2 is an experimental prerelease. Live rc1 acceptance confirmed
that the bounded operations do not validate or submit orders, but also showed that
`fundFlags`/surcharge metadata and ordinary-order cost indications do not reveal
current savings-plan promotion status. The stable known-good baseline remains
v1.18.0, and the v1.19.0-rc2 Gateway App remains marked `experimental`.

## Installation channels

### Manual or prerelease testing

Follow `docs/UPGRADE-1.19.0-rc2.md`. The integration and Gateway App must both be
updated for brokerage-diagnostic testing. Preserve App-private `/data` and retain v1.18.0 artifacts
for rollback.

### Stable HACS installation

Stable users should remain on the latest non-prerelease HACS version. The repository
contains a flat `portfolio_architect.zip` HACS asset, HACS metadata, brand assets,
HACS validation, and hassfest workflows.

See `docs/PUBLICATION-SETUP.md` and `docs/PUBLISHING.md` for maintainer publication.

## Supported environment

- Home Assistant 2026.7.0 or newer
- Python 3.14 for source validation and Gateway builds
- Gateway App 1.19.0-rc2 for experimental brokerage diagnostics
- Gateway App 1.16.1 or newer for the established live portfolio/reserve protocol

The current stable Portfolio Architect release and the immediately preceding stable
release receive security and correctness fixes. Prereleases receive best-effort
support and must have a documented rollback path. See `SUPPORT.md` and
`docs/SUPPORTED-VERSIONS.md`.

## Privacy and security

Bank authentication remains inside the local Gateway App. Home Assistant receives
only the bounded provider-neutral portfolio and health contracts. The selected
investment account identifier, IBAN, account holder, transaction history, OAuth
material, qSession cookie, and bank credentials are not included in the public
portfolio snapshot or diagnostics.

Experimental probe results stay in Gateway process memory. Internal depot and venue
identifiers are represented by short-lived Ingress tokens and are absent from the
sanitized result. Never expose the Gateway REST or Ingress ports to an untrusted
network.

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

The lock targets CPython 3.14.6 on Linux x86-64. The pipeline compiles Python,
parses structured files, checks immutable publication contracts, runs the complete
regression suite, builds reproducible archives, and verifies checksums and ZIP
safety. Digest-pinned HACS and hassfest containers execute on GitHub-hosted runners
as the live external validation step.

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
- `docs/COMDIRECT-FEE-PROBE.md`
- `docs/UPGRADE-1.19.0-rc2.md`
