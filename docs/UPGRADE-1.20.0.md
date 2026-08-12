# Upgrade to Portfolio Architect 1.20.0

Version 1.20.0 adds graceful last-known-good operation, evidence-based Gateway
freshness diagnostics, and transparent AI-assisted-development disclosure.

## What changes

During a live REST outage or rejected incoming snapshot, a previously validated
portfolio may remain visible as last-known-good while it is inside the bounded
retention window. This is informational continuity, not permission to act on stale
bank data.

REST-based recommendation and cash entities now require an actionable source.
When the source is degraded, reauthentication is required, health is unavailable,
or integrity validation fails, holdings/allocation/policy can remain visible but
new cash-based recommendations become unavailable until live trusted data returns.

Refresh-overdue diagnostics now require current evidence. Snapshot age and expiry
are calculated from the accepted timestamp and tick locally once per minute.

## Upgrade procedure

1. Update **Portfolio Architect Gateway** to 1.20.0 through **Settings → Apps**.
2. Update **Portfolio Architect** to 1.20.0 through HACS.
3. Restart Home Assistant once after the HACS update.
4. Confirm `Version` reports 1.20.0 and normal live health returns `Source healthy`,
   `Gateway status: OK`, `Operating mode: Live`, and `Snapshot verified`.
5. Confirm no new Repairs or Portfolio Architect warnings appear.

No reconfiguration, new account selection, or new Comdirect PhotoTAN bootstrap is
required solely by this upgrade. If Comdirect independently requires
reauthentication, complete it through the existing Gateway App Web UI.

## Resilience acceptance

A useful live acceptance is to observe a temporary degraded state only when it
occurs naturally or in a deliberate test environment. While degraded:

- trusted holdings and allocation remain visible inside the retention window;
- `Source healthy` is off and the operating mode indicates LKG/degraded behavior;
- authorized investment cash and new purchase recommendations are not actionable;
- stale schedule telemetry alone cannot create a refresh-overdue failure; and
- the system automatically returns to live operation after a valid fresh snapshot
  is accepted.

Do not intentionally corrupt credentials or Home Assistant `.storage` data to
create this test.

## Compatibility

Payload schema 8, REST schema 1, Gateway health schema 5, entity IDs, unique IDs,
and the v1.19 authorized-cash contract remain unchanged. Gateway App 1.19.1 is
protocol-compatible, while the normal supported deployment keeps integration and
App package versions aligned at 1.20.0.
