# Portfolio Architect Gateway — Trade Republic v1.45.1

Version 1.45.1 is package alignment for the DKB legacy-migration hotfix. The common Gateway health document now represents expired cached snapshots consistently; the DKB-only migration snapshot endpoint is not enabled here. Trade Republic holdings/cash statement acquisition is unchanged.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 6 and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
