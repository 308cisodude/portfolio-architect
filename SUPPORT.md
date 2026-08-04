# Support policy

Portfolio Architect is a community-maintained Home Assistant custom integration.
It is not maintained, reviewed, or supported by Home Assistant, Comdirect, DKB, or
any execution venue.

## Supported versions

Security and correctness fixes are provided for:

- the current stable Portfolio Architect release; and
- the immediately preceding stable release while a documented upgrade path exists.

The stable known-good baseline is v1.18.0. Version v1.19.0-rc1 is an experimental
prerelease and receives best-effort support only. It must not be treated as a stable
fee-discovery contract until real-account acceptance is complete.

The Home Assistant support floor for the 1.18.x/1.19.x release lines is
**2026.7.0**. The project targets the current and immediately previous monthly Home
Assistant release, subject to automated compatibility checks.

Gateway App versions 1.16.1 and later remain compatible with the established REST
portfolio schema 1 and health schema 5. Experimental probe testing requires Gateway
App v1.19.0-rc1 because older Apps intentionally contain no cost-indication POST.

## Getting help

Before reporting a problem:

1. confirm the installed Portfolio Architect, Gateway App, and Home Assistant versions;
2. reproduce the issue after one integration/App restart as appropriate;
3. review diagnostics and remove all credentials and private portfolio data;
4. for probe issues, share only the sanitized JSON result;
5. check the documented known limitations and upgrade notes.

Use public issues for ordinary defects and feature requests. Use private
vulnerability reporting for issues that could expose credentials, authentication
material, account metadata, portfolio data, or internal depot/venue identifiers.

## Out of scope

The project does not provide investment advice, trade validation or execution,
order placement, payment initiation, tax calculation, or guarantees about broker
availability, pricing, promotion status, or data accuracy. An ordinary-order ex-ante
cost indication is not represented as a savings-plan quotation.
