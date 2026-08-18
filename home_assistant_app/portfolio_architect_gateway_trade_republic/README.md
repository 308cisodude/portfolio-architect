# Portfolio Architect Gateway — Trade Republic v1.33.1

Version 1.33.1 is package/User-Agent alignment for the Home Assistant-side recurring-schedule
anchor hotfix. The bounded latest-import diagnostic introduced in v1.32.0 and
the established local `DEPOTAUSZUG` statement-import/provider-snapshot contracts are unchanged.

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
