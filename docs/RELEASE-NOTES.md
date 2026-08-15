# Portfolio Architect 1.27.3

Version 1.27.3 fixes the residual DKB Supervisor-discovery UX defect found immediately
after live acceptance of the v1.27.2 HTTPS migration fix. The primary Comdirect and
supplemental Trade Republic sources migrated successfully to private-CA verified
HTTPS, but Home Assistant still displayed one pending **Discovered → Portfolio
Architect → Add** card.

The cause was a provider-identity namespace mix-up. The DKB Gateway publishes the
bounded Gateway provider ID `dkb`, while the established DKB CSV importer identifies
its source as `dkb_csv`. The v1.27.2 suppression code compared Gateway discovery
identity against the CSV provider constant, so a real DKB Gateway discovery could
never match the suppression condition.

## Explicit Gateway provider identity

Version 1.27.3 introduces a small Home Assistant-side Gateway provider-identity module
that deliberately separates Gateway IDs from CSV importer IDs. DKB Gateway discovery
uses `dkb`; DKB CSV remains `dkb_csv`. A shared collision helper is used by all three
relevant paths:

- Supervisor discovery before a new supplemental-provider confirmation card is shown;
- explicit confirmation of a newly discovered supplemental Gateway; and
- manual addition of a supplemental REST Gateway after health-schema-6 provider
  identity is known.

Therefore an existing configured DKB CSV source suppresses the DKB Gateway discovery
prompt and also prevents DKB Gateway addition through the other supported setup paths.
Trade Republic and Comdirect identities remain unaffected.

## Security and architecture

This is a narrow Home Assistant discovery/provider-collision fix. The live-proven
v1.27.2 transport and migration architecture is unchanged:

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported where previously supported;
- per-installation private CA and hostname-verified HTTPS: unchanged;
- bearer authentication remains independent of TLS;
- verified HTTPS must succeed before a legacy HTTP source is migrated;
- changed CA trust for an already secured source is refused;
- no automatic plaintext fallback is introduced;
- the one Portfolio Architect config-entry architecture remains explicitly enforced;
- Comdirect OAuth/session/PhotoTAN/account/cash behavior: unchanged;
- Trade Republic `DEPOTAUSZUG` statement import: unchanged;
- DKB Gateway remains experimental/manual-only/fail-closed with no live acquisition;
- DKB live Gateway acquisition remains a later provider-specific milestone;
- Trade Republic statement parsing remains isolated in its Gateway App; this release
  does not move PDF parsing into Portfolio Architect;
- portfolio calculations, source atomicity, LKG behavior, entities and dashboard
  behavior: unchanged;
- No trading, order, transfer, payment, or transaction-history capability is added;
  and
- the historical experimental `v1.19.0-rc2` brokerage diagnostics/fee-probe work
  remains separate and is not promoted by this release.

The upgrade path is documented in `docs/UPGRADE-1.27.3.md`. No dashboard YAML
migration is required.
