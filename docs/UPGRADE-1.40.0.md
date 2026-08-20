# Upgrade to Portfolio Architect v1.40.0

Portfolio Architect v1.40.0 makes existing broker-schema-3 advisory funding transfers evidence-aware. It does not initiate transfers or trades. Existing broker schemas 1, 2 and legacy schema-3 documents remain compatible; the native broker editor now creates transfer edges with explicit evidence source/date and stale evidenced edges fail closed for route selection.

## Before upgrading

- Keep the existing Portfolio Architect private state, provider configuration and dashboard in place.
- Do not delete or recreate the integration or any Gateway App.
- Existing schema-2 `broker.yaml` remains valid and does not gain cross-provider funding automatically.
- Existing schema-3 edges without provenance remain supported for compatibility; v1.40 does not silently invent evidence for them.
- No trade, cash transfer, provider reauthentication, Trade Republic statement re-import or DKB capability probe is required solely to install this release.

## Upgrade sequence

1. Update the HACS integration to v1.40.0 and restart Home Assistant.
2. Confirm Portfolio Architect returns to its expected healthy/live state.
3. Align the Comdirect, DKB and Trade Republic Gateway Apps to v1.40.0 in place. Their provider runtime behavior is unchanged.
4. No dashboard YAML replacement is required; v1.39.0 presentation remains current.
5. To opt into evidence-backed cross-provider funding, use **Portfolio Architect → Configure → Execution providers → Funding topology → Add funding transfer** and enter only a relationship you have actually verified.

For an evidence-backed edge record:

- exact source provider;
- exact destination provider;
- verified transfer fee;
- a conservative settlement time in business days (`0` means same-business-day availability, not an exact seconds SLA);
- a bounded evidence-source description; and
- the evidence date in `YYYY-MM-DD` form.

The edge is directional. The reverse route is never inferred.

## Freshness behavior

An evidenced edge uses the broker document's existing `fee_data_max_age_days` window. When its evidence becomes older than that window, Portfolio Architect keeps the configuration but does not use the edge for route selection until the operator refreshes the evidence date/source. Future-dated evidence and partial provenance (`source` without `as_of`, or vice versa) fail closed.

Legacy schema-3 edges without provenance retain their historical behavior for backward compatibility. The native editor intentionally does not create new legacy edges.

## What to verify

- healthy/live Portfolio Architect state after restart;
- integration and all three Apps report v1.40.0;
- current v1.39.0 colourful allocation and v1.38.1 signed drift presentation remain unchanged;
- adding an evidenced transfer through the native editor writes `source` and `as_of` together;
- an exact directed edge can make remote provider cash eligible for an advisory route when fee/evidence is fresh;
- the reverse edge remains unavailable unless separately configured;
- no transfer is initiated and no order/payment capability appears anywhere.

## Compatibility

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged;
- presentation schema 2: unchanged;
- broker schemas 1/2/3: retained; schema 3 gains optional per-edge evidence provenance;
- verified private-PKI HTTPS and bearer authentication: unchanged;
- provider acquisition and cash-authorization semantics: unchanged;
- no dashboard migration required.

Rollback does not require converting the broker file if no evidence-backed edge was added. If v1.40-only `source`/`as_of` fields were added to schema-3 funding edges, remove those optional fields before rolling back to a pre-v1.40 integration. Never move or rewrite an already published immutable tag.
