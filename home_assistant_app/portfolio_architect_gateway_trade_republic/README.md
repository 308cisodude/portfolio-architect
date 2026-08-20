# Portfolio Architect Gateway — Trade Republic v1.37.0

Version 1.37.0 carries the shared human-numeric Gateway helper for future opt-in use, but the Trade Republic statement-import path does not use locale numeric normalization. Statement import/private diagnostics are unchanged and no cash or transaction-history acquisition is added.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 6 and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
