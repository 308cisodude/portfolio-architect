# v1.35.2 validation

Portfolio Architect v1.35.2 is prepared from the exact published and live-accepted v1.35.1 tracked
source baseline. Validation must prove the new configuration/cash-policy surface without weakening
the established funding, transport, provider-isolation or publication boundaries.

Required evidence:

- all integration/common Gateway/provider App version markers align at `1.35.2`;
- broker schemas 1/2/3 retain established runtime behavior;
- the native broker editor accepts only schema 2/3, validates the complete document before save and
  performs an atomic same-file replacement;
- native editing preserves an existing advanced numeric priority when its preference tier is not changed;
- adding a funding relationship creates only the exact directed edge and schema-2-to-3 opt-in;
- `promotional` is boolean when present and cannot make a higher-cost route beat a cheaper route;
- route economics remain cost first, settlement time second and optional priority only a later tie-break;
- retained-cash authorization implements `max(eligible - retain, 0)` including the retain-above-eligible case;
- all three cash policies satisfy `0 <= authorized <= eligible`;
- private schema-1 cash-policy state remains readable and schema-2 retained state round-trips;
- Gateway/cache/REST/Home Assistant model validation rejects inconsistent cap/retain combinations;
- existing v1.35.1 Comdirect session-maintenance resilience regressions remain green;
- v1.35.0 provider-scoped funding, exact directed topology and DKB probe-fingerprint regressions remain green;
- Python compilation, tracked JSON/YAML parsing, `git diff --check`, publication-readiness and privacy checks pass;
- all tests pass;
- three independent release builds are byte-identical;
- release verification and release-artifact privacy checks pass for every build;
- overlay and binary patch independently reproduce the final tracked tree from the exact v1.35.1 baseline.

Local Docker availability is environment-dependent. Protected GitHub **Validate release** remains
authoritative for actual provider-App Docker/private-PKI smoke execution when Docker is unavailable
in the preparation environment.

## Live acceptance

Start from healthy/live v1.35.1 with the already accepted schema-3 funding configuration. Upgrade in
place without reauthentication or source recreation. Confirm current execution recommendations and
funding plans remain unchanged, inspect the new native execution-provider/funding editor, and exercise
the retained-cash policy only with a deliberately chosen amount. No real trade or transfer is required
for acceptance.
