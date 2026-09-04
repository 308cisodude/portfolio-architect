# v1.62.5 validation

The v1.62.5 release-preparation contract starts from the exact published v1.62.4 source and validates the live-observed optional-exceptions coordinator metadata fix without changing provider acquisition, wire schemas, first-run financial-choice semantics, private-PKI behavior, freshness or planner behavior.

Required gates include:

- all integration/Gateway/App package versions aligned to v1.62.5;
- the four established required configuration files remain mandatory in coordinator metadata;
- absent optional `exceptions.yaml` is accepted by coordinator modification/fingerprint/LKG metadata;
- present `exceptions.yaml` participates in the deterministic configuration fingerprint;
- removing `exceptions.yaml` returns to the four-file fingerprint;
- a missing required configuration file still fails closed;
- the first-run four-document directory shape is directly eligible for coordinator metadata without a dummy exceptions file;
- v1.62.4 runtime-aware unload and event-loop-safe private-CA normalization remain covered;
- v1.62.3 Trade Republic German month parsing remains covered;
- complete regression suite, Python compilation, structured JSON/YAML parsing, whitespace/diff, strict publication/privacy, provider-source synchronization and OpenSSL security-floor checks pass;
- three independent release builds are byte-identical and pass release verification/artifact privacy;
- source release, Git overlay and binary patch independently reproduce the exact final tree/modes from the published v1.62.4 baseline.
