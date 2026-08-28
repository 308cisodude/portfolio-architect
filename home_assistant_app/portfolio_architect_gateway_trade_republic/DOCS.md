# Portfolio Architect Gateway — Trade Republic v1.55.0

Version 1.55.0 fixes the live-observed conflict between the historical Gateway cache-age setting and Portfolio Architect's longer imported-statement freshness policy. Accepted Trade Republic PDF evidence remains servable with its original timestamp; Portfolio Architect alone decides whether that evidence is fresh enough to use. Parsing and provider identity are unchanged.

Version 1.53.0 adds provider-neutral health-schema-8 acquisition control metadata. Trade Republic reports `pdf` as the active/ready production method and `live_api` as unavailable/non-activatable. Statement parsing, independent evidence clocks, private persistence and verified HTTPS are unchanged.

Version 1.50.0 aligns the Trade Republic App package with Portfolio Architect’s source-management UX milestone. DEPOTAUSZUG/KONTOAUSZUG parsing, static persistence and the live/static Ingress distinction are unchanged from the live-accepted v1.49.0 baseline.

Version 1.48.1 aligns the Trade Republic App package with Portfolio Architect’s acquisition-aware freshness correction. DEPOTAUSZUG/KONTOAUSZUG parsing, static persistence and Ingress UX are unchanged from v1.48.0.

Version 1.48.0 keeps Trade Republic statement acquisition unchanged and makes the acquisition boundary visually explicit: the active static PDF statement path is separated from an explicitly unavailable live/private-API section.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 8 (with schemas 1–7 compatible) and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
