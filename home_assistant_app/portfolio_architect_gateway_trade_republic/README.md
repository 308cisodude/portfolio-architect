# Portfolio Architect Gateway — Trade Republic v1.45.0

Version 1.45.0 is package alignment for the DKB Gateway CSV acquisition release. The strict local `DEPOTAUSZUG` holdings and `KONTOAUSZUG` cash-statement imports are unchanged.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 6 and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
