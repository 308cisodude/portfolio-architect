# Upgrade to Portfolio Architect 1.24.1

Version 1.24.1 fixes startup of the experimental DKB and Trade Republic provider shells published in 1.24.0. The established Comdirect runtime and Portfolio Architect behavior are unchanged.

## What is fixed

The v1.24.0 DKB/TR shell packages deliberately excluded Comdirect-specific modules. A leftover runtime import of the Comdirect `GatewayConfig` type in the common server caused the shell process to exit with `ModuleNotFoundError` before Ingress or health could start. Version 1.24.1 makes that dependency type-check-only while retaining provider-neutral `ServerConfig` at runtime.

The release also strengthens CI so the exact reduced shell package must import its startup module successfully, each Docker image must build, and the DKB/TR containers must remain running with ports 8099 and 8787 listening.

## Upgrade procedure

1. Update **Portfolio Architect Gateway — Comdirect** to 1.24.1 in place if an update is offered; do not uninstall it.
2. Update **Portfolio Architect** through HACS to 1.24.1 and restart Home Assistant once.
3. Update installed **Portfolio Architect Gateway — DKB** and **Portfolio Architect Gateway — Trade Republic** shells to 1.24.1. If a shell was not installed for v1.24.0 acceptance, installation remains optional.
4. Start each experimental shell manually for acceptance only. Its Ingress page must load and state that live acquisition is not implemented.
5. Do not configure Portfolio Architect to consume DKB/TR as live REST sources yet.

No Comdirect reauthentication, account reselection, API-token change, cash-policy migration, configuration-entry migration, entity migration or dashboard replacement is required solely because of this hotfix.

## Expected shell state

A running DKB/TR shell intentionally has no portfolio snapshot. Health schema 6 identifies `dkb` or `trade_republic`, while operating mode remains unavailable/degraded because acquisition is not implemented. This is fail-closed behavior, not a startup error.
