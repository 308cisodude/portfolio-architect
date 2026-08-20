# v1.38.1 validation

Portfolio Architect v1.38.1 is prepared from the exact published v1.38.0 tracked-source baseline. The release is a Home Assistant-native presentation follow-up: it restores dynamic signed allocation-drift visualization for the existing bounded target presentation slots while preserving the v1.38.0 cash context and copy-friendly ISIN interaction. Provider runtime, portfolio mathematics and Gateway wire/security contracts are unchanged.

## Required evidence

Release-specific validation must prove:

- all integration/common Gateway/provider App current version markers align to 1.38.1 while historical release documentation remains historical;
- the allocation-drift surface consumes exactly the existing 32 generic target presentation slots and does not hard-code target IDs, ISIN-derived holding IDs or sample instruments;
- each slot has native Conditional variants for `underweight`, `on_target` and `overweight`, mapped respectively to amber, green and red Tile presentation;
- every drift Tile uses the slot's dynamic entity name and the native `bar-gauge` feature with `min: -100` and `max: 100`;
- tapping a visible drift Tile opens the matching slot's bounded allocation-explanation entity;
- unused/unavailable slots remain suppressed by their state conditions;
- the v1.38.0 recommended-purchase tap-to-ISIN and hold-to-explanation interaction remains present;
- the v1.38.0 policy-aware authorized/remaining-cash context remains present in both locale views;
- presentation schema 2, payload schema 8, REST portfolio schema 1, Gateway health schema 6 and broker schemas 1/2/3 remain unchanged;
- no custom frontend dependency, provider acquisition change, execution capability, transfer capability or transaction-history ingestion is introduced;
- common Gateway/App source copies remain synchronized;
- the complete test suite, Python compilation, structured-file parsing, publication-readiness, repository privacy, deterministic release builds, release verification and release-artifact privacy checks pass;
- the full Git overlay and binary patch independently replay to the final tracked tree from the exact published v1.38.0 baseline.

The protected GitHub workflows remain authoritative for Docker smoke execution when a local Docker daemon is unavailable.
