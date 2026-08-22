# v1.43.0 validation

Portfolio Architect v1.43.0 is prepared from the exact published/live-accepted v1.42.0 tracked-source baseline. The release adds Home Assistant-side route-level savings-plan evidence/freshness, enhanced native route editing, native exact funding-edge editing, regression coverage, and normal package/version/documentation alignment. Provider acquisition and the v1.42 dashboard remain unchanged.

Release validation requires:

- all integration/common Gateway/provider App current-version markers align to 1.43.0 while historical release documentation remains historical;
- broker schemas 1/2/3 remain accepted and legacy provider-level route-evidence fallback stays compatible;
- explicit route evidence is pairwise, bounded, future-safe and independently freshness-gated by `fee_data_max_age_days`;
- stale route evidence cannot be refreshed by a provider-level date, and fresh explicit route evidence is not suppressed merely because provider-level fallback/manual-order evidence is stale;
- native savings-plan route Add/Edit uses Home Assistant DateSelector controls and writes explicit route evidence;
- native funding-transfer Edit preserves exact directed edge identity while allowing only fee, conservative settlement days, source and date to change;
- provider-scoped cash, v1.41.1 local-cash routing, v1.42 execution-path presentation, wire/security schemas and advisory-only semantics remain unchanged;
- complete regression tests, Python compilation, structured-file parsing and `git diff --check` pass;
- source/release privacy, publication readiness, provider-App source parity, deterministic release builds, and exact Git overlay/binary-patch replay all pass.

Protected GitHub workflows remain authoritative for actual Docker provider-App build/smoke execution when Docker is unavailable in the preparation environment.
