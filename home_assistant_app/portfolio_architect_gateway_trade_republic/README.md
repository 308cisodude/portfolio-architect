# Portfolio Architect Gateway — Trade Republic v1.24.0

Version 1.24.0 publishes the separate, isolated Home Assistant App identity for Trade Republic.
The App starts only when explicitly requested and currently exposes a fail-closed provider shell; live acquisition is intentionally not implemented in this release.

The package owns its own `/data/gateway` volume, API token, cached-snapshot path and provider health identity. It shares only the audited provider-neutral Gateway runtime contract with the other Portfolio Architect provider Apps.

Do not configure Portfolio Architect to use this App as a portfolio source yet.
