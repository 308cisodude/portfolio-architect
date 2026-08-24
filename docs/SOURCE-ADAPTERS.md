# Portfolio source adapters

Portfolio Architect consumes canonical provider-neutral positions before policy and investment-plan calculations begin. Provider-specific acquisition belongs to the provider Gateway Apps; the Home Assistant integration retains only the provider-neutral mapped-CSV escape hatch until a dedicated generic import Gateway replaces it in a later milestone.

## Comdirect Gateway

**Portfolio Architect Gateway — Comdirect** owns both supported Comdirect acquisition modes:

- **Live API** — authenticated read-only Comdirect acquisition with the established OAuth/session/PhotoTAN boundary and provider-scoped authorized cash.
- **Static CSV** — explicit depot-CSV holdings plus optional Girokonto Umsatz CSV cash. Holdings and cash retain independent evidence clocks.

The modes are mutually exclusive and never silently fall back to one another. Raw CSV bytes, filenames, account/depot identifiers, transaction descriptions, counterparties and transaction rows remain transient; only normalized provider state and bounded evidence timestamps persist in the App-private volume.

Portfolio Architect no longer contains a provider-specific Comdirect CSV adapter or migration parser as of v1.49.0.

## DKB Gateway

**Portfolio Architect Gateway — DKB** owns DKB depot-CSV holdings and independent Girokonto CSV cash acquisition. Uploaded documents are parsed inside the provider App and only normalized evidence is served through the canonical authenticated REST snapshot.

Authenticated DKB FinTS holdings acquisition remains disabled. The isolated capability probe is research-only and cannot replace or silently fall back from CSV evidence.

## Trade Republic Gateway

**Portfolio Architect Gateway — Trade Republic** owns the documented local `DEPOTAUSZUG` holdings and `KONTOAUSZUG` cash statement families. PDFs remain transient private input; only normalized holdings/cash evidence is persisted and served through the canonical authenticated REST snapshot.

## Generic EUR CSV

The remaining Home Assistant-side local-file adapter is provider-neutral. It requires explicit mappings for identifier, name and EUR market value. Optional mappings cover ISIN, type and currency. It does not derive values from price and quantity and does not perform currency conversion.

This generic adapter is deliberately not a Comdirect/DKB/Trade Republic parser. A later roadmap milestone will move this mapped-CSV capability into a dedicated generic import Gateway as well.

## Multi-source consolidation

A primary Gateway/local generic source can be combined with additional provider Gateways. Every configured source is validated independently and the complete set is aggregated atomically:

1. ISIN is the canonical cross-source identity when present.
2. WKN is used only when no ISIN is available.
3. EUR values are summed without intermediate rounding.
4. Provider/source provenance remains attached to the aggregate.
5. Identity/type discrepancies become bounded diagnostic conflicts.
6. A configured provider failure never silently drops that provider and recalculates a smaller portfolio.
7. A matching complete Home Assistant last-known-good aggregate may remain informationally available, while new investment actionability fails closed until the full configured source set is healthy again.

Verified private-PKI HTTPS, bearer authentication, DNS pinning and snapshot-integrity checks remain mandatory for official Gateway sources.

## Optional authorized investment cash in REST schema 1

A conforming provider Gateway may publish the established optional `investment_reserve` / `investment_cash` evidence through REST portfolio schema 1. Provider-scoped cash remains separate between providers and may be used by Portfolio Architect only within the explicit advisory execution/funding model. Portfolio Architect never initiates transfers, payments or orders.
