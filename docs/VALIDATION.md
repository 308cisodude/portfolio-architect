# v1.26.7 validation

Portfolio Architect v1.26.7 retains the complete v1.26.6 unavailable-source,
v1.26.5 date-domain presentation, v1.26 atomic-LKG, provider-App,
publication/privacy and reproducible-release regression pipeline.

The release-specific contracts must prove:

- integration and all three provider App package versions align with 1.26.7;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- optional schema-1 position `quantity` survives cached-snapshot parsing and
  persistence using canonical bounded decimal syntax;
- saving and reloading an unchanged quantity-bearing snapshot reproduces the exact
  same serialized bytes, SHA-256 and ETag;
- malformed, negative, exponent-form, non-string or non-finite cached quantity
  values fail closed;
- when `If-None-Match` is present and matches the current ETag, the Gateway may
  return `304 Not Modified` with consistent integrity metadata;
- when `If-None-Match` is present and does not match, `If-Modified-Since` cannot
  override it and the Gateway returns `200` with the current representation;
- `If-Modified-Since` remains supported when no ETag validator is present;
- common Gateway `models.py` and `server.py` fixes are synchronized into all three
  provider App build contexts;
- Portfolio Architect's existing fail-closed fingerprint/count/timestamp/health
  validation is unchanged;
- v1.26.6 non-live Gateway source identification remains green;
- v1.26.5 date-domain presentation and prior dashboard regressions remain green;
- Comdirect OAuth/session/PhotoTAN/account/cash behavior remains unchanged;
- Trade Republic statement parser/privacy contracts remain unchanged;
- the common REST API remains authenticated GET-only and no provider App gains
  trading/order/transfer/payment/transaction-history capability;
- source and built artifacts pass publication/privacy gates; and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

Live acceptance starts from the healthy v1.26.6 three-source / three-provider
installation. A short controlled Comdirect Gateway cold restart after a fresh live
refresh must not create a changed snapshot fingerprint, integrity Repair or false
`304` inconsistency. Normal live operation must recover automatically without
reauthentication or Portfolio Architect reconfiguration when the upstream session
has not expired.
