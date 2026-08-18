# v1.34.0 validation

Portfolio Architect v1.34.0 is prepared from the exact live-accepted v1.33.1 tracked-source baseline.

The release must prove:

- integration, engine, common Gateway and all three official App versions align at `1.34.0`;
- schema 1 legacy target IDs remain accepted;
- schema 2 requires an explicit opaque `target_` + 32-hex target ID representing 128 random bits;
- the PA generator creates fresh target IDs without ISIN/WKN/name/order input;
- the native plan editor keys candidate selection by ISIN and never derives target identity from WKN;
- deleting a target from the active plan does not preserve/resurrect its identity through a later matching ISIN;
- target count is generic and bounded to 32 rather than fixed at seven;
- an existing target ID survives reorder, rename, weight/policy change and deliberate instrument replacement for the same current role;
- the reference schema-2 plan uses seven opaque target IDs and preserves the same allocation/instrument semantics;
- payload schema 8 remains unchanged while `target_id` / `plan_target_id` aliases match compatibility `fund_id` / `plan_fund_id`;
- presentation schema 1 exposes every current configured target, current-plan holding and currently evidenced outside-scope holding;
- no target tombstone/history registry or outside-scope history registry is introduced;
- outside-scope inventory is derived only from accepted current portfolio data;
- reference dashboards remain native-only and are aligned to the migrated opaque reference IDs;
- v1.33 evidence-kind freshness and v1.33.1 evaluation-anchored scheduling remain unchanged;
- Comdirect, Trade Republic and DKB runtime/diagnostic behavior remains unchanged apart from normal package/User-Agent alignment;
- DKB stays experimental/manual-only/non-live and authenticated user-capability/UPD remains a later gate; and
- no trading, order placement, automatic sell, transfer, payment or transaction-history capability is introduced.

Run the complete regression suite, `git diff --check`, Python compilation, structured-file parsing,
strict publication/privacy checks, three independent reproducible release builds, release
verification, release-artifact privacy validation and independent Git-overlay/binary-patch replay
over the exact v1.33.1 tracked baseline.

Protected GitHub workflows remain authoritative for actual provider-App Docker/private-PKI smoke
execution because Docker is unavailable in the preparation environment.

## Live acceptance

1. Upgrade Portfolio Architect to 1.34.0 and restart without changing the existing live schema-1 `portfolio.yaml`.
2. Confirm the legacy plan remains healthy with the same 6/7 target coverage, source freshness, 7-Sep/5-Oct schedule, provider aggregation and existing target entities.
3. Upgrade all three Gateway Apps in place; do not reauthenticate Comdirect, re-import Trade Republic or re-probe DKB solely for this release.
4. Back up `portfolio.yaml`, then deliberately install the supplied schema-2 current-plan migration and matching reference dashboard together.
5. Re-evaluate and confirm the same 6/7 economic/strategy state, the expected one-time opaque target-entity identity migration, no automatic sell, and unchanged freshness/schedule behavior.
6. Inspect the presentation-model entity: seven configured target IDs, six held current-plan roles, and the complete live outside-scope inventory should reconcile with the whole-portfolio model.
7. Confirm an outside-scope holding disappears only after accepted source evidence no longer reports it; do not infer absence from a failed or stale source.
