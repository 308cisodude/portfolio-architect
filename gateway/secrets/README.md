# Secret files

Create these five files without a trailing blank line:

- `portfolio_gateway_token` — a random token of at least 32 characters, for example `openssl rand -hex 32`;
- `comdirect_client_id`;
- `comdirect_client_secret`;
- `comdirect_username`;
- `comdirect_password`.

On a native deployment, set owner-only permissions:

```bash
chmod 600 secrets/*
```

Docker Compose mounts these files at `/run/secrets`. The gateway never writes
bank credentials to disk, never returns them through the API, and never includes
them in diagnostics or logs. The persisted session file contains OAuth/session
material and therefore belongs on encrypted storage with access limited to the
gateway host.
