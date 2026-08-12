# Support policy

Portfolio Architect is a community-maintained Home Assistant custom integration.
It is not maintained, reviewed, or supported by Home Assistant, Comdirect, DKB,
or any execution venue.

## Supported versions

Security and correctness fixes are provided for:

- the current stable Portfolio Architect release; and
- the immediately preceding stable release while a documented upgrade path exists.

The Home Assistant support floor for the 1.19.x release line is **2026.7.0**.
The project targets the current and immediately previous monthly Home Assistant
release, subject to automated compatibility checks. Beta releases receive
best-effort compatibility only.

Gateway App versions 1.16.1 and later remain compatible with Portfolio Architect
1.19.1 through the legacy reserve contract. Gateway App 1.19.0 or newer is required
for the configurable authorized-cash policy and its explanatory metadata; 1.19.1
contains the corrected capped-to-all-available Ingress transition.

## Getting help

Before reporting a problem:

1. confirm the installed Portfolio Architect and Home Assistant versions;
2. reproduce the issue after one integration reload;
3. review diagnostics and remove all credentials and private portfolio data;
4. check the documented known limitations and upgrade notes.

Use public issues for ordinary defects and feature requests. Use private
vulnerability reporting for issues that could expose credentials, authentication
material, account metadata, or portfolio data.

## Out of scope

The project does not provide investment advice, trade execution, order placement,
payment initiation, tax calculation, or guarantees about broker availability,
pricing, or data accuracy.
