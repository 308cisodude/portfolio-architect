# Portfolio Architect v1.45.0

Portfolio Architect is a Home Assistant-native portfolio overview, policy-check,
and deterministic investment-planning system. It supports provider-isolated acquisition, multi-source consolidation, cost-aware recommendations, and separate read-only Gateway Apps, including DKB depot-CSV acquisition inside the DKB Gateway and simultaneous aggregation of multiple local Gateway REST snapshots.

Portfolio Architect is advisory software. It exposes no trading, order,
transfer, payment, or account-transaction capability.

## Highlights

- Native Home Assistant entities, configuration flows, diagnostics, repairs, and
  bilingual English/German reference dashboards.
- Deterministic allocation, policy, and cost-aware investment recommendations.
- Private two-evaluation Plan Delta & Decision Trace with bounded reason codes and recorder-safe attributes.
- Live Comdirect data through the credential-isolated **Portfolio Architect Gateway — Comdirect** App.
- Provider-neutral consolidation across Comdirect/Trade Republic Gateway REST snapshots plus established DKB and generic CSV sources.
- Provider-owned authorized investment cash with conservative eligibility and optional Gateway caps or retained cash reserves.
- Explicit provider-scoped funding topology that keeps cash pools separate and combines funding source with execution-route economics without moving money.
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
- Verified-HTTPS Gateway transport with per-App private CA trust distributed through
  Home Assistant Supervisor discovery, layered with the existing bearer token.
- DNS-pinned local REST transport that binds the validated private address set to
  the authenticated connection while preserving Host/SNI/certificate identity.

## Provider Gateway Apps

Version 1.45.0 moves active DKB depot-CSV acquisition into the DKB Gateway while retaining the old HA-side DKB parser only as a strict migration-verification bridge. The Gateway persists only a canonical provider snapshot and can replace legacy `dkb_csv` scope only after exact holdings/timestamp equivalence over verified HTTPS. Authenticated DKB FinTS remains gated and separate.

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
- Gateway App 1.16.1 or newer for the established live Comdirect protocol; Gateway App 1.19.0 or newer for configurable cash authorization; 1.19.1 or newer includes the corrected capped-to-all-available transition; 1.20.1 or newer includes the LKG entity-propagation fix; 1.21.0 adds execution/actionability semantics; 1.22.0 adds publication/privacy hardening; 1.24.1 includes the distinct-provider shell startup hotfix; 1.25.0 adds private local Trade Republic `DEPOTAUSZUG` statement import; 1.26.0 adds simultaneous provider Gateway aggregation; 1.26.1 makes instrument identity ISIN-first without changing REST schema 1 or health schema 6; 1.26.2 adds localized dashboard presentation and privacy-safe unavailable-source diagnostics; 1.26.3 closes the remaining German unavailable-state dashboard edge case and polishes policy-compliance layout without changing machine-readable entity states; 1.26.4 attempts native Tile short-date rendering without changing entity states; 1.26.5 moves only dashboard date presentation to additive read-only native `date.*` counterparts after live acceptance showed the v1.26.4 Tile formatter is ineffective for `sensor` DATE states; 1.26.6 fixes non-live REST Gateway source identification without changing acquisition or authentication behavior; 1.26.7 preserves persisted quantities and corrects conditional-request precedence so Gateway cold restarts cannot create a false snapshot-fingerprint change; 1.27.0/1.27.1 introduce per-Gateway private-PKI verified HTTPS; 1.27.2 fixes existing-entry Supervisor discovery eligibility; 1.27.3 fixes DKB Gateway-vs-CSV discovery identity suppression; 1.27.4 decouples Comdirect OAuth session maintenance from portfolio polling while retaining fail-closed migration; 1.28.0 adds only a registration-gated anonymous DKB FinTS capability probe and keeps live DKB acquisition disabled; 1.28.1 refreshes immutable GitHub Actions to Node.js 24-capable major versions without changing runtime behavior; 1.28.2 groups GitHub Actions Dependabot version updates without changing runtime behavior; 1.29.0 adds native policy-dashboard hierarchy without changing entity or runtime contracts; 1.30.0 adds provider-aware local execution routing and route-scoped exception review without changing Gateway wire schemas; 1.31.0 retargets Robotics to the accumulating share class and retires the old distributing exception into audit history; 1.31.1 restores ISIN-only outside-scope holding validation without changing Gateway runtime; 1.31.2 hardens only the DKB registered capability-probe diagnostics/navigation while live DKB acquisition remains disabled; 1.32.0 adds provider freshness observability and cross-provider diagnostic hardening; 1.33.0 separates evidence-age freshness from plan scheduling and adds explicit user-owned evidence-kind thresholds; 1.33.1 corrects the remaining oldest-source schedule anchor without changing Gateway wire schemas; 1.34.0 adds opaque PA-generated 128-bit target IDs and a first-class current-state presentation contract while retaining schema-1 plan compatibility; 1.34.1 fixes whole-portfolio allocation presentation and ISIN-first outside-scope dashboard bindings; 1.35.0 adds provider-scoped cash and explicit advisory funding-transfer topology without changing Gateway wire schemas; 1.35.1 hardens Comdirect session-maintenance transport resilience without changing those wire schemas; 1.35.2 adds native execution-policy editing, explicit promotional/tie-break semantics, and retained-cash authorization; 1.35.3 restores the missing native broker-editor menu labels without changing those semantics; 1.35.4 accepts common human EUR cash-policy formats and replaces the generic invalid-amount Ingress 400 with bounded guidance; 1.36.0 adds native dynamic presentation slots and removes instrument-specific inventories from the reference dashboard; 1.36.1 fixes the live-observed entity-filter/Distribution composition and compact dynamic naming without changing the presentation-slot backend; 1.37.0 adds shared opt-in human-numeric Gateway validation and migrates the established Comdirect cash fields onto it without changing wire/provider semantics; 1.38.0 adds native copy-friendly recommendation ISIN interaction and policy-aware cash context without changing provider runtimes or wire schemas; 1.38.1 restores native dynamic per-target drift bars through bounded presentation slots, core Conditional + Tile cards and the Tile-native bar-gauge feature without changing provider runtimes or wire schemas; 1.39.0 adds paired colourful current/target allocation Tiles through the same bounded native presentation slots without changing provider runtimes or wire schemas; 1.40.0 adds evidence-backed freshness semantics for advisory directed funding edges without adding transfer execution; 1.40.1 fixes native Configure-form compatibility and evidence-date UX without changing funding semantics; 1.41.0 adds independent local Trade Republic `KONTOAUSZUG` cash evidence without changing REST schema 1 or the advisory-only boundary; 1.41.1 prefers sufficient execution-provider-local cash over an otherwise identical zero-fee/zero-day cross-provider funding transfer; 1.42.0 exposes the already-decided funding/purchase sequence as bounded bilingual Home Assistant presentation and renders it through a native dashboard Markdown block without changing route economics or provider runtimes; 1.44.0 adds independent per-route fee evidence and native funding-edge editing without changing route economics or provider runtimes; 1.45.0 moves DKB depot-CSV acquisition into the auto-starting experimental DKB Gateway with exact fail-closed legacy-source migration while authenticated FinTS remains disabled

The current stable Portfolio Architect release and the immediately preceding
stable release receive security and correctness fixes while a documented upgrade
path exists. See `SUPPORT.md` and `docs/SUPPORTED-VERSIONS.md`.

## Privacy and security

Bank authentication remains inside the local Gateway App. Home Assistant receives
only bounded provider-neutral portfolio, authorized-cash, and health contracts.
The selected investment account identifier, IBAN, account holder, transaction
history, OAuth material, qSession cookie, and bank credentials are not included
in the public portfolio snapshot or diagnostics.

Official v1.45.0 Gateway Apps use verified HTTPS on the private Home Assistant App network and retain bearer authentication. Never expose the Gateway REST port to an untrusted network.

## AI-assisted development

Portfolio Architect is developed with substantial use of generative AI, including
AI-assisted implementation, tests, documentation, and release preparation under
maintainer direction. The maintainer remains responsible for architecture,
security decisions, merges, releases, and published content. Automated validation
and live acceptance provide evidence; they do not transfer that responsibility.
Selected material release candidates may also receive a separate security-focused AI
second-opinion review under the limitations documented in `AI_POLICY.md`. The
maintainer retains all merge, release, and publication authority. See `AI_POLICY.md`
for the project's full disclosure and human-controlled development policy.

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
- `docs/TARGET-ARCHITECTURE.md`
- `docs/ARCHITECTURE.md`
- `docs/SOURCE-ADAPTERS.md`
- `docs/OPERATIONS.md`
- `docs/PRIVACY.md`
- `docs/SECURITY.md`
- `docs/PUBLISHING.md`
- `docs/ROADMAP.md`
- `docs/PROVIDER-DIAGNOSTICS.md`
- `docs/GATEWAY-PROVIDERS.md`
- `docs/EXECUTION-PROVIDERS.md`
- `docs/QUALITY.md`
- `docs/DECISION-TRACE.md`
- `AI_POLICY.md`
- `docs/UPGRADE-1.39.0.md`
- `docs/UPGRADE-1.45.0.md`
- `docs/UPGRADE-1.42.0.md`
- `docs/UPGRADE-1.41.1.md`
- `docs/UPGRADE-1.41.0.md`
- `docs/UPGRADE-1.40.1.md`
- `docs/UPGRADE-1.38.1.md`
- `docs/UPGRADE-1.38.0.md`
- `docs/UPGRADE-1.37.0.md`
- `docs/UPGRADE-1.36.0.md`
- `docs/UPGRADE-1.35.4.md`
- `docs/UPGRADE-1.35.3.md`
- `docs/UPGRADE-1.35.2.md`
- `docs/UPGRADE-1.35.0.md`
- `docs/UPGRADE-1.34.1.md`
- `docs/UPGRADE-1.34.0.md`
- `docs/UPGRADE-1.33.1.md`
- `docs/UPGRADE-1.31.2.md`
- `docs/UPGRADE-1.31.1.md`
- `docs/UPGRADE-1.31.0.md`
- `docs/UPGRADE-1.30.0.md`
- `docs/UPGRADE-1.29.0.md`
- `docs/UPGRADE-1.28.2.md`
- `docs/UPGRADE-1.28.1.md`
- `docs/UPGRADE-1.28.0.md`
- `docs/UPGRADE-1.27.4.md`
- `docs/UPGRADE-1.27.3.md`
- `docs/UPGRADE-1.26.7.md`
- `docs/UPGRADE-1.26.6.md`
- `docs/UPGRADE-1.26.5.md`
- `docs/UPGRADE-1.26.4.md`
- `docs/UPGRADE-1.26.3.md`
- `docs/UPGRADE-1.26.2.md`
- `docs/UPGRADE-1.26.1.md`
- `docs/UPGRADE-1.26.0.md`
- `docs/UPGRADE-1.24.1.md`
- `docs/UPGRADE-1.24.0.md`
- `docs/UPGRADE-1.22.0.md`
- `docs/UPGRADE-1.21.0.md`
- `docs/UPGRADE-1.20.1.md`
- `docs/UPGRADE-1.20.0.md`
- `docs/UPGRADE-1.19.1.md`
- `docs/UPGRADE-1.19.0.md`
