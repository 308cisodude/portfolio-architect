# Portfolio Architect Gateway — Trade Republic v1.48.2

Version 1.48.2 aligns the Trade Republic App package with Portfolio Architect’s Home Assistant-side source-summary propagation hotfix. Provider acquisition/runtime behavior is unchanged from v1.48.1 and no re-import or reauthentication is required solely for this package alignment.

Version 1.48.1 aligns the Trade Republic App package with Portfolio Architect’s acquisition-aware freshness correction. DEPOTAUSZUG/KONTOAUSZUG parsing, static persistence and Ingress UX are unchanged from v1.48.0.

Version 1.48.0 keeps Trade Republic statement acquisition unchanged and makes the acquisition boundary visually explicit: the active static PDF statement path is separated from an explicitly unavailable live/private-API section.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 7 (with schemas 1–6 compatible) and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
