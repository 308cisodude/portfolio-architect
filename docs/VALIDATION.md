# v1.55.0 validation

Portfolio Architect v1.55.0 is prepared from the exact published and fully live-accepted v1.54.0 tracked-source baseline. It is a narrow Comdirect Home Assistant App-identity migration release; provider identity, acquisition semantics, freshness, wire schemas and planner behavior remain unchanged.

Release validation requires:

- all integration/common Gateway/all five App current-version markers align to 1.55.0 while historical release documentation remains historical;
- both Comdirect App packages coexist: historical slug `portfolio_architect_gateway` and provider-qualified slug `portfolio_architect_gateway_comdirect`, with the latter visibly labelled `Comdirect NEW`;
- the provider-qualified App starts non-discoverable on a pristine installation and exposes only the migration/setup shell plus internal migration/watchdog listeners;
- historical→successor hostname derivation is exact and does not accept a user-controlled URL;
- migration payloads are allowlisted, size-bounded, per-file SHA-256 validated and reject symlinks/unknown state/pending acquisition switches;
- `comdirect-session.json` is never exported and is absent before canonical cut-over;
- private CA SHA-256 and Gateway bearer token are preserved; only the TLS server leaf may be renewed for the new hostname;
- legacy freeze disables provider refresh/session maintenance while retaining cached REST serving and offers explicit restart-based recovery;
- provider-qualified discovery waits for health-schema-8 `ok` / `live` / snapshot-available state with provider `comdirect`;
- PA recognizes only the exact slug successor, refuses CA changes, requires explicit confirmation, reuses the existing bearer token and validates health/provider/snapshot count/timestamp/SHA before endpoint replacement;
- Gateway health schema 8 and REST portfolio schema 1 remain unchanged; schemas 1–7 stay accepted;
- v1.54 acquisition colours, static freshness authority, live-LKG scope and branch-current OpenSSL >=3.5.8 build policy remain intact across all five built Apps;
- provider-source synchronization is idempotent and the complete master Comdirect source is byte-identical in both Comdirect App build contexts;
- strict publication/privacy, release-artifact privacy and complete-history secret scanning pass;
- deterministic release builds are byte-identical;
- source/archive modes and both Git handoff replay paths reproduce the final tracked tree from exact v1.54.0.

The preparation environment does not provide Docker. Protected GitHub workflows remain authoritative for all five actual provider-App Docker builds, minimum-OpenSSL enforcement, pending Comdirect NEW migration-shell smoke, existing provider private-PKI smoke and complete-history/Gitleaks gates.
