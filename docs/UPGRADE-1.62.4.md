# Upgrade to Portfolio Architect v1.62.4

v1.62.4 is a narrow Home Assistant integration hotfix on top of v1.62.3. It fixes the immediate first-run activation reload and removes blocking private-CA trust-store work from synchronous config/discovery normalization. Provider acquisition, wire schemas and planning semantics do not change.

## What changes

### First-run completion reload

A `source_required` / `plan_required` entry intentionally has no coordinator or forwarded PA platforms. In v1.62.3, the initial-plan wizard could successfully create and validate `portfolio.yaml`, `policy.yaml`, `instruments.yaml` and `broker.yaml`, mark the entry `configured`, then fail the immediate reload because unload inferred loaded platforms from the new setup-state rather than the actual runtime.

v1.62.4 unloads a runtime-less setup entry trivially. Normal configured entries with an actual coordinator/runtime still unload the established `sensor`, `binary_sensor` and `date` platforms normally.

### Event-loop-safe private CA handling

Synchronous REST/discovery normalization now performs only bounded PEM envelope/base64 validation. The actual X.509 private-CA trust load and hostname-verifying SSL-context construction stay in the existing executor-backed health/snapshot request path. Bad trust material remains fail-closed.

## Existing installations

Existing configured installations require no YAML migration, dashboard replacement, source reconfiguration, provider reauthentication or freshness change solely because of this release.

- config-entry schema 13 is unchanged;
- `source_required` / `plan_required` / `configured` semantics are unchanged;
- REST portfolio schema 1, payload schema 8 and health schema 10 are unchanged;
- Supervisor discovery schemas 1/2 are unchanged;
- broker schemas 1/2/3 are unchanged;
- `fallback_policy: none`, private-PKI HTTPS, bearer authentication, DNS pinning, LKG/anti-rollback/source-set atomicity and advisory-only boundaries are unchanged;
- v1.62.3 Trade Republic German cash-date compatibility is unchanged;
- authenticated DKB FinTS remains disabled/research-only.

All four active Gateway Apps are version-aligned to v1.62.4 for package hygiene, but the runtime behavioral fix is Home Assistant integration-only.

## Live acceptance — LG clean-room continuation

Do not reset the existing LG fixture.

1. Update the PA integration to v1.62.4 and restart Home Assistant once if required by HACS.
2. Align Generic Import to v1.62.4 without clearing its private state.
3. Confirm the already generated four YAML files and `generic_2ec6b19d4f74` source remain intact.
4. Re-enter/redo the final initial-plan completion only on a fixture still in `plan_required`; if the existing LG fixture is already `configured` after the recovery restart, retain it for normal configured-runtime checks and use a second clean setup cycle only if desired.
5. For a true transition test, confirm `plan_required` → `configured` completes without **Failed to unload**, without a Home Assistant restart, and normal PA entities appear immediately.
6. Confirm `broker.yaml` still contains no invented provider/funding topology when the user configured none.
7. Continue Generic independent cash-clock, rename/restart, atomic rejected-import and second-profile discovery tests.

## Live acceptance — HH established production

1. Update the PA integration directly from the current supported v1.61/v1.62 line to v1.62.4 and restart Home Assistant once.
2. Confirm schema-13 migration/established configuration loads directly as `configured`; no first-run flow appears and the existing YAML/source/broker topology is untouched.
3. Align Trade Republic to v1.62.4, then re-import the exact current `KONTOAUSZUG` that previously failed on the old `Sept.` parser; the v1.62.3 parser behavior is unchanged and should accept it.
4. Confirm the TR cash evidence timestamp advances independently while current holdings evidence remains unchanged.
5. Confirm all production sources are healthy/fresh under the existing thresholds and the plan is actionable with unchanged routing/economics apart from legitimately refreshed cash.
6. Align Comdirect and DKB to v1.62.4 for package-version hygiene; do not install unused Generic solely for alignment.

No dashboard replacement is required.
