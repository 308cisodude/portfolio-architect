# Portfolio Architect

Portfolio Architect is a Home Assistant integration for portfolio overview,
policy checks, and deterministic investment planning. It combines independently
acquired holdings and eligible EUR investment cash, explains freshness and policy
findings, and proposes purchases and funding routes. All recommendations are
advisory: Portfolio Architect cannot place orders or move money.

For current changes and the corresponding upgrade guide, read the
[release notes](docs/RELEASE-NOTES.md).

## Portfolio and planning

- Consolidate provider-isolated portfolio snapshots in one Home Assistant service.
- Define target allocations, investment policies, savings-plan routes, fees, and
  optional directed funding relationships through native configuration flows.
- Evaluate evidence age and route readiness before producing an actionable plan.
  Stale or incomplete evidence does not silently become fresh or authoritative.
- Review the plan, cash authorization, source health, policy findings, and
  execution sequence in native entities and generated English/German dashboards.
- Use separate, read-only Gateway Apps for provider acquisition. Gateways publish
  bounded, provider-neutral snapshots over verified private HTTPS and bearer
  authentication; they do not execute transactions.

## Providers and source authority

| Gateway App | Current planning source | Other method |
| --- | --- | --- |
| Comdirect | Live API by default, or an explicitly activated complete holdings-and-cash CSV path | No automatic cross-method fallback |
| DKB | Depot holdings and Girokonto cash CSV by default, or explicitly activated manual FinTS holdings and selected-account booked cash | No automatic cross-method fallback; FinTS observations expire after 14 days |
| Trade Republic | Local `DEPOTAUSZUG` holdings and `KONTOAUSZUG` cash PDF imports | Live API unavailable |
| Generic Import | Mapped holdings CSV, with optional provider-local EUR cash; up to eight separately identified profiles | Fixed CSV method |

The DKB Gateway can select one eligible EUR cash account using masked choices and
manually refresh the authorized depot and selected account. The bank may require
app approval. **CSV remains authoritative after upgrade.** A complete new FinTS
read stages private account-bound evidence; a separate confirmation activates
FinTS for both holdings and cash. The two observations have independent clocks
and a fixed 14-day expiry. Expired or missing FinTS evidence stops that source
without selecting CSV automatically. Investment cash authorization (all eligible
cash, a cap, or a retained reserve) applies to the selected source. The detailed
review remains temporary and the older research shadows stay separate. See the
[DKB upgrade guide](docs/UPGRADE-1.66.0.md).

One provider may advertise several methods, but changing authority is explicit.
There is no silent fallback from a failed or stale source to another method.

## Install and configure

Home Assistant **2026.7.0 or newer** is required. Install the integration through
HACS as a custom **Integration** repository or use the versioned manual drop-in.
Install each Gateway App separately through the Home Assistant App repository or
as a local App; HACS does not install the Apps.

Add **Portfolio Architect** in **Settings → Devices & services**. A new installation
starts without inventing a portfolio source or investment assumptions. Configure
and explicitly adopt a ready Gateway, then complete the native initial-plan setup
or use an existing valid configuration. See the [installation guide](docs/INSTALL.md)
and [dashboard guide](dashboard/README.md).

## Security and privacy

Bank credentials, authentication sessions, raw statements, full account identifiers,
and private Gateway state remain outside Home Assistant entities and diagnostics.
Gateway Apps keep provider-specific acquisition isolated and publish only the
validated portfolio, authorized cash, and bounded health contracts needed by the
integration. DKB FinTS feeds planning only after explicit activation. No Gateway
provides order, transfer, payment, or transaction-history write operations.

Read the [privacy model](docs/PRIVACY.md), [security policy](SECURITY.md),
[architecture](docs/ARCHITECTURE.md), and [support policy](SUPPORT.md).

## Development and validation

The repository includes regression tests, reproducible release archives,
publication checks, privacy checks, HACS and hassfest workflows, and a pinned
Python validation toolchain. See [quality and validation](docs/QUALITY.md) and
[publishing](docs/PUBLISHING.md) for the complete gates.

## AI-assisted development

Generative AI assists implementation, tests, documentation, and release
preparation. The maintainer retains responsibility for architecture, security,
review, merging, and publication. See [AI_POLICY.md](AI_POLICY.md).
