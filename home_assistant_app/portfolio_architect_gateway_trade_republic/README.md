# Portfolio Architect Gateway — Trade Republic v1.35.3

Version 1.35.3 is package alignment for the Home Assistant broker-editor menu-label hotfix.
Trade Republic statement import, accepted-snapshot behavior and the v1.35.2 common retained-cash
contract remain unchanged; this release does not add Trade Republic cash acquisition or authorization.
Trade Republic statement import, accepted snapshots, diagnostics, REST schema 1 and verified
private-PKI transport are unchanged.

The App may persist only an allowlisted/genericized `accepted`, `rejected` or
`internal_error` outcome next to its private snapshot. Unexpected parser/document text is
never echoed into persisted diagnostics, malformed diagnostic state fails closed, and a later
successful import replaces obsolete failure evidence. The diagnostic file is App-private mode
`0600`.

The uploaded PDF is still parsed in memory and is not stored. No persistent PDF SHA-256 or
raw document content is added for troubleshooting. Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 6 and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
