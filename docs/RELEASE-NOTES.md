# Portfolio Architect 1.26.2

Version 1.26.2 is a presentation and diagnostics polish release on top of the
live-accepted v1.26.1 multi-provider/ISIN-first baseline. It does not change
portfolio calculation, provider acquisition, Gateway wire schemas, or the
read-only security boundary.

## German reference-dashboard presentation

The German reference dashboard now consumes explicit German presentation
attributes for state values that Home Assistant otherwise renders according to the
global frontend language. Machine-readable entity states and options remain stable
for automations and API consumers.

The affected presentation includes plan frequency, actionability, execution policy,
source/freshness state, Gateway status/operating mode, refresh schedule/trigger,
attention reason/recommended action, unavailable monetary/count values, and
relevant timestamps. The English reference dashboard continues to use the normal
machine-readable/frontend presentation except where the source-unavailable tile
uses the new bounded source summary.

Copied/imported dashboards remain user-owned and are not overwritten by HACS. An
existing copied dashboard must deliberately adopt the updated v1.26.2 reference
YAML to receive these presentation changes.

## Source-specific outage visibility

When a configured source prevents a live aggregate, Portfolio Architect now exposes
bounded privacy-safe metadata:

- `unavailable_source_count`;
- `unavailable_source_ids`;
- `unavailable_source_summary`; and
- `unavailable_source_summary_de`.

The reference **Source unavailable / Quelle fehlt** tile renders the corresponding
summary, for example `Trade Republic Gateway` / `Trade-Republic-Gateway`. DKB CSV
sources use bounded instance labels such as `DKB CSV 2`; configured paths are never
exposed. Gateway summaries contain provider identity only, never endpoint URLs or
bearer tokens.

Additional REST Gateway health failures are collected for all configured
supplemental Gateways during a refresh so several simultaneous failed sources can
be named. Atomic aggregation remains unchanged: if any configured source fails,
Portfolio Architect does not calculate from the successful subset. A matching
complete Home Assistant LKG is retained or the refresh fails closed.

## Attention-reason correction

The existing coordinator state `supplemental_source_unavailable` is now a declared
and translated Gateway-attention enum option. Supplemental-source outages therefore
show a meaningful reason instead of `None`, while the existing recommended action
remains bounded (`check_connectivity`).

## Compatibility and security

Payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
the current wire/data contracts; health schemas 1–5 remain supported. The historical experimental `v1.19.0-rc2`
brokerage diagnostics/fee-probe work remains separate and is not promoted by this release.

- payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 6 (unchanged)
- existing entity IDs / unique IDs: unchanged
- machine-readable state values: unchanged, except the already-existing
  `supplemental_source_unavailable` reason is now correctly declared by its entity
- ISIN-first identity and WKN fallback semantics: unchanged from v1.26.1
- Comdirect authorized-cash semantics: unchanged
- Trade Republic statement import: unchanged
- DKB Gateway remains an experimental manual-only fail-closed shell
- No trading, order, transfer, payment, or transaction-history capability is added.

Unavailable-source metadata is derived only from bounded provider/source-instance
identities. It excludes private Gateway endpoint URLs, bearer tokens, DKB CSV paths,
account/depot/customer identifiers, and provider documents.

DKB live Gateway acquisition remains a later provider-specific milestone; v1.26.2
does not promote the experimental DKB shell into a live acquisition source.

The release does not move PDF parsing into Portfolio Architect: Trade Republic
statement parsing remains isolated in the Trade Republic Gateway App.
