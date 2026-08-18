# Upgrade to Portfolio Architect 1.35.0

Version 1.35.0 adds provider-scoped cash and explicit funding-transfer topology while preserving
the established Gateway wire/TLS contracts. Existing broker schema-1 and schema-2 configuration
continues to work unchanged; cross-provider funding is **not** enabled automatically.

## Upgrade procedure

1. Update **Portfolio Architect** through HACS to 1.35.0 and restart Home Assistant once.
2. Confirm the existing portfolio sources return healthy/live state and the expected private-CA
   verified HTTPS diagnostics.
3. If you use the copied reference dashboard, replace or merge the v1.35.0 bilingual dashboard to
   receive the accumulating/distributing Robotics label correction.
4. Update the Comdirect, Trade Republic and DKB Gateway Apps to 1.35.0 in place for package/version
   alignment. **Do not reauthenticate Comdirect** solely because of this release when the existing
   provider session/state is healthy.
5. Keep the existing `broker.yaml` unchanged unless you intentionally want to enable explicit
   cross-provider funding planning.

## Enabling funding topology

To opt in, change `broker.yaml` from schema 2 to schema 3 and add only transfer relationships whose
cost and conservative settlement time you have actually established. Example:

```yaml
schema_version: 3
fee_data_max_age_days: 30
providers:
  comdirect:
    # existing provider configuration remains here
  trade_republic:
    # existing provider configuration remains here

funding_transfers:
  - from_provider: comdirect
    to_provider: trade_republic
    fee_eur: 1.50
    settlement_business_days: 2
```

The values above are an example, not an assertion about a current tariff. Use the transfer cost and
business-day planning delay you actually want Portfolio Architect to assume. Add the reverse edge
separately only if the reverse relationship is also intentionally authorized; PA never infers it.

After reloading/restarting, inspect **Authorized investment cash** and the proposed-buy entity
attributes. Provider-scoped cash exposes the initial authorized amount and remaining amount per
provider. A cross-provider recommendation exposes its funding provider, execution provider,
transfer fee and settlement business days; the authorized-cash entity also contains the aggregate
advisory transfer plan.

## Existing cash authorization remains authoritative

The Gateway-side `all_available` and `capped` settings are unchanged and continue to define the
maximum cash Portfolio Architect may use from that provider. Broker schema 3 does not expand a
Gateway cash authorization and does not make unavailable provider cash actionable.

## DKB probe evidence

The next DKB anonymous capability probe performed under v1.35.0 stores two privacy-safe response
correlation pairs:

- exact bounded HTTP response-body SHA-256 and byte count; and
- decoded bounded FinTS response SHA-256 and byte count.

Existing schema-1/schema-2 probe state remains readable. The FinTS registration gate is unchanged:
a positive `HIWPDS` result remains bank-level evidence only, does not yet enable live DKB holdings,
and authenticated user-capability/UPD validation remains a later gate. Historical probes do not gain invented raw
fingerprints; schema 3 probe state is written only when the real response body was actually
fingerprinted. The raw and decoded response bodies themselves remain ephemeral and are discarded.

## Preserved boundaries

- REST portfolio schema 1 and Gateway health schema 6 are unchanged.
- Existing schema-1/schema-2 broker files retain their established behavior.
- Portfolio Architect remains advisory and performs no transfer or trade.
- DKB live holdings acquisition remains disabled.
- Private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and
  no-plaintext fallback remain unchanged.

No dashboard entity-ID migration is required.
