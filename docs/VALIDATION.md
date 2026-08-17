# v1.31.1 validation

Portfolio Architect v1.31.1 is an integration-side identity-validation hotfix based on
the exact immutable v1.31.0 source baseline.

Release-specific validation must prove:

- integration, engine, common Gateway and all three App versions align at `1.31.1`;
- a whole-portfolio holding with a non-empty ISIN and empty WKN is valid;
- an empty WKN does not enter duplicate-WKN detection;
- a holding with neither ISIN nor WKN fails closed;
- duplicate non-empty WKN and duplicate ISIN protections remain enforced;
- the exact live v1.31.0 topology is reproduced end to end: a Trade Republic-only
  `IE00BYWZ0333` holding with no WKN becomes outside current plan scope while
  accumulating `IE00BYZK4552` remains the active Robotics target;
- the resulting engine payload passes the complete Home Assistant model parser and
  reports six of seven targets held;
- the old distributing holding retains outside-scope identity and Trade Republic source
  provenance without generating an automatic sell action;
- the v1.31 superseded exception remains inactive and the v1.30 provider-aware execution
  semantics remain intact;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain unchanged;
- Comdirect acquisition/OAuth/session behavior, Trade Republic statement import and DKB
  FinTS capability-probe behavior remain unchanged;
- verified private-PKI HTTPS, bearer authentication, DNS pinning and no-plaintext fallback
  remain unchanged; and
- no trading, order placement, automatic sell, transfer, payment or transaction-history
  capability is added.

The complete local regression/release/privacy/reproducibility pipeline remains required.
Protected GitHub **Validate release** remains authoritative for actual provider-App
Docker/TLS smoke execution because Docker is unavailable in the preparation environment.

Live acceptance should start from the reproduced degraded v1.31.0 state when available.
Update the integration to 1.31.1 without restoring the old plan files or reimporting the
Trade Republic statement; successful recovery to the intended six-of-seven state is the
primary acceptance proof. Align the three Gateway Apps to 1.31.1 afterward.
