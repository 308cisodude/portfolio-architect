# v1.41.0 validation

Portfolio Architect v1.41.0 is prepared from the exact published/live-accepted v1.40.1 tracked-source baseline. The release adds only bounded Trade Republic `KONTOAUSZUG` cash-statement acquisition plus the minimum provider-neutral REST/coordinator changes required to keep holdings and cash evidence independent. v1.40.1 Configure fixes, v1.40.0 evidence-backed funding semantics, v1.39 dashboard presentation, provider isolation, verified private-PKI transport, and the advisory/no-money-movement boundary remain intact.

Validation requires:

- all integration/common Gateway/provider App current-version markers align to 1.41.0 while historical release documentation remains historical;
- the existing Trade Republic `DEPOTAUSZUG` holdings importer remains independently fail-closed;
- the new `KONTOAUSZUG` parser accepts only bounded text PDFs, validates issuer/document-family markers, reconciles Cashkonto arithmetic, reconciles trust-account/QMMF custody totals, and rejects ambiguity or future/inconsistent evidence;
- raw PDFs, transaction rows, counterparties, account identifiers, names and addresses are never persisted;
- holdings and cash private state remain independent and are composed only through the existing additive REST schema-1 cash fields;
- cash timestamps may be independent of holdings timestamps without refreshing holdings evidence;
- provider cash is freshness-gated separately using the configured imported-statement threshold and stale cash is excluded from funding decisions without erasing otherwise valid holdings;
- no unofficial Trade Republic API, credentials, transaction-history model, transfer/payment/order/write capability is introduced;
- the complete 640-test regression suite, structured-file parsing, Python compilation, publication/privacy gates, provider-App source parity, deterministic release builds, release verification and release-artifact privacy checks pass;
- full Git overlay and binary-patch replay reproduce the exact final tracked tree from the v1.40.1 baseline including executable-bit semantics.

The preparation environment has no Docker command. Protected GitHub workflows remain authoritative for actual Docker build/smoke execution.
