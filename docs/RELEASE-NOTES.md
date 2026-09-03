# Portfolio Architect v1.62.2 release notes

v1.62.2 is a narrow first-run safety and presentation follow-up to v1.62.1. Live clean-room acceptance proved the new integration-owned lifecycle, but also exposed that Home Assistant's frontend may render usable selector minima or first options for required selector fields even when Portfolio Architect supplied no suggested value. v1.62.2 makes the native initial-plan wizard robust against that frontend behavior so no UI artifact can become an investment choice.

## Explicit first-run choices

Every field in **Complete initial setup** now starts without an investment choice at the schema/UI boundary and is enforced as mandatory only when the form is submitted.

- target instruments start with none selected;
- contribution, corridor, minimum purchase, rounding step, target weight, TER, fund size and policy thresholds start blank;
- distribution policy starts unselected;
- investment/policy booleans use an explicit unanswered **Yes / No** selector rather than a checkbox whose unchecked state could be mistaken for a deliberate `false` choice;
- target-weight normalization likewise requires an explicit Yes/No decision;
- omitted or blank fields are rejected with field-level validation before any configuration document is built or written.

The backend still validates the complete candidate through the established engine before atomically installing the four YAML documents. No source, allocation, policy, instrument fact, execution provider or funding edge is invented.

## Generic Import READY presentation

The Generic Import source-profile card now follows the established acquisition-state colour contract:

- **SETUP REQUIRED** profile: amber;
- **READY** profile: blue (ready for Portfolio Architect consumption);
- the profile's active/authoritative CSV acquisition method remains green.

This is presentation-only. Generic profile identity, discovery, holdings/cash evidence, mapping, persistence and provider transport are unchanged.

## Compatibility and preserved contracts

Config-entry schema 13 and the v1.62.1 integration-owned lifecycle are unchanged. A source-less or plan-less Portfolio Architect entry remains a supported fail-closed setup state; Gateway discovery never creates the singleton service.

The v1.62.0 stable multi-profile Generic Import contract remains intact: legacy `generic_csv`, generated `generic_<stable-id>` identities, up to eight profiles, independent holdings/cash evidence clocks, raw CSV privacy, provider-specific REST paths, health schema 10 and discovery schema 2 remain supported.

Comdirect, DKB and Trade Republic acquisition behavior is unchanged. **Comdirect LEGACY remains removed from the active repository.** REST portfolio schema 1, payload schema 8, presentation schema 2, broker schemas 1/2/3, health schemas 1–10, `fallback_policy: none`, evidence freshness, verified private-PKI HTTPS, bearer authentication, DNS pinning, LKG/anti-rollback/source-set atomicity and planner/funding semantics remain intact. **Authenticated DKB FinTS remains disabled** and research-only. There is **no silent fallback** between acquisition methods. No trading, order, transfer, payment, transaction-history, sell or withdrawal capability is introduced.

The v1.33.0 source-freshness and plan-schedule separation remains in force. This release does not alter any configured freshness threshold. Trade Republic provider-specific PDF parsing remains in its Gateway. The historical `v1.19.0-rc2` brokerage-probe idea is not promoted. The v1.38.1 dynamic drift presentation remains part of the established presentation schema rather than an alternate calculation path.

No dashboard YAML replacement is required.

## Preserved historical release invariants

For regression clarity, v1.62.2 explicitly preserves these established contracts:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 10 is current; schemas 1–9 remain supported
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- recurring schedule anchoring continues to use the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold.
- Trade Republic provider-specific PDF parsing stays in its Gateway; this release does not move PDF parsing into Portfolio Architect.
- authenticated DKB FinTS acquisition remains disabled and research-only.
- No trading, order, transfer, payment, or transaction-history capability is introduced.
- Comdirect LEGACY remains removed from the active repository and the historical slug is not reused.
- Acquisition remains explicit with no silent fallback.
- The v1.38.1 dynamic drift presentation is included through the established presentation schema; it is not included as a separate alternate calculation path.
- The historical `v1.19.0-rc2` brokerage-probe idea is not promoted by this release.
