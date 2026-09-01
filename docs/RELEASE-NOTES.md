# Portfolio Architect v1.62.1 release notes

v1.62.1 completes the Generic Import graduation by making **Portfolio Architect integration-owned from the first click**. A Gateway can provide the first and only source, but it no longer creates the Portfolio Architect service or assumes that an expert has already authored YAML configuration.

## Integration-owned first run

A new user now initializes Portfolio Architect explicitly from Home Assistant **Add integration**. Portfolio Architect creates or validates its confined configuration directory and creates the singleton config entry in a fail-closed `source_required` state.

Initialization deliberately creates **no** source, allocation, investment policy, instrument metadata, broker/execution provider or transaction capability.

A source-less or plan-less config entry is a supported state. It loads without calculation entities or Gateway I/O until setup is completed; bounded diagnostics identify the setup state.

## Source adoption after initialization

Supervisor-discovered Gateways are acquisition candidates, not service owners.

A valid discovery received before PA exists is remembered transiently and tells the user to initialize PA first. After PA exists, **Configure → Portfolio sources** can adopt a discovered or manually entered first REST Gateway. The same verified-HTTPS, bearer, provider-identity, health and snapshot-integrity checks used by established source flows remain mandatory.

Existing complete YAML configuration becomes operational immediately after the first source validates. A newly initialized empty directory proceeds to `plan_required` instead.

## Native initial setup

The new **Complete initial setup** flow builds the first real configuration only from explicit user choices and source evidence.

The user selects source holdings with valid ISIN identity as plan targets, supplies target weights and relevant instrument facts, chooses plan parameters and policy controls, and reviews normalization where needed. Financial assumptions are not silently prefilled.

The four established YAML documents are generated in a private staging directory and the full engine candidate is calculated before anything is installed. The destination must still be empty; rejected/invalid setup cannot overwrite an existing configuration. Successful installation is atomic for ordinary failures and then reloads the integration into normal configured operation.

Broker schema 3 may now explicitly contain zero execution providers when there are no funding edges. This lets first-run setup remain advisory/fail-closed without inventing an execution venue.

## Compatibility

Config-entry schema 13 adds `source_required`, `plan_required` and `configured`. Existing entries migrate to `configured` without changing source or plan semantics.

The v1.62.0 stable multi-profile Generic Import contract is unchanged: legacy `generic_csv`, generated Generic identities, independent holdings/cash clocks, raw CSV privacy, health schema 10 and discovery schema 2 remain supported.

Comdirect, DKB and Trade Republic acquisition behavior is unchanged. **Comdirect LEGACY remains removed from the active repository.** REST portfolio schema 1, payload schema 8, health schemas 1–10, `fallback_policy: none`, evidence freshness, private-PKI/bearer/DNS-pinning, LKG/anti-rollback/source-set atomicity, planner/funding semantics remain intact. **Authenticated DKB FinTS remains disabled** and research-only. There is **no silent fallback** between acquisition methods. No trading, order, transfer, payment, transaction-history, sell or withdrawal capability is introduced.

## Preserved historical release invariants

For regression clarity, the following established contracts are explicitly preserved by v1.62.1:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 10 is current; schemas 1–9 remain supported
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- The v1.33.0 source-freshness and plan-schedule separation remains in force: recurring schedule anchoring uses the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold.
- Trade Republic provider-specific PDF parsing stays in its Gateway; this release does not move PDF parsing into Portfolio Architect.
- The historical `v1.19.0-rc2` brokerage-probe idea is not promoted by this release.
- Comdirect LEGACY was removed from the active repository in v1.57.0 and the historical slug is not reused.
- Acquisition remains explicit with no silent fallback.
- authenticated DKB FinTS acquisition remains disabled and research-only.
- No trading, order, transfer, payment, or transaction-history capability is introduced.
- The v1.38.1 dynamic drift presentation is included through the established presentation schema; it is not included as a separate alternate calculation path.

No dashboard YAML replacement is required.
