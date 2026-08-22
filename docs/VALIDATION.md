# v1.44.0 validation

Portfolio Architect v1.44.0 is prepared from the exact published/live-accepted v1.43.0 tracked-source baseline. The release is a Home Assistant Configure UX consistency pass: selected-object edit forms gain immutable identity context, every Configure menu receives structural bilingual label coverage, and normal package/version/documentation alignment is applied. Planner/provider runtime and dashboard behavior remain unchanged.

Release validation requires:

- all integration/common Gateway/provider App current-version markers align to 1.44.0 while historical release documentation remains historical;
- the exact v1.43.0 normalized tracked-source fingerprint is used as the preparation baseline;
- every native Configure menu target has a non-empty English and German menu label and translated target-step title;
- menu translation ordering matches emitted Configure menu ordering, including the funding-topology edit action;
- every `async_step_edit_*_details` selected-object editor exposes explicit description placeholders for immutable identity context;
- English and German editor descriptions consume every required identity placeholder above the editable fields;
- execution-provider context includes provider display name + provider ID;
- savings-plan-route context includes provider display name + provider ID + ISIN;
- funding-transfer context includes exact directed source/destination provider names + IDs;
- the plan-instrument editor retains its existing instrument name/ISIN/target-ID context;
- v1.43 route-level evidence/fallback/freshness behavior, v1.41.1 local-cash routing, v1.42 execution-path presentation, provider acquisition, wire/security schemas and advisory-only semantics remain unchanged;
- complete regression tests, Python compilation, structured-file parsing and `git diff --check` pass;
- source/release privacy, publication readiness, provider-App source parity, deterministic release builds, and exact Git overlay/binary-patch replay all pass.

Protected GitHub workflows remain authoritative for actual Docker provider-App build/smoke execution when Docker is unavailable in the preparation environment.
