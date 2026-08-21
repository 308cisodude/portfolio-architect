# v1.41.1 validation

Portfolio Architect v1.41.1 is prepared from the exact published v1.41.0 tracked-source baseline. The release changes only the funded-route tie-break, adds direct regression coverage, and performs normal package/version/documentation alignment. The v1.41.0 Trade Republic cash-statement acquisition implementation is unchanged.

Validation requires:

- all integration/common Gateway/provider App current-version markers align to 1.41.1 while historical release documentation remains historical;
- a synthetic zero-fee/zero-business-day Comdirect → Trade Republic edge plus sufficient local Trade Republic cash reproduces the v1.41.0 lexical tie and selects local Trade Republic cash under v1.41.1;
- cost ratio, settlement time, configured provider priority, executable order amount and combined fees remain ahead of the new local-cash preference;
- existing provider-scoped cash, exact directed funding topology and transfer-fee semantics remain unchanged;
- Trade Republic `DEPOTAUSZUG` holdings and `KONTOAUSZUG` cash import behavior remains unchanged from v1.41.0;
- no provider acquisition, schema, dashboard, trading, transfer execution, payment or other money-movement capability is added;
- the complete regression suite, structured-file parsing, Python compilation, publication/privacy gates, provider-App source parity, deterministic release builds, release verification and release-artifact privacy checks pass;
- full Git overlay and binary-patch replay reproduce the exact final tracked tree from the v1.41.0 baseline including executable-bit semantics.

The preparation environment has no Docker command. Protected GitHub workflows remain authoritative for actual Docker build/smoke execution.
