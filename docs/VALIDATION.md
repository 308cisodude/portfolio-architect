# v1.26.4 validation

Portfolio Architect v1.26.4 retains the complete v1.26.3 dashboard/policy,
v1.26.2 presentation/source-outage, v1.26.1 ISIN-first, v1.26 atomic-LKG,
provider-App, publication/privacy, and reproducible-release regression pipeline.

The release-specific contracts must prove:

- integration and all three provider App package versions align with 1.26.4;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- existing machine-readable entity IDs, states and availability semantics remain
  stable;
- every date-only reference-dashboard Tile for planned execution, next plan review,
  last exception decision, next exception review and oldest overdue exception
  review uses `state_content: state` plus native `time_format` type `date`, style
  `short`;
- the same generic date contract is present in English, German, composed, and
  standalone reference-dashboard variants;
- no locale-specific date display attribute, helper/template sensor, or hard-coded
  date pattern is added;
- the existing refresh-schedule timestamp Tiles remain on native `datetime` /
  `short` rendering and do not add seconds-specific formatting;
- the underlying schedule/policy date entities remain native
  `SensorDeviceClass.DATE` sensors returning `date` values;
- v1.26.3 German unavailable-state and policy-layout regressions remain green;
- v1.26.2 failed-source identification and translated attention reason/action remain
  unchanged;
- v1.26.1 ISIN-first identity/collision tests continue to pass unchanged;
- Trade Republic statement-parser privacy/integrity contracts remain unchanged;
- Comdirect authentication/account/cash behavior remains unchanged;
- the common REST API remains authenticated GET-only and no provider App gains
  trading/order/transfer/payment/transaction-history capability;
- source, history and built artifacts continue to pass publication/privacy gates;
  and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

Live acceptance starts from the established three-source/three-provider 7/7
v1.26.3 installation. After upgrade, the healthy state and accepted policy/outage
UX must remain unchanged. The date-only dashboard tiles must use the frontend's
normal localized short-date presentation rather than raw ISO dates. No seconds-
specific refresh-time formatting is introduced.
