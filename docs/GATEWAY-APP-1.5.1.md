# Portfolio Architect Gateway Home Assistant App v1.5.1

## Architecture

```text
api.comdirect.de
       │ outbound HTTPS
       ▼
Portfolio Architect Gateway App
  ├─ PhotoTAN bootstrap through admin-only Ingress
  ├─ private /data/gateway state
  └─ authenticated REST schema 1 on internal port 8787
       │ internal Supervisor network
       ▼
Portfolio Architect custom integration
```

The App is classified as a service so Supervisor starts it before Home Assistant Core. The App and custom integration are separate containers. The App does not map
Home Assistant configuration and requests no Supervisor, Home Assistant, Auth,
Docker, host-network, device, or privileged access.

## Installation

1. Extract the App bundle so this directory exists:

   ```text
   /addons/portfolio_architect_gateway/config.yaml
   ```

2. In Home Assistant open **Settings → Apps → App store**.
3. Open the three-dot menu and select **Check for updates**.
4. Open **Portfolio Architect Gateway** under **Local apps** and choose
   **Install**.
5. Keep port 8787 disabled in the App network configuration.
6. Start the App and open its Web UI.

Supervisor builds the App locally during installation. The first build can take
several minutes because the pinned Python base image must be downloaded.

## PhotoTAN bootstrap

In the App Web UI, enter:

- Comdirect API client ID;
- Comdirect API client secret;
- Comdirect username;
- Comdirect password.

Start the bootstrap and approve the PhotoTAN push request. The username/password
are retained only by the running bootstrap thread. They are not written to App
options, the App data volume, logs, diagnostics, or backups.

After success, the UI displays:

```text
Endpoint: http://local-portfolio-architect-gateway:8787/api/v1/portfolio
Token:    generated App-local bearer token
```

The API client ID and client secret are persisted with mode `0600`, because
OAuth refresh-token operations require them. OAuth/session state is also stored
privately but is excluded from Home Assistant backups.

## Deliberate source switch

Before switching, compare the gateway's position count and portfolio total with
the latest CSV import. Then open:

**Settings → Devices & services → Portfolio Architect → Reconfigure**

Select **Local REST JSON gateway**, enter the endpoint and token shown by the App,
and complete validation. Keep the CSV file and configuration as the rollback
path until several successful refresh and renewal cycles have completed.

## Recovery

When the App reports reauthentication required:

1. open the App Web UI;
2. enter the four Comdirect bootstrap fields again;
3. approve PhotoTAN;
4. wait for a successful refresh.

The generated local gateway token remains stable, so Portfolio Architect does
not normally require reconfiguration.

## Backup behaviour

The App uses cold backups. The last-known-good normalized snapshot, gateway token,
and Comdirect API client credentials are included in the App data backup.
`gateway/comdirect-session.json` is excluded. After restoring a backup, run the
PhotoTAN bootstrap again before relying on live data.

Treat Home Assistant backups as sensitive because the retained API client secret
and local gateway token are still credentials, even though neither can replace
the bank username/password and PhotoTAN factor.
