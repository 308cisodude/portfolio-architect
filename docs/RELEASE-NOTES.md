# Portfolio Architect v1.62.3 release notes

v1.62.3 is a narrow Trade Republic cash-statement compatibility hotfix on top of v1.62.2. A freshly generated native Trade Republic `KONTOAUSZUG` was rejected because the provider rendered September as the locale-aware German abbreviation `Sept.` in the authoritative `BARMITTELÜBERSICHT` as-of line. Review of the complete German abbreviated month set also showed that a robust provider parser must handle three- and four-letter labels and months without a trailing period rather than special-case September.

## Trade Republic German month-label compatibility

The Trade Republic Gateway now accepts a bounded explicit matrix matching the German abbreviated month labels used by locale-aware documents:

`Jan.`, `Feb.`, `März`, `Apr.`, `Mai`, `Juni`, `Juli`, `Aug.`, `Sept.`, `Okt.`, `Nov.`, `Dez.`

Previously accepted aliases (`Mär.`, `Mar.`, `Mai.`, `May.`, `Jun.`, `Jul.`, `Sep.`, `Oct.`, `Dec.`) remain valid for backward compatibility. Arbitrary other spellings are not accepted.

The cash as-of date still comes only from the provider's `BARMITTELÜBERSICHT` / `Zum …` evidence. Creation timestamp validation, future-date rejection, Cashkonto arithmetic reconciliation, trust-account / money-market-fund reconciliation and bounded amount limits remain unchanged, and holdings/cash evidence remain independent.

The import error contract is also more precise. A missing or unsupported cash as-of date now produces the bounded reason `Statement cash as-of date is missing or unsupported`; two or more distinct supported as-of dates still produce `Statement contains an ambiguous cash as-of date`.

Rejected imports continue to preserve the last accepted private cash snapshot. No transaction rows, account identifiers, counterparties or uploaded PDF bytes are persisted.

## Compatibility and preserved contracts

The v1.62.2 explicit-choice first-run safety and Generic READY colour correction are unchanged. Config-entry schema 13 and the v1.62.1 integration-owned lifecycle remain unchanged. The v1.62.0 stable multi-profile Generic Import contract remains intact.

Comdirect and DKB acquisition behavior is unchanged. Generic Import behavior is unchanged from v1.62.2. Only the Trade Republic Gateway cash-statement parser changes at runtime; all four active Gateway App packages are version-aligned for release hygiene.

**Comdirect LEGACY remains removed from the active repository.** REST portfolio schema 1, payload schema 8, presentation schema 2, broker schemas 1/2/3, Gateway health schemas 1–10, discovery schemas 1/2, `fallback_policy: none`, evidence freshness, verified private-PKI HTTPS, bearer authentication, DNS pinning, LKG/anti-rollback/source-set atomicity and planner/funding semantics remain intact. **Authenticated DKB FinTS remains disabled** and research-only. There is **no silent fallback** between acquisition methods. No trading, order, transfer, payment, transaction-history, sell or withdrawal capability is introduced.

The v1.33.0 source-freshness and plan-schedule separation remains in force. This release does not alter any configured freshness threshold. Trade Republic provider-specific PDF parsing remains in its Gateway; this release does not move PDF parsing into Portfolio Architect. The historical `v1.19.0-rc2` brokerage-probe idea is not promoted. The v1.38.1 dynamic drift presentation remains part of the established presentation schema rather than an alternate calculation path.

No dashboard YAML replacement is required.

## Preserved historical release invariants

For regression clarity, v1.62.3 explicitly preserves these established contracts:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 10 is current; schemas 1–9 remain supported
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- recurring schedule anchoring continues to use the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold.
- Trade Republic provider-specific PDF parsing stays in its Gateway; this release changes only the bounded German cash-date month-label matrix and error classification.
- authenticated DKB FinTS acquisition remains disabled and research-only.
- No trading, order, transfer, payment, or transaction-history capability is introduced.
- Comdirect LEGACY remains removed from the active repository and the historical slug is not reused.
- Acquisition remains explicit with no silent fallback.
- The v1.38.1 dynamic drift presentation is included through the established presentation schema; it is not included as a separate alternate calculation path.
- The historical `v1.19.0-rc2` brokerage-probe idea is not promoted by this release.
