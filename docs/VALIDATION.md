# v1.40.1 validation

Portfolio Architect v1.40.1 is prepared from the exact published/live-accepted v1.40.0 tracked-source baseline. The release changes only Home Assistant Configure/editor compatibility and aligned package/version metadata; v1.40.0 evidence-backed funding semantics, provider acquisition, Gateway wire contracts, dashboard presentation and the advisory/no-execution boundary remain unchanged.

Validation requires:

- all integration/common Gateway/provider App current version markers align to 1.40.1 while historical release documentation remains historical;
- broker schemas 1/2 and legacy schema-3 edges remain compatible;
- evidence-backed schema-3 edges require `source` + `as_of` together, reject future dates and expose bounded provenance;
- evidence-backed edges become ineligible when older than `fee_data_max_age_days` while local same-provider funding remains available;
- reverse transferability is never inferred;
- native broker editing creates evidence-backed edges rather than provenance-free edges;
- no transfer/payment/order/write capability is introduced;
- the complete regression suite, structured-file parsing, Python compilation, publication/privacy gates, provider-App source parity, deterministic release build, release verification and release-artifact privacy checks pass;
- full overlay and binary-patch replay reproduce the final tracked tree from the exact v1.40.0 baseline including executable-bit semantics.

The preparation environment has no Docker command. Protected GitHub workflows remain authoritative for actual Docker build/smoke execution.
