# Upgrade to Portfolio Architect 1.26.1

Version 1.26.1 is the ISIN-first identity hotfix for the v1.26 multi-Gateway
release. Version 1.26.0 successfully connected and validated the Trade Republic
Gateway during live acceptance, but an ISIN-only Trade Republic holding remained
outside the target architecture because the calculation path still expected a WKN
key. Version 1.26.1 corrects that identity model without changing any wire schema.

## What changes

- ISIN is the canonical instrument identity whenever it is available.
- WKN is used only as fallback identity when the source position has no ISIN.
- When both are present, WKN is consistency evidence and may not override a
  contradictory ISIN.
- Ambiguous mappings fail closed: one WKN cannot identify multiple ISINs and one
  ISIN cannot be merged with contradictory WKN values.
- REST schema 1 `identifier` values that are the same as the supplied ISIN are no
  longer copied into the internal WKN field.
- The v1.26 multi-Gateway configuration, provider counts, source provenance, atomic
  aggregation/LKG behavior and Trade Republic auto-start remain unchanged.

## Upgrade procedure

1. Update **Portfolio Architect Gateway — Comdirect** to 1.26.1 in place.
2. Update **Portfolio Architect Gateway — Trade Republic** to 1.26.1 in place.
3. Update Portfolio Architect to 1.26.1 through HACS.
4. Restart Home Assistant once after the HACS update.
5. Do not uninstall/reinstall either Gateway App; their private tokens, Comdirect
   authentication state and accepted Trade Republic snapshot must remain in place.
6. If the Trade Republic Gateway was temporarily removed from Portfolio Architect
   after the v1.26.0 acceptance failure, add it again under **Portfolio sources →
   Additional REST Gateways** using the same private App-network endpoint and bearer
   token.

No Comdirect reauthentication, account reselection, cash-policy migration, entity
migration or Trade Republic statement re-import is required solely by this hotfix.

## Live acceptance

A successful v1.26.1 acceptance requires:

1. Comdirect remains healthy with `provider_id: comdirect` and no reauthentication
   or migration.
2. Trade Republic remains healthy/OK with `provider_id: trade_republic` and the
   previously accepted private statement snapshot.
3. Portfolio Architect accepts the configured Trade Republic additional Gateway.
4. After refresh, the accepted aggregate reports `source_count: 3`,
   `provider_count: 3`, and provider IDs for Comdirect, DKB and Trade Republic.
5. Target architecture changes from 6/7 to **7/7**; Robotics is held with Trade
   Republic provenance while the existing MSCI World provenance remains Comdirect
   + DKB.
6. The Source provider attribute reports `Multi-source portfolio · 3 providers`.
7. Stop the Trade Republic App temporarily. Portfolio Architect must retain the
   complete 7/7 aggregate as degraded/non-actionable Home Assistant LKG and must
   not recompute a misleading live 6/7 portfolio.
8. Start Trade Republic again and confirm automatic recovery to healthy/live 7/7
   without reconfiguration or Comdirect disturbance.

Successful live acceptance establishes v1.26.1 as the first known-good end-to-end
multi-provider Gateway aggregation baseline.

## Compatibility

- payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 6 (unchanged)
- existing Home Assistant entity IDs / unique IDs: unchanged
- existing Comdirect authorized-cash semantics: unchanged
- v1.20/v1.20.1 LKG semantics: unchanged apart from applying atomically to the
  already-configured multi-Gateway source set
- v1.21 actionability semantics: unchanged
- v1.22 privacy/publication gates: unchanged
- no trading, order, transfer, payment or transaction-history capability
