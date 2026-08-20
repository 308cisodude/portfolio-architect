# v1.39.0 validation

Portfolio Architect v1.39.0 is prepared from the exact live-accepted v1.38.1 tracked-source baseline. The release changes only Home Assistant native-dashboard presentation plus aligned package/version metadata: paired dynamic colourful current/target allocation Tiles are added while the v1.38.1 drift implementation and all provider/runtime contracts remain unchanged.

Validation requires that:

- all integration/common Gateway/provider App current version markers align to 1.39.0 while historical release documentation remains historical;
- each English/German view exposes exactly 32 paired current/target bounded slot candidates through native Conditional + Tile cards;
- both members of each slot pair use the same deterministic slot colour and native 0–100% `bar-gauge`;
- current-allocation Tile visibility is keyed to positive target allocation so a configured-but-missing target remains visible at 0% current allocation;
- the v1.38.1 three-variant signed drift presentation remains unchanged at 32 slots × underweight/on-target/overweight, with amber/green/red semantics and -100…+100 pp gauges;
- the dashboard contains no hard-coded target hashes, holdings, ISIN inventory, sample instrument names, custom cards, JavaScript, card-mod or auto-entities;
- v1.38.0 cash-context and copy-friendly ISIN interactions remain covered by regression tests;
- payload schema 8, REST portfolio schema 1, Gateway health schema 6, presentation schema 2 and broker schemas 1/2/3 remain unchanged;
- private-PKI HTTPS, bearer authentication, provider isolation and advisory/no-trading boundaries remain unchanged;
- strict publication, repository privacy, provider-App source parity, deterministic release-build, release-verification and replay checks pass before handoff.

Protected GitHub workflows remain authoritative for actual Docker build/smoke execution when Docker is unavailable in the preparation environment.
