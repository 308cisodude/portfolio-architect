# Generic target architecture

Portfolio Architect treats the target architecture as current user-owned configuration. The
reference seven-ETF retirement plan under `examples/current-plan` is an example only; no
calculation contract assumes those seven targets exist.

Portfolio Architect remains deliberately about **the portfolio now and the next investment
cycle**. It is not a strategy-history or target-history database.

## Opaque current-target identity

Portfolio schema 2 makes each current strategic target explicit with `target_id`:

```yaml
schema_version: 2
portfolio:
  allocation:
    - target_id: target_0123456789abcdef0123456789abcdef
      name: Example equity ETF
      isin: IE0000000001
      wkn: ABC123
      target_pct: 70
      buy_enabled: true
```

A schema-2 target ID has the exact form `target_` plus 32 lowercase hexadecimal digits.
The 32 hexadecimal digits contain 128 random bits generated once by Portfolio Architect's
native plan flow. At most 32 positive-weight targets are supported and the positive target
weights must total exactly 100%.

The target ID is the durable machine identity of one **currently configured strategic role**.
It is independent from:

- ISIN;
- WKN;
- the security or target display name;
- target order; and
- target weight or purchase eligibility.

For the lifetime of an existing target, keep the same target ID when reordering, renaming,
changing its weight/buy policy, or deliberately replacing the instrument assigned to that
same strategic role.

Home Assistant per-target entity/unique-ID identity is anchored to this machine target ID.
The opaque token is not parsed to obtain an instrument or a human label.

Portfolio schema 1 remains supported and uses the historical human-readable `id` field.
Historical plan overrides with those IDs also remain loadable. Schema 2 deliberately raises
the identity bar: `target_id` is required and must use the opaque 128-bit format. If both
`target_id` and legacy `id` are supplied they must match exactly.

## New target creation and deletion

A new target created through Portfolio Architect receives a fresh opaque ID at the moment the
new target role is created. The ID generator takes no instrument identity input and never
derives the token from ISIN, WKN, name, or list position.

Deleting a target removes that current strategic role from Portfolio Architect. PA does not
keep a tombstone database or retired-target registry.

If a user later adds a target again, PA creates a fresh target ID even when the chosen
instrument has exactly the same ISIN as a target that existed years earlier. Matching an old
instrument is not evidence that the old strategic role should be resurrected.

A manually maintained schema-2 `portfolio.yaml` must persist its explicit target IDs. PA never
generates a new token merely while reading a file because doing so would churn Home Assistant
identity on every reload. Advanced file-plan users therefore create/persist an opaque token
once; the normal native plan flow generates it automatically.

## Instrument identity is separate

ISIN is the canonical instrument identity. WKN remains secondary German metadata and may be
used only as an established fallback/validation identifier where ISIN is unavailable or where
a provider supplies WKN as additional evidence. Neither identifier participates in target-ID
generation.

The native plan editor keys selectable plan candidates by ISIN. WKN may still be displayed as
useful secondary metadata, but is not used to invent or select a target identity.

An instrument migration under an unchanged target ID may temporarily make the target missing
until a holding matches the new security. Portfolio Architect does not automatically sell the
former instrument: if it remains held, it becomes an outside-current-plan holding under the
established ISIN-first holding identity model.

## Outside-scope holdings are evidence-driven

Outside-current-plan holdings have no target ID and no persistent PA configuration object.
They exist only because current accepted portfolio-source evidence says the holding exists.

When every relevant accepted source no longer reports that instrument, the holding disappears
from the next successfully calculated whole-portfolio and presentation model automatically.
No PA deletion action is required.

This is intentionally fail-closed around source freshness: an unavailable provider, an older
still-accepted statement/CSV, or an active last-known-good snapshot is not interpreted as proof
that a holding was sold. The position disappears only when accepted evidence supersedes it.

The distinction is deliberate:

- configured targets persist because they express **current intent**;
- non-target holdings persist only while accepted sources provide **current evidence**.

## First-class presentation model

`sensor.portfolio_architect_presentation_model` exposes bounded presentation schema 2. It is a
structural index rather than another monetary snapshot. Its attributes include:

- ordered current target IDs and bounded target metadata;
- which current target roles are held;
- current-plan holding IDs;
- the complete current outside-scope holding inventory;
- source provenance IDs for target/current/outside holdings;
- current plan actionability state; and
- aggregate policy state.

Each target row uses `target_id` as its `entity_key`; each outside holding uses its stable
ISIN-first `position_id`. Live values, quantities, drift, proposed purchases and other
high-churn/actionable data remain on the existing dedicated native entities.

v1.36 consumes the structural contract with bounded presentation-slot adapter entities and native `entity-filter` cards, removing instrument-specific inventory lists from the reference dashboard. Slots are UI projections only and repeat the stable target/holding identity in attributes. No `auto-entities`, card-mod, custom JavaScript, or other custom frontend dependency is added.

## Security and privacy boundaries

- target count and target-ID format are bounded;
- schema-2 target IDs are opaque 128-bit random machine identities;
- duplicate target IDs, ISINs and established WKN validation conflicts fail closed;
- target-ID compatibility aliases must agree exactly;
- presentation metadata is built only from validated current portfolio data;
- no target-history/tombstone database is introduced;
- no bank account, authentication, transaction-history or provider credential material is
  introduced by the presentation contract; and
- Portfolio Architect remains advisory and exposes no trading/order/sell/transfer/payment
  capability.
