# v1.35.0 validation

Portfolio Architect v1.35.0 is prepared from the exact v1.34.1 tracked-source baseline and adds
provider-scoped cash/funding topology plus two narrow presentation/diagnostic corrections.

## Required automated evidence

- integration, engine, common Gateway and all three official App versions align at `1.35.0`;
- complete Python regression suite passes;
- v1.35 funding regressions prove explicit directed transfer edges, no reverse-edge inference,
  provider-local cash isolation, transfer-fee route economics, settlement-delay tie-breaking,
  provider cash debiting and advisory transfer-plan payload validation;
- broker schemas 1 and 2 retain their established behavior;
- DKB regressions prove the exact bounded HTTP response body is SHA-256 fingerprinted before decode,
  only digest/length persist, schema-1/schema-2 probe state remains readable, and live DKB
  acquisition remains disabled;
- reference-dashboard regressions prove the accumulating/distributing Robotics labels remain
  visually distinct in English and German;
- Python compilation, JSON/YAML parsing, `git diff --check`, strict publication readiness, source
  privacy, release verification and release-artifact privacy pass;
- repeated release builds are byte-identical; and
- the Git overlay and binary patch independently reproduce the final tracked tree from the exact
  v1.34.1 baseline, including executable-bit semantics.

## Live acceptance

1. Update Portfolio Architect to 1.35.0 and restart Home Assistant.
2. Confirm existing Comdirect and Trade Republic sources remain healthy on verified HTTPS and the
   existing target/presentation model is unchanged apart from the Robotics label.
3. Without changing `broker.yaml`, confirm schema-2 execution behavior is unchanged.
4. When ready to exercise v1.35 funding topology, migrate `broker.yaml` explicitly to schema 3 with
   reviewed transfer cost/business-day evidence, then confirm provider-scoped cash and the advisory
   funding route match that configuration.
5. Update all three Gateway Apps to 1.35.0 in place and verify their established provider-specific
   behavior remains unchanged.
6. A future DKB probe may be used to verify the new raw response-body digest/byte-count evidence;
   no additional probe is required merely to accept the release.

Local Docker availability is environment-dependent; protected GitHub workflows remain authoritative
for actual provider-App Docker build/smoke execution when local Docker is unavailable.
