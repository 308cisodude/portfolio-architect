# Portfolio Architect Gateway — DKB v1.45.1

Version 1.45.1 fixes legacy CSV migration when the exact comparison snapshot is older than the normal Gateway serving-age limit. A bearer-authenticated verified-HTTPS migration endpoint can expose only the already-normalized canonical snapshot for equivalence checking while the normal portfolio endpoint remains fail-closed.

## DKB CSV acquisition

Open the admin-only Home Assistant Ingress page and upload the current DKB depot CSV export(s) as one authoritative batch. Up to eight files are accepted. The importer:

- accepts the established UTF-8 semicolon DKB depot-export format;
- applies the same bounded position parsing as the legacy Portfolio Architect `dkb_csv` adapter;
- selects only the newest export per depot when multiple dated exports are supplied;
- rejects ambiguous same-depot/same-date exports whose contents differ;
- aggregates overlapping instruments by canonical ISIN-first identity;
- uses the oldest selected export date as the conservative source timestamp;
- keeps depot numbers and raw CSV bytes transient; and
- persists only the normalized canonical provider snapshot in the App-private `/data` volume with restrictive permissions.

Each successful batch replaces the complete DKB snapshot. For multiple DKB depots, upload all current exports together; the Gateway does not retain hidden per-depot identifiers or raw source documents between imports.

The App auto-starts in v1.45.0 because the accepted canonical snapshot is an active portfolio source and must survive Home Assistant restarts.

## Portfolio Architect migration

Existing installations may still contain legacy HA-side `dkb_csv` supplemental paths. When Supervisor discovers the DKB Gateway, Portfolio Architect offers a dedicated migration rather than adding a duplicate source. The cut-over succeeds only when:

- private-CA HTTPS and the App bearer token validate;
- Gateway health schema/provider identity and snapshot integrity validate;
- the canonical Gateway holdings, quantities and instrument identities match the selected legacy CSV view exactly; and
- the conservative source timestamp matches exactly.

Only then does one config-entry mutation add the `dkb` Gateway and remove the legacy `dkb_csv` paths. A mismatch leaves the existing source configuration unchanged. New PA-side legacy DKB CSV sources are no longer offered; the old parser remains only as a migration verifier for this bridge release.

## FinTS remains a separate research gate

The existing registration-gated anonymous BPD capability probe remains available in the same admin-only Ingress UI. It still uses the fixed DKB FinTS endpoint and only anonymous dialog-initialization segments. It does not request a DKB login name, PIN or TAN and does not issue holdings, balance, transaction, order, transfer, payment, debit or withdrawal operations.

A FinTS probe cannot replace, refresh, or silently fall back to the CSV-backed canonical snapshot. Authenticated DKB FinTS acquisition remains disabled until the separate product-registration and authenticated user-capability gates are deliberately satisfied and implemented.

## Security boundary

The public Gateway REST surface remains read-only and bearer-authenticated over verified private-PKI HTTPS. The App has no host network, Docker, Home Assistant API, authentication API or Supervisor API access. The raw import is handled only through authenticated Home Assistant Ingress and is never persisted. Portfolio Architect remains advisory-only and cannot place orders or move money.
