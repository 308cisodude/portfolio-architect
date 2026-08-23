# Portfolio Architect Gateway — Trade Republic v1.46.0

Version 1.46.0 is package alignment for the Home Assistant-side DKB bridge-retirement release. The temporary DKB migration-only endpoint is removed from the common runtime. Trade Republic holdings/cash statement acquisition and verified-HTTPS snapshot serving are unchanged.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 6 and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
