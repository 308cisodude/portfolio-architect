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
menu, choose **Check for updates**, and install **Portfolio Architect Gateway**
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
format, and column mapping. For REST, it asks for the local endpoint and a
dedicated bearer token. Market values must already be in EUR in every adapter.
Banking credentials remain in the Gateway.

The local App endpoint is:

```text
http://local-portfolio-architect-gateway:8787/api/v1/portfolio
```

The flow calculates and validates the complete source before creating or
reconfiguring the single service config entry. No YAML integration configuration
or command-line sensor is required.

## Native plan configuration

Open **Settings → Devices & services → Portfolio Architect → Configure →
Investment plan**.

`portfolio.yaml` supplies the initial plan and remains the fallback until the UI
plan is saved. The UI supports budget, budget basis, frequency, recurring
execution days, review lead time, instrument scope, target weights, and purchase
eligibility.

## Verification

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py
```

All three markers must report `1.17.2`.
