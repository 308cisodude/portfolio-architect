# Portfolio Architect Gateway — Trade Republic v1.48.0

Version 1.48.0 keeps Trade Republic statement acquisition unchanged and makes the acquisition boundary visually explicit: the active static PDF statement path is separated from an explicitly unavailable live/private-API section.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 6 and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
