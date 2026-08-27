# v1.54.0 validation

Portfolio Architect v1.54.0 is prepared from the exact published and fully live-accepted v1.53.1 tracked-source baseline. It is a Gateway acquisition-presentation and release-engineering policy cleanup; provider acquisition and Portfolio Architect planning semantics remain unchanged.

Release validation requires:

- all integration/common Gateway/all four App current-version markers align to 1.54.0 while historical release documentation remains historical;
- Gateway health schema 8 and REST portfolio schema 1 remain unchanged; schemas 1-7 stay accepted;
- authoritative acquisition cards are green across Comdirect, Trade Republic, DKB and Generic Import; inactive-ready is blue; unavailable/not-ready/research-only acquisition is amber;
- static-only DKB/TR/Generic App configuration no longer exposes `max_cached_snapshot_age_seconds`, while the bounded compatibility parser continues to tolerate stale stored legacy state;
- Comdirect retains the bounded option under the explicit `Maximum live LKG snapshot age` presentation and the Ingress Live API section states that Portfolio Architect owns planning freshness;
- no provider Dockerfile exact-pins an Alpine OpenSSL APK revision; protected validate/release workflows enforce OpenSSL >= 3.5.8 on every built App image and record the resolved version;
- Python/Alpine base images remain digest-pinned, GitHub Actions remain commit-SHA pinned, and Python requirements remain hash-locked;
- provider-source synchronization remains idempotent;
- strict publication and privacy checks pass;
- three release builds are byte-identical;
- source/archive modes and both Git handoff replay paths reproduce the final tracked tree from exact v1.53.1.

The preparation environment does not provide Docker. Protected GitHub workflows remain authoritative for actual provider-App Docker build, minimum-OpenSSL enforcement and verified-private-PKI smoke execution.
