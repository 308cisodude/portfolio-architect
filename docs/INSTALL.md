# Installation

Portfolio Architect requires Home Assistant 2026.7.0 or newer. The integration
and its four Gateway Apps are separate packages. HACS installs only the
integration; provider acquisition runs in the appropriate App.

## Install the integration

### HACS

1. Add this repository to HACS as a custom **Integration** repository.
2. Install **Portfolio Architect** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → Portfolio Architect**.

HACS consumes the release asset `portfolio_architect.zip`. The repository's
README appears in HACS; the current behavior and upgrade steps are documented in
[release notes](RELEASE-NOTES.md).

### Manual

Extract the versioned Home Assistant drop-in over `/config` so that
`/config/custom_components/portfolio_architect` exists, then restart Home
Assistant and add the integration. Do not store backups below
`/config/custom_components`.

## Initialize a new Portfolio Architect installation

The integration creates one service entry with an explicit **source required**
state. It does not invent a source, target allocation, investment policy, or
execution provider.

1. Choose a configuration directory below `/config` in the setup flow; the
   default is `portfolio-architect`.
2. Install and configure at least one Gateway App. Its ready provider is offered
   as a candidate, not added silently. Under **Configure → Portfolio sources**,
   explicitly adopt the first source.
3. Complete the native **initial setup** when the integration shows
   **plan required**. Select target instruments and supply the allocation and
   policy facts yourself. The four required YAML files are written only after
   the whole candidate validates.
4. Add execution providers and savings-plan routes separately when you have
   verified their availability and fees.

Advanced users may instead point the setup flow at a complete, valid existing
directory containing `portfolio.yaml`, `policy.yaml`, `instruments.yaml`,
and `broker.yaml`; `exceptions.yaml` is optional. Partial or invalid
existing configuration is not overwritten automatically. See
[initial setup](UPGRADE-1.62.1.md) and [target architecture](TARGET-ARCHITECTURE.md).

## Install provider Gateway Apps

Install the version-aligned App bundles through the Home Assistant App repository
or extract each complete App directory below `/addons` for a local installation:

| App | Local directory | Supported acquisition |
| --- | --- | --- |
| Comdirect | `portfolio_architect_gateway_comdirect` | Live API or explicit complete CSV |
| DKB | `portfolio_architect_gateway_dkb` | Depot and Girokonto CSV, or explicitly activated manual FinTS holdings and selected-account cash |
| Trade Republic | `portfolio_architect_gateway_trade_republic` | Holdings and cash statement PDFs |
| Generic Import | `portfolio_architect_gateway_import` | Mapped holdings CSV with optional EUR cash |

In **Settings → Apps → App store**, use **Check for updates** after copying a
local App, then install and start it. Configure acquisition through its admin
Ingress page. Gateway Apps keep credentials and raw input private and do not
publish a LAN port.

Home Assistant Supervisor discovery supplies each App's internal verified-HTTPS
endpoint and public private-CA trust. You supply the App's dedicated bearer
token when adopting it. An additional discovered Gateway also requires explicit
confirmation and validation before it joins the portfolio. Avoid hard-coded
App hostnames: repository-installed Apps may receive a generated prefix.

DKB starts with CSV authority. Select one eligible EUR cash account in the DKB
App, then perform a complete manual FinTS holdings-and-cash read with this
release. The read alone does not change planning. Review the bounded authority
status and separately confirm the switch to FinTS for both capabilities. Each
observation expires after 14 days; a missing or expired observation blocks the
FinTS snapshot without an automatic CSV fallback. The App's investment cash
authorization applies to the selected source. Follow the
[DKB upgrade guide](UPGRADE-1.66.0.md) before switching.

## Check the installation

Confirm the integration and installed Apps report the intended aligned release
version. In **Configure → Portfolio sources**, verify the provider identities,
active acquisition methods, evidence dates, and freshness. A missing or failed
source must not silently switch acquisition methods. Check the plan's current
actionability before acting on any recommendation.

For source builds and release validation, see [quality](QUALITY.md) and
[publishing](PUBLISHING.md).
