# Installation

## HACS installation after public repository configuration

After the repository has been published and accepted as a HACS custom repository:

1. Add the repository URL to HACS as an **Integration** repository.
2. Install **Portfolio Architect**.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Portfolio Architect**.

HACS consumes the fixed release asset `portfolio_architect.zip`. The Gateway App
is not installed by HACS and remains a separate local App or App-repository
package.

## Manual Home Assistant installation

1. Extract the versioned integration drop-in so this directory exists:
   `/config/custom_components/portfolio_architect`.
2. Create a portfolio data directory, for example
   `/config/portfolio-architect`.
3. Put these files in that directory:
   - `portfolio.yaml`
   - `policy.yaml`
   - `instruments.yaml`
   - `broker.yaml`
   - optional `exceptions.yaml`
4. For a CSV source, put the current portfolio CSV below `/config`.
5. Restart Home Assistant.

Never store backup directories directly below `/config/custom_components`.

## Optional local Gateway App

For Comdirect API access on Home Assistant OS, copy the complete
`portfolio_architect_gateway` directory from the App bundle into:

```text
/addons/portfolio_architect_gateway
```

In Home Assistant, open **Settings → Apps → App store**, select the three-dot
menu, choose **Check for updates**, and install **Portfolio Architect Gateway — Comdirect**
from **Local apps**. Start the App and open its Web UI to perform the PhotoTAN
bootstrap.

The App keeps persistent state in its private `/data/gateway` directory. It
requires no Home Assistant configuration mapping and publishes no port to the
LAN. The standalone Docker Gateway remains documented in `gateway/README.md`.

## UI setup

Open **Settings → Devices & services → Add integration → Portfolio Architect**.
Choose a provider:

- **Comdirect depot CSV** for the established Comdirect export;
- **Generic mapped CSV** for another local CSV format;
- **Local REST JSON gateway** for the bounded provider-neutral local API contract.

Enter paths relative to `/config`:

```text
Portfolio CSV path:              portfolio-architect/depot.csv
Portfolio configuration folder:  portfolio-architect
```

For a generic CSV, the flow asks for encoding, delimiter, header row, number
format, and column mapping. Official v1.27 Gateway Apps are discovered through Home
Assistant Supervisor: discovery supplies the verified-HTTPS internal endpoint and
public private-CA trust, while the user supplies the dedicated Gateway bearer token.
Market values must already be in EUR in every adapter. Banking credentials and TLS
private keys remain inside the Gateway App.

For a local-development installation the Comdirect endpoint is typically
`https://local-portfolio-architect-gateway:8787/api/v1/portfolio`; repository-installed
Apps receive a Supervisor-generated repository prefix, so discovery rather than a
hard-coded hostname is authoritative.

The flow calculates and validates the complete source before creating or
reconfiguring the single service config entry. No YAML integration configuration
or command-line sensor is required. New/reconfigured REST sources require verified
HTTPS.

### Additional provider Gateways (v1.27)

A newly discovered supplemental Gateway is never added silently. Supervisor supplies
its HTTPS endpoint/public CA; Portfolio Architect asks for explicit confirmation and
the Gateway's dedicated bearer token, then validates health-schema-6 provider
identity, the live snapshot and integrity metadata before changing portfolio scope.

Existing v1.26 HTTP supplemental Gateways migrate in place when their v1.27 App is
updated, but only after verified HTTPS succeeds with the existing token. Keep all
Gateway endpoints on the private App network; no host/LAN port mapping is required.
Additional bearer tokens and private CA trust are config-entry data/options and are
never included as secret material in diagnostics or portfolio payloads.

## Native plan configuration

Open **Settings → Devices & services → Portfolio Architect → Configure →
Investment plan**.

`portfolio.yaml` supplies the initial plan and remains the fallback until the UI
plan is saved. Portfolio schema 2 uses a stable user-owned `target_id` for each
target; keep it unchanged across reordering, renaming, or deliberate instrument
replacement so Home Assistant target entity identity remains stable. Schema 1
legacy `id` plans remain supported. The UI supports budget, budget basis, frequency,
recurring execution days, review lead time, instrument scope, stable target IDs,
target weights, and purchase eligibility. See `docs/TARGET-ARCHITECTURE.md`.

## Verification

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py
```

All three markers must report `1.35.1`.
