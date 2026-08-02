# Upgrade to Portfolio Architect 1.17.1

Version 1.17.1 replaces the unpublished v1.17.0 publication candidate and adds
software-supply-chain and local REST transport hardening. Portfolio calculations,
entities, configuration, dashboard behavior, and Gateway schemas are unchanged.

## 1. Update the integration

Upload `portfolio-architect-v1.17.1-ha-dropin.zip` to `/config`, back up the
current custom component and Portfolio Architect data directory, extract the
archive over `/config`, run `ha core check`, and restart Home Assistant.

After restart, verify `sensor.portfolio_architect_version` reports `1.17.1` and
that the existing live or last-known-good portfolio remains available.

The runtime change affects only the authenticated local REST transport: the DNS
answer that passes the private-address allowlist is now pinned to the subsequent
connection. The original hostname remains the TLS and HTTP identity.

## 2. Dashboard

No dashboard replacement is required. The v1.16.3 bilingual dashboard remains
fully compatible.

## 3. Gateway

No Gateway update is required. Gateway App v1.16.1 and later remain compatible.
The v1.17.1 Gateway package aligns release metadata only.

## 4. Replace the unpublished publication source

Do not continue with a configured v1.17.0 source directory. Extract a fresh copy
of the v1.17.1 complete source archive, run `tools/configure_publication.py` again
with the same real repository and code-owner values, and then run:

```bash
python tools/check_publication.py --strict
./tools/release_check.sh
```

The configurator writes the active `.github/CODEOWNERS` file and removes the
example file. The strict checker also verifies immutable GitHub Action refs,
immutable validator image digests, the Ubuntu 24.04/Python 3.14.6 hash-locked
validation toolchain, and explicit ownership of security-sensitive repository
paths.

Do not tag the release until the first GitHub-hosted Validate release, HACS, and
hassfest jobs are green. The local environment verifies the contracts but does
not execute the external validator containers or the exact hosted Python runner.
