# Portfolio Architect Gateway — Trade Republic v1.41.1

Version 1.41.1 is package alignment for the Portfolio Architect local-cash routing tie-break hotfix. The separate strict local `DEPOTAUSZUG` holdings and `KONTOAUSZUG` cash-statement imports introduced in v1.41.0 are unchanged.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 6 and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
