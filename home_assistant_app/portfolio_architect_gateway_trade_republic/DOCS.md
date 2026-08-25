# Portfolio Architect Gateway — Trade Republic v1.52.0

Version 1.52.0 graduates the Trade Republic App-level maturity marker to **stable** for its live-proven `DEPOTAUSZUG` holdings and `KONTOAUSZUG` cash PDF acquisition paths. Statement parsing, evidence clocks, private persistence, verified HTTPS and REST behavior are unchanged from v1.51.1.

Version 1.50.0 aligns the Trade Republic App package with Portfolio Architect’s source-management UX milestone. DEPOTAUSZUG/KONTOAUSZUG parsing, static persistence and the live/static Ingress distinction are unchanged from the live-accepted v1.49.0 baseline.

Version 1.48.1 aligns the Trade Republic App package with Portfolio Architect’s acquisition-aware freshness correction. DEPOTAUSZUG/KONTOAUSZUG parsing, static persistence and Ingress UX are unchanged from v1.48.0.

Version 1.48.0 keeps Trade Republic statement acquisition unchanged and makes the acquisition boundary visually explicit: the active static PDF statement path is separated from an explicitly unavailable live/private-API section.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 7 (with schemas 1–6 compatible) and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.