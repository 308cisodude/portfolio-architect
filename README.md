# Portfolio Architect v1.24.1

Portfolio Architect is a Home Assistant-native portfolio overview, policy-check,
and deterministic investment-planning system. It supports provider-specific CSV
imports, multi-source consolidation, cost-aware recommendations, and separate
provider-isolated read-only Gateway Apps, with Comdirect as the currently released live provider.

Portfolio Architect is advisory software. It exposes no trading, order,
transfer, payment, or account-transaction capability.

## Highlights

- Native Home Assistant entities, configuration flows, diagnostics, repairs, and
  bilingual English/German reference dashboards.
- Deterministic allocation, policy, and cost-aware investment recommendations.
- Private two-evaluation Plan Delta & Decision Trace with bounded reason codes and recorder-safe attributes.
- Live Comdirect data through the credential-isolated **Portfolio Architect Gateway — Comdirect** App.
- Comdirect, DKB, and generic mapped CSV sources with multi-source consolidation.
- Provider-owned authorized investment cash with conservative eligibility and optional Gateway caps.
- Bounded graceful degradation: trusted LKG holdings stay informationally available while stale bank cash and new investment actions fail closed.
- Evidence-based Gateway refresh diagnostics and locally time-derived snapshot freshness.
- Provider-aware Gateway health schema 6 with bounded provider identity and backward-compatible health negotiation.
- Separate scheduled-execution, last-evaluation, and current-actionability semantics; past schedule dates never imply transaction execution.
- Explicit transaction-cost and execution policies.
- Reproducible release archives, SHA-256 manifests, SPDX 2.3 SBOMs, and release
  provenance workflows.
- Fail-closed publication privacy checks plus immutable Gitleaks scanning of the
  tracked tree, complete Git patch history, and built release artifacts.
- Immutable GitHub Action and validator-image dependencies, plus a hash-locked
  Python validation toolchain, enforced by local and release checks.
- DNS-pinned local REST transport that binds the validated private address set to
  the authenticated connection while preserving Host/SNI identity.

## Provider Gateway Apps

Version 1.24.1 retains the separate Comdirect, DKB and Trade Republic Home Assistant App identities introduced in 1.24.0 and fixes startup of the experimental DKB/TR shells. Comdirect remains the stable live provider; DKB and Trade Republic are experimental manual-only shells until their provider-specific acquisition milestones.

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
- Gateway App 1.16.1 or newer for the established live Comdirect protocol; Gateway App 1.19.0 or newer for configurable cash authorization; 1.19.1 or newer includes the corrected capped-to-all-available transition; 1.20.1 or newer includes the LKG entity-propagation fix; 1.21.0 adds execution/actionability semantics; 1.22.0 adds publication/privacy hardening; 1.24.1 includes the distinct-provider shell startup hotfix on top of the provider-aware Gateway contract and health schema 6

The current stable Portfolio Architect release and the immediately preceding
stable release receive security and correctness fixes while a documented upgrade
path exists. See `SUPPORT.md` and `docs/SUPPORTED-VERSIONS.md`.

## Privacy and security

Bank authentication remains inside the local Gateway App. Home Assistant receives
only bounded provider-neutral portfolio, authorized-cash, and health contracts.
The selected investment account identifier, IBAN, account holder, transaction
history, OAuth material, qSession cookie, and bank credentials are not included
in the public portfolio snapshot or diagnostics.

Never expose the Gateway REST port to an untrusted network.

## AI-assisted development

Portfolio Architect is developed with substantial use of generative AI, including
AI-assisted implementation, tests, documentation, and release preparation under
maintainer direction. The maintainer remains responsible for architecture,
security decisions, merges, releases, and published content. Automated validation
and live acceptance provide evidence; they do not transfer that responsibility.
See `AI_POLICY.md` for the project's full disclosure and human-controlled
development policy.

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
Python, parses structured files, checks immutable publication and privacy
contracts, runs the complete regression suite, builds reproducible archives, and
verifies checksums, ZIP safety, and artifact privacy. Digest-pinned HACS, hassfest,
and Gitleaks containers execute on GitHub-hosted runners as external publication
validation. The Gitleaks gate covers the tracked tree, complete Git patch history,
and built release contents before publication.

## Documentation

- `docs/INSTALL.md`
- `docs/ARCHITECTURE.md`
- `docs/SOURCE-ADAPTERS.md`
- `docs/OPERATIONS.md`
- `docs/PRIVACY.md`
- `docs/SECURITY.md`
- `docs/PUBLISHING.md`
- `docs/ROADMAP.md`
- `docs/GATEWAY-PROVIDERS.md`
- `docs/QUALITY.md`
- `docs/DECISION-TRACE.md`
- `AI_POLICY.md`
- `docs/UPGRADE-1.24.1.md`
- `docs/UPGRADE-1.24.0.md`
- `docs/UPGRADE-1.22.0.md`
- `docs/UPGRADE-1.21.0.md`
- `docs/UPGRADE-1.20.1.md`
- `docs/UPGRADE-1.20.0.md`
- `docs/UPGRADE-1.19.1.md`
- `docs/UPGRADE-1.19.0.md`
