# Upgrade to Portfolio Architect 1.56.0

Version 1.56.0 is a UX/hygiene release from the fully published and live-accepted v1.55.1 baseline. It does not require a broker configuration migration, source reconfiguration, dashboard entity migration, fresh provider evidence, or Comdirect PhotoTAN solely because of the upgrade.

> **Historical Comdirect App retirement:** `portfolio_architect_gateway` / **Comdirect LEGACY** is deprecated in v1.56.0 and v1.56.x is its final published line. If it is still installed, complete the established identity migration to `portfolio_architect_gateway_comdirect` before upgrading beyond v1.56.x. Repository withdrawal is scheduled for v1.57.0. Do not uninstall the legacy App until Portfolio Architect is explicitly healthy on the canonical endpoint.

## Recommended upgrade

1. Update Portfolio Architect through HACS to **1.56.0** and restart Home Assistant once.
2. Update the installed canonical **Portfolio Architect Gateway — Comdirect** App (`portfolio_architect_gateway_comdirect`) to **1.56.0**.
3. Update **Portfolio Architect Gateway — DKB** and **Portfolio Architect Gateway — Trade Republic** to **1.56.0**.
4. Update **Portfolio Architect Gateway — Generic Import** only if it is intentionally installed.
5. Do **not** reinstall the historical `portfolio_architect_gateway` App on installations where the v1.55 identity migration is already complete. It remains published only as **Comdirect LEGACY** for users who still need that migration path.
6. Replace the complete bilingual reference dashboard YAML if you use the shipped reference dashboard; v1.56.0 deliberately consolidates its runtime-health cards.

## Live acceptance

After the update, verify:

- Portfolio Architect remains healthy with the same canonical provider set and no unexpected discovery card;
- Comdirect remains on the existing canonical endpoint and private-CA fingerprint, with its configured acquisition mode unchanged;
- the canonical Comdirect App title no longer contains `NEW`;
- DKB Ingress shows the last anonymous BPD probe dispatch time as explicit `Europe/Berlin` time plus authoritative UTC, with authenticated FinTS still labelled unavailable/research-only;
- Trade Republic and DKB acquisition/freshness semantics are unchanged;
- if Generic Import is installed, its bearer token appears only inside the lower collapsed **Sensitive connection material** section;
- stopping and restarting Generic Import does not leave duplicate Portfolio Architect discovery entries;
- the runtime-health dashboard shows one consolidated incident reason/action tile when attention is required, and one LKG/snapshot-state tile when HA LKG is active;
- routine Ingress page polling no longer produces repetitive INFO-level request-completion lines.

No destructive fault injection is required for v1.56.0 acceptance. Existing diagnostic entities and repairs remain authoritative for incident handling.

## Optional Generic Import standalone cleanup smoke

If Generic Import is not part of the real portfolio source set, its v1.56.0 discovery-lifecycle cleanup may be exercised as a standalone synthetic smoke test. Install/start the App, verify its own discovery publication, then stop and uninstall it. For this smoke, do **not** add its discovery card/source to the real Portfolio Architect configuration. The standalone exercise must not alter the real canonical provider set, and the temporary Generic Import App should be uninstalled after this standalone smoke test.

## DKB research boundary

Do not interpret the Comdirect migration completion or the DKB timestamp cleanup as permission to advance authenticated FinTS. The anonymous BPD probe remains isolated research. CSV evidence stays authoritative and no silent fallback is introduced.
