# Upgrade to Portfolio Architect v1.58.0

v1.58.0 is an additive acquisition-authority architecture release. It does not require a dashboard replacement, provider reconfiguration, new credentials, or a change to the acquisition methods already selected in the provider Gateways.

## Upgrade order

1. Update the Portfolio Architect Home Assistant integration to v1.58.0 and restart Home Assistant when requested.
2. Update the installed canonical Comdirect, DKB and Trade Republic Apps to v1.58.0.
3. If Generic Import is installed, align it to v1.58.0 as well.
4. Do not change a provider acquisition method merely because of the upgrade.

## Expected authority after upgrade

For the currently supported/live-accepted production configuration:

- Comdirect: holdings and cash authority = `live_api`;
- Trade Republic: holdings and cash authority = `pdf`;
- DKB: holdings and cash authority = `csv`;
- all capability fallback policies = `none`.

Comdirect may advertise complete `csv` as another ready method, but it does not become authoritative when `live_api` is unavailable. An operator must explicitly switch the complete Comdirect acquisition method before CSV can become authoritative. DKB FinTS remains `research_only`; authenticated DKB FinTS acquisition remains disabled. Trade Republic `live_api` remains unavailable.

## Live acceptance

After alignment, confirm:

- integration and installed Apps report v1.58.0;
- exactly the existing production providers remain present;
- Gateway health schema 9 is accepted and capability authority is visible in PA diagnostics/status;
- Comdirect remains `live_api`, Trade Republic remains `pdf`, and DKB remains `csv`;
- capability authority for holdings/cash matches those methods and every capability reports `fallback_policy: none`;
- all sources remain healthy/fresh, HA LKG remains inactive, and planner/cash-routing economics are unchanged;
- stopping or making the active Comdirect live source unavailable does not silently make prepared CSV authoritative.

No dashboard YAML replacement is required.

If Generic Import is installed only for its isolated experimental smoke, do **not** add its discovery card/source to the real Portfolio Architect production source set. That smoke must not alter the real source set; Generic Import should be uninstalled after this standalone smoke test unless it is intentionally being adopted.
