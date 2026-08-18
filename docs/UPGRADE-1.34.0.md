# Upgrade to Portfolio Architect 1.34.0

Version 1.34.0 introduces opaque 128-bit target identity and a first-class current-state
presentation model. Provider runtime and wire contracts are unchanged.

## Upgrade order

1. Update **Portfolio Architect** through HACS to 1.34.0 and restart Home Assistant once.
2. Leave the existing live schema-1 `portfolio.yaml` unchanged initially. Confirm the same target
   coverage, source freshness, recurring dates, provider aggregation and existing target entities.
3. Update **Portfolio Architect Gateway — Comdirect**, **Trade Republic**, and **DKB** to 1.34.0 in
   place, preserving every App-private `/data` volume.
4. Do not reauthenticate Comdirect, re-import Trade Republic, re-enter DKB registration, or run a
   DKB FinTS probe merely because of this release.
5. Only after Phase A is healthy, back up `/config/portfolio-architect/portfolio.yaml` and perform
   the deliberate schema-2 target-identity migration.
6. The schema-2 migration intentionally changes target machine identity from the old semantic IDs
   to opaque PA-generated 128-bit IDs. Replace the copied reference dashboard at the same time if
   you use it, because its static target cards must point at the new IDs until the later dynamic-
   dashboard milestone.
7. Re-evaluate and confirm the same economic/strategy state: seven configured roles, six currently
   held target roles, accumulating Robotics still missing, distributing Robotics still outside
   scope, no automatic sell, unchanged freshness and unchanged 7-Sep/5-Oct schedule semantics.

There is no config-entry, bank-authentication or Gateway-wire migration. There is also no source,
broker, exceptions, freshness or schedule migration. No dashboard replacement is required for the
software/App upgrade or the Phase A compatibility check. If the operator deliberately applies the
supplied opaque-ID schema-2 reference-plan migration, the matching static reference dashboard must
be replaced at the same time. In Phase B, migrate the user-owned `portfolio.yaml` to schema 2 using
the supplied migration package.

## Portfolio schema 2

A schema-2 target uses an opaque target ID:

```yaml
schema_version: 2
portfolio:
  allocation:
    - target_id: target_0123456789abcdef0123456789abcdef
      name: Example equity ETF
      isin: IE0000000001
      wkn: ABC123
      target_pct: 55
      buy_enabled: true
```

The 32 hexadecimal digits represent 128 random bits. The ID is generated once by the native PA
plan flow for a newly created target and is independent from instrument identifiers and names.
For manually maintained schema-2 YAML, the explicit opaque ID must be persisted; PA never creates
a new token merely while reading the file.

Existing schema-1 `id` plans remain supported. Historical UI overrides remain supported. Schema 2
requires the opaque form.

ISIN is canonical instrument identity. WKN remains secondary fallback/validation metadata and is
not used to create target identity.

## Target lifecycle

- Editing an existing current target keeps its target ID.
- Deleting a target removes the current strategic role; PA keeps no retired-target/tombstone DB.
- Adding a target later creates a fresh target ID even if its ISIN matches a formerly deleted
  target.
- If an operator manually pastes a previously used explicit ID into YAML, that explicit config is
  authoritative; PA does not maintain history just to reject deliberate file contents.

## Outside-current-plan holdings

Outside-scope holdings are not configured objects. They are current evidence from portfolio
sources. No manual PA deletion is needed after a sale: once all relevant accepted source evidence
no longer reports the holding, the next successful evaluation removes it automatically.

An unavailable source, an older still-valid statement/CSV, or LKG state does not count as evidence
of absence and therefore cannot make a holding disappear prematurely.

## First-class presentation model

`sensor.portfolio_architect_presentation_model` exposes current structural target/current-plan/
outside-scope inventory. It is the backend prerequisite for a later dynamic native dashboard.
The current reference dashboard remains static and v1.34.0 adds no custom frontend dependency.

The policy tile wording changes from **Next review** to **Exception review** /
**Ausnahmeprüfung**.

## Preserved boundaries

- payload schema 8 unchanged
- REST portfolio schema 1 unchanged
- Gateway health schema 6 unchanged
- source freshness policy unchanged
- recurring schedule behavior unchanged
- Comdirect provider behavior unchanged
- Trade Republic statement import/private diagnostics unchanged
- DKB anonymous FinTS probe unchanged and still non-live; `HIWPDS` remains bank-level capability evidence only and authenticated user-capability/UPD remains a later gate. No holdings acquisition is enabled by this release
- private-PKI HTTPS/bearer/DNS/no-plaintext-fallback unchanged
- no trading, order, automatic sell, transfer, payment or transaction-history capability
