# Portfolio Architect Gateway — Trade Republic v1.38.0

Version 1.38.0 is package alignment for Portfolio Architect's Home Assistant-side dashboard usability polish. The v1.37 shared human-input helper remains present but unused by the Trade Republic statement-import path. Statement import/private diagnostics are unchanged and no cash or transaction-history acquisition is added.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 6 and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
