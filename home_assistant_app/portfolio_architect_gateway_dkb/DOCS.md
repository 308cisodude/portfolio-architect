# Portfolio Architect Gateway — DKB v1.46.0

Version 1.46.0 removes the temporary migration-only snapshot endpoint after the PA-side legacy DKB CSV bridge was live-proven and retired. Normal DKB CSV acquisition, cached-snapshot age enforcement, private canonical persistence and the isolated anonymous FinTS capability probe are unchanged.

## DKB CSV acquisition

Open the admin-only Home Assistant Ingress page and upload the current DKB depot CSV export(s) as one authoritative batch. Up to eight files are accepted. The importer:

- accepts the established UTF-8 semicolon DKB depot-export format;
- applies the established bounded provider-specific DKB position parsing inside this Gateway;
- selects only the newest export per depot when multiple dated exports are supplied;
- rejects ambiguous same-depot/same-date exports whose contents differ;
- aggregates overlapping instruments by canonical ISIN-first identity;
- uses the oldest selected export date as the conservative source timestamp;
- keeps depot numbers and raw CSV bytes transient; and
- persists only the normalized canonical provider snapshot in the App-private `/data` volume with restrictive permissions.

Each successful batch replaces the complete DKB snapshot. For multiple DKB depots, upload all current exports together; the Gateway does not retain hidden per-depot identifiers or raw source documents between imports.

The App auto-starts in v1.45.0 because the accepted canonical snapshot is an active portfolio source and must survive Home Assistant restarts.

## FinTS remains a separate research gate

The existing registration-gated anonymous BPD capability probe remains available in the same admin-only Ingress UI. It still uses the fixed DKB FinTS endpoint and only anonymous dialog-initialization segments. It does not request a DKB login name, PIN or TAN and does not issue holdings, balance, transaction, order, transfer, payment, debit or withdrawal operations.

A FinTS probe cannot replace, refresh, or silently fall back to the CSV-backed canonical snapshot. Authenticated DKB FinTS acquisition remains disabled until the separate product-registration and authenticated user-capability gates are deliberately satisfied and implemented.

## Security boundary

The public Gateway REST surface remains read-only and bearer-authenticated over verified private-PKI HTTPS. The App has no host network, Docker, Home Assistant API, authentication API or Supervisor API access. The raw import is handled only through authenticated Home Assistant Ingress and is never persisted. Portfolio Architect remains advisory-only and cannot place orders or move money.
