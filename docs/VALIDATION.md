# v1.26.5 validation

Portfolio Architect v1.26.5 retains the complete v1.26.4, v1.26.3 dashboard/policy,
v1.26.2 presentation/source-outage, v1.26.1 ISIN-first, v1.26 atomic-LKG,
provider-App, publication/privacy, and reproducible-release regression pipeline.

The release-specific contracts must prove:

- integration and all three provider App package versions align with 1.26.5;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- the five established `SensorDeviceClass.DATE` sensors remain present, native
  `date`-valued, and authoritative;
- the integration forwards the Home Assistant `date` platform and creates exactly
  five additive presentation counterparts with distinct unique IDs;
- each presentation counterpart returns a native Python `date` value without a
  fabricated timestamp, timezone conversion, or locale-specific string;
- every write through `date.set_value` is rejected fail-closed;
- all 45 date-only reference-dashboard Tile occurrences use the corresponding
  `date.portfolio_architect_*` entity and no longer carry the ineffective v1.26.4
  date-only `state_content`/`time_format` override;
- each presentation-date Tile routes `more-info` to its authoritative sensor so
  Home Assistant's editable date-domain control is not exposed by the reference
  dashboard;
- no state/availability condition uses a presentation `date.*` entity;
- no reference-dashboard Tile renders an authoritative DATE sensor directly;
- English/German date-platform translations and icons exist for all five
  counterparts;
- refresh-schedule timestamp Tiles remain on native `datetime` / `short` rendering
  and do not add seconds-specific formatting;
- v1.26.3 German unavailable-state and policy-layout regressions remain green;
- v1.26.2 failed-source identification and translated attention reason/action remain
  unchanged;
- v1.26.1 ISIN-first identity/collision tests continue to pass unchanged;
- Trade Republic statement-parser privacy/integrity contracts remain unchanged;
- Comdirect authentication/account/cash behavior remains unchanged;
- the common REST API remains authenticated GET-only and no provider App gains
  trading/order/transfer/payment/transaction-history capability;
- source and built artifacts continue to pass publication/privacy gates; and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

Live acceptance starts from the established healthy v1.26.4 three-source /
three-provider 7/7 installation. After the integration and reference dashboard are
updated, the underlying DATE sensors must still expose their ISO machine states in
Developer Tools, while the visible date Tiles must use Home Assistant's normal
localized date presentation. Refresh-schedule timestamps must remain unchanged.
