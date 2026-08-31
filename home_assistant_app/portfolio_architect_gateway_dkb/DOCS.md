# Portfolio Architect Gateway — DKB v1.61.2

Version 1.61.2 is package alignment for Portfolio Architect's Home Assistant-side primary-Gateway identity-context hotfix. Provider acquisition, health schema 9, canonical evidence clocks, private-PKI transport and no-fallback behavior are unchanged from v1.61.1.

Version 1.60.0 adds read-only authoritative holdings/cash evidence availability and UTC timestamps to the existing Acquisition authority cards. The two clocks remain independent and come only from the canonical CSV snapshot. DKB `csv` remains authoritative; `fints` remains `research_only`, inactive, non-activatable, and authenticated FinTS acquisition remains disabled.

## DKB depot CSV holdings

Open the admin-only Home Assistant Ingress page and upload the current DKB depot CSV export(s) as one authoritative batch. Up to eight files are accepted. The established importer:

- accepts the bounded UTF-8 semicolon DKB depot-export format;
- selects only the newest export per depot when multiple dated exports are supplied;
- rejects ambiguous same-depot/same-date exports whose contents differ;
- aggregates overlapping instruments by canonical identity;
- uses the oldest selected export date as the conservative holdings timestamp;
- keeps depot numbers and raw CSV bytes transient; and
- persists only normalized canonical holdings in the App-private `/data` volume.

A holdings import replaces only holdings evidence. It does not refresh cash evidence.

## DKB Girokonto cash evidence

Version 1.47.0 adds a second, independent upload control for the DKB **Umsatzliste Girokonto** CSV. The cash importer:

- requires the supported `Girokonto` export structure and exactly one dated `Kontostand vom DD.MM.YYYY:` row;
- requires the explicit balance to be EUR and parses it as an exact Decimal;
- validates the expected bounded transaction-table structure without retaining transaction contents;
- treats a positive account balance as eligible/authorized investment cash under `all_available`;
- clamps a zero or negative account balance to EUR 0 eligible/authorized cash and never infers an overdraft or credit facility;
- uses deterministic conservative date evidence, so re-importing the same old file cannot make it fresh merely because it was uploaded again;
- keeps account identifiers, transaction rows, counterparties, references, and the raw CSV transient; and
- persists only the normalized balance and evidence timestamp in a private sibling state file.

A cash import does not refresh holdings evidence. Portfolio Architect freshness-gates this DKB cash using the same imported-statement policy family as Trade Republic cash, while DKB holdings retain their normal Gateway-snapshot freshness policy.

## FinTS remains a separate research gate

The registration-gated anonymous BPD capability probe remains available in the same admin-only Ingress UI. It does not request a DKB login name, PIN or TAN and does not issue holdings, balance, transaction, order, transfer, payment, debit or withdrawal operations.

FinTS cannot replace, refresh, or silently fall back to either CSV evidence family. Authenticated DKB FinTS acquisition remains disabled until the separate product-registration and authenticated user-capability gates are deliberately satisfied and implemented.

## Security boundary

The public Gateway REST surface remains read-only and bearer-authenticated over verified private-PKI HTTPS. Uploaded CSVs are handled only through authenticated Home Assistant Ingress and are never persisted. Portfolio Architect remains advisory-only and cannot place orders or move money.
