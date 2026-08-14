# v1.26.6 validation

Portfolio Architect v1.26.6 retains the complete v1.26.5 date-domain presentation,
v1.26.3/v1.26.2 dashboard/source-outage, v1.26.1 ISIN-first, v1.26 atomic-LKG,
provider-App, publication/privacy, and reproducible-release regression pipeline.

The release-specific contracts must prove:

- integration and all three provider App package versions align with 1.26.6;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- a reachable primary REST Gateway whose operating mode is
  `reauthentication_required` is included in `unavailable_source_ids` even when
  Portfolio Architect is not using its separate Home Assistant LKG;
- the corresponding English/German bounded summaries render `Comdirect Gateway` /
  `Comdirect-Gateway`, never `None` / `Keine` while that source is non-live;
- Gateway-local `last_known_good` and primary health-unavailable states are covered
  by the same non-live source-identification rule;
- an additional REST Gateway whose health is observed but non-live is likewise
  included in the bounded unavailable-source set;
- existing supplemental Gateway error collection and DKB CSV source diagnostics
  remain present and deduplicated;
- healthy/live REST Gateways are not reported as unavailable;
- no endpoint, bearer token, account/depot/customer identifier, configured path, or
  provider-private state enters unavailable-source IDs or summaries;
- v1.26.5 authoritative DATE sensors and read-only native `date.*` presentation
  counterparts remain unchanged;
- v1.26.3 German unavailable-state and policy-layout regressions remain green;
- v1.26.1 ISIN-first identity/collision tests continue to pass unchanged;
- Trade Republic statement-parser privacy/integrity contracts remain unchanged;
- Comdirect OAuth/session/account/cash behavior remains unchanged;
- the common REST API remains authenticated GET-only and no provider App gains
  trading/order/transfer/payment/transaction-history capability;
- source and built artifacts continue to pass publication/privacy gates; and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

Live acceptance starts from the established healthy v1.26.5 three-source /
three-provider 7/7 installation. After upgrading, normal healthy operation must be
unchanged. When Comdirect requires reauthentication while its Gateway remains
reachable and serves its trusted cached snapshot, Portfolio Architect must remain
degraded/non-actionable and **Source unavailable** must identify **Comdirect
Gateway** rather than displaying `None`. After reauthentication, the source summary
must disappear again when all configured Gateways return to live operation.
