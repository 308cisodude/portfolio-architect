# Upgrade to Portfolio Architect 1.32.0

Version 1.32.0 adds provider freshness observability and a shared provider-diagnostics
security foundation. It does not relax Portfolio Architect's existing stale-data actionability
rule and does not enable DKB live acquisition.

## Upgrade order

1. Update **Portfolio Architect** through HACS to 1.32.0 and restart Home Assistant once.
2. Replace the supplied bilingual dashboard YAML if you use the reference dashboard and want
   the new visible stale-source/actionability explanation.
3. Update **Portfolio Architect Gateway — Comdirect** to 1.32.0 in place.
4. Update **Portfolio Architect Gateway — Trade Republic** to 1.32.0 in place.
5. Update **Portfolio Architect Gateway — DKB** to 1.32.0 in place.

Preserve every App-private `/data` volume. Do not recreate sources, replace bearer tokens or
change private-CA trust merely for this upgrade.

Do not reauthenticate Comdirect solely because of this release when the current session is
healthy. Do not re-import the Trade Republic statement solely because of this release. Do not
re-enter the DKB FinTS registration or run another DKB probe solely because of this release.

There is no portfolio-plan, config-entry, bank-authentication or Gateway-wire migration. The
reference dashboard YAML **does change** only to show the new bounded blocker detail; existing
custom dashboards remain runtime compatible.

## Freshness observability without policy relaxation

The existing age-threshold actionability rule remains unchanged. Portfolio Architect still
uses the oldest contributing source as the aggregate freshness gate. A stale contributing
source can therefore keep the entire investment plan non-actionable.

Version 1.32.0 adds bounded per-source evidence to the Portfolio sources and Snapshot
freshness entities, including source/provider, evidence kind, source timestamp, locally
derived age, currently applicable threshold and whether the source is inside that threshold.
It also adds bounded English/German stale-source and plan-actionability details.

With the current live three-source topology, the expected state before refreshing the old DKB
CSV is:

- Comdirect: inside the existing 168-hour freshness window;
- Trade Republic statement: inside the existing 168-hour freshness window;
- DKB CSV: outside the existing 168-hour freshness window;
- `data_fresh: false`;
- `plan_actionable: false` with reason `data_stale`.

This is intentional. Version 1.32.0 does not introduce provider-specific freshness limits and
does not ignore a stale source based on contribution size.

## Provider-specific diagnostic hardening

`docs/PROVIDER-DIAGNOSTICS.md` defines the common retention/redaction boundary.

### Trade Republic

The App now keeps only its latest bounded statement-import outcome in private mode-`0600`
state. Only explicitly allowlisted/genericized parser and form errors can survive persistence;
unexpected document-derived text is replaced by a fixed generic message. A malformed stored
diagnostic is never echoed back. A later successful import replaces obsolete failure evidence.

The uploaded PDF remains in memory only and is not stored. No persistent PDF SHA-256 is
introduced.

### Comdirect

The runtime behavior is unchanged. Existing bounded refresh failure classes, OAuth rejection
reasons and App-relative Ingress navigation are explicitly regression-protected. Authenticated
remote bodies/free text, credentials, OAuth/qSession state and private account material remain
excluded from diagnostics.

### DKB

The live-accepted v1.31.2 anonymous FinTS diagnostic behavior is unchanged apart from package
metadata. Existing configured registration and persisted `bank_rejected` evidence survive an
in-place update. The current product-registration propagation wait should not be disturbed
merely for v1.32.0.

The DKB probe still sends no holdings, balance, transaction, order, transfer, payment or debit
business transaction. `HIWPDS` remains only bank-level capability evidence; authenticated user
capability/UPD and DKB-App decoupled authentication remain mandatory later gates before live
holdings could be considered.

## Dashboard acceptance

After replacing the reference dashboard, the Runtime health freshness Tile should show the
bounded stale-source summary when freshness is off, and the unavailable Investment plan Tile
should show the corresponding actionability detail. The dashboard uses only native Home
Assistant Tile attributes (`state_content`).

No custom frontend component is required.
