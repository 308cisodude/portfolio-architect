# Portfolio Architect 1.40.1

Portfolio Architect v1.40.1 hardens the native Home Assistant **Configure** experience after live v1.40.0 testing exposed two form-level UX defects: the savings-plan route form could not be constructed by Home Assistant Core 2026.8.1 because its percentage selector requested a step below Home Assistant's supported minimum, and free-text evidence dates failed closed without useful browser guidance when entered in a locale-style format.

## Configure-menu compatibility audit

The complete `PortfolioArchitectOptionsFlow` surface was audited against Home Assistant Core 2026.8.1 selector contracts rather than patching only the one field that failed live.

The audit covers every native selector configuration used by Configure, including Number, Select, Text, Boolean and Date selectors. Regression coverage now also derives every rendered options-flow step and requires bilingual translation coverage, and checks that literal menu destinations resolve to implemented flow methods.

The live failure was isolated to the savings-plan fee selector:

- v1.40.0 requested `step=0.0001`;
- Home Assistant Core 2026.8.1 requires numeric `NumberSelector` steps of at least `0.001`;
- v1.40.1 uses `0.001`, the finest supported value.

Home Assistant does not round typed box input to the selector step, so this is a compatibility correction rather than a reduction in practical broker-fee precision.

No other invalid selector configuration was found in the audited Configure surface.

## Native evidence dates

Broker provider evidence dates and funding-transfer evidence dates now use Home Assistant's native `DateSelector` instead of free-text fields.

New evidence forms preselect the current Home Assistant-local date. Existing provider evidence dates remain preselected when editing. The editor also propagates that Home Assistant-local date through broker-document validation and atomic write validation so a local date selected shortly after local midnight is not incorrectly compared against a host-UTC previous day.

The stored broker format remains ISO `YYYY-MM-DD`; only the input control changes.

## Bounded duplicate feedback

The native broker editor now gives specific field-level errors when an operator tries to add:

- an execution provider ID that already exists;
- a savings-plan route that already exists for the same provider/ISIN; or
- a directed funding transfer that already exists for the same source/destination pair.

Other invalid or unsafe broker changes continue to fail closed behind the bounded generic broker-configuration error.

## Preserved contracts

v1.40.1 changes only Home Assistant configuration-flow/editor behavior plus aligned version/package metadata.

- v1.40.0 evidence-backed funding-transfer semantics are unchanged;
- cost-first route selection and provider-scoped cash ownership are unchanged;
- payload schema 8, REST portfolio schema 1, Gateway health schema 6 and presentation schema 2 are unchanged;
- broker schemas 1/2/3 are unchanged;
- Comdirect, DKB and Trade Republic provider acquisition/runtime behavior is unchanged;
- verified private-PKI HTTPS, bearer authentication and fail-closed provider isolation are unchanged;
- the v1.39.0 colourful allocation dashboard and v1.38.1 signed drift presentation are unchanged;
- no Trade Republic private API or unsupported provider access is introduced;
- no trading, order, transfer, payment or transaction-history capability is added.

No dashboard YAML migration is required for v1.40.1.

## Historical compatibility preservation

Historical experimental `v1.19.0-rc2` brokerage-diagnostic work remains excluded and is not promoted by this release.

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported;
- presentation schema 2: unchanged;
- broker schemas 1/2/3: unchanged;
- Trade Republic local/private statement import is unchanged; this release does not move PDF parsing into Portfolio Architect;
- DKB remains experimental, manual-only and non-live; DKB live Gateway acquisition remains a later authenticated milestone.

The colourful paired current/target Tile view was not included in v1.38.1; it arrived in v1.39.0 and remains unchanged here. The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, source timestamps remain evidence-only freshness inputs, and v1.40.1 does not change any configured freshness threshold.

No trading, order, transfer, payment, or transaction-history capability is introduced by v1.40.1.
