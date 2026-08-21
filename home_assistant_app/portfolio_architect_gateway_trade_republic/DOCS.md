# Portfolio Architect Gateway — Trade Republic v1.41.0

Version 1.41.0 adds a separate strict local `KONTOAUSZUG` cash-statement import beside the established `DEPOTAUSZUG` holdings import. The two evidence families persist independently and are composed only at the provider-neutral REST boundary; raw PDFs and transaction/account identity data are not retained.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 6 and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
