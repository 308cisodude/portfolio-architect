# Comdirect gateway architecture

## Trust zones

```text
Comdirect API
     │ outbound HTTPS only
     ▼
Dedicated gateway container/host
  - Comdirect client credentials
  - OAuth/PhotoTAN session state
  - read-only endpoint allowlist
  - provider-neutral snapshot
     │ authenticated local GET only
     ▼
Home Assistant / Portfolio Architect
  - dedicated gateway bearer token
  - no bank credential
  - unchanged canonical calculation engine
```

The Comdirect API session may grant brokerage scope broader than portfolio
retrieval. The gateway therefore does not rely on OAuth scope as its sole
read-only control. Production code implements only:

- OAuth token acquisition/refresh;
- session discovery, validation, and 2FA activation;
- depot discovery;
- position retrieval;
- instrument metadata retrieval.

There is no generic external URL function, order endpoint, order model, transfer
operation, or write method exposed to callers.

## Data minimization

The gateway returns only:

- source-owned snapshot timestamp;
- WKN-compatible stable identifier;
- display name;
- EUR market value;
- optional ISIN;
- normalized instrument type.

It does not return depot numbers, account numbers, quantities, purchase prices,
profit/loss, transactions, orders, personal data, or bank/session metadata.

## Authentication lifecycle

The one-shot bootstrap uses the bank username/password and registered PhotoTAN
device to obtain secondary OAuth state. The long-running service does not mount
or read the username/password. It uses the persisted refresh token, client
credentials, and qSession state. If renewal fails, a human-approved bootstrap is
required again.

## Availability model

The last valid provider-neutral snapshot is written atomically and can be served
through transient bank/API failures. Its original `generated_at` timestamp is
preserved. Portfolio Architect independently evaluates freshness, preventing an
old cache from appearing current.

The gateway health response contains timestamps and status only; it never
contains holdings or monetary values. Both health and portfolio endpoints require
the dedicated local bearer token.

## Deployment controls

The reference container:

- uses a digest-pinned official Python/Alpine runtime;
- adds no application dependency;
- runs as UID/GID 65532;
- has a read-only root filesystem and 16 MiB no-exec tmpfs;
- drops all capabilities;
- enables `no-new-privileges`;
- has PID, memory, and CPU limits;
- publishes on loopback unless an explicit host IP is configured.

Host firewalling and network segmentation remain mandatory deployment controls.
Native TLS is available for deployments where the dedicated bearer token crosses
a network segment.
