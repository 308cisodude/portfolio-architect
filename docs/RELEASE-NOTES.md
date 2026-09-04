# Portfolio Architect v1.63.0 release notes

v1.63.0 replaces the duplicated English/German reference-dashboard authoring model with a deterministic shared-source localization architecture and includes the already accepted zero-exception policy-review presentation correction. It is deliberately **runtime-neutral**: provider acquisition, source arbitration, planning, freshness/LKG, wire schemas, and the verified private-PKI trust boundary are unchanged from v1.62.5.

## One dashboard behavior source

Card, entity, condition, color, icon, bar, and layout logic now lives once under `dashboard/src/shared/`, split into the nine established Sections-view sections. User-facing EN/DE wording is kept separately in matched locale catalogs with 100 keys. German technical localization that is not a human translation is isolated in 40 bounded JSON-Pointer overlay operations; English uses no technical overlay.

The old duplicated `dashboard/en/`, `dashboard/de/`, root section fragments, and temporary authoring files are retired. `dashboard/bilingual-dashboard.yaml` remains supported as a compatibility surface and is byte-identical to the generated combined dashboard.

## Static generation only

`tools/build_dashboard.py` resolves a selected locale at development/release time and emits normal static Home Assistant YAML. Nothing new runs on Home Assistant or the Raspberry Pi: there is no runtime generator, include processor, custom parser, JavaScript, helper entity, frontend plugin, or custom-card dependency.

Release packaging regenerates all dashboard outputs and refuses stale committed generated files. Regression coverage locks locale-key parity, complete `$i18n` resolution, overlay bounds, deterministic byte output, canonical semantic hashes, and the compatibility alias.

## Single-language release artifacts

In addition to the existing combined EN/DE dashboard, releases now publish dedicated English-only and German-only YAML. A user who wants one language can therefore import only one view instead of loading both. Future language additions can reuse the shared card structure without multiplying source logic or bloating existing single-language installations.

Published dashboard artifacts are:

- `portfolio-architect-v1.63.0-dashboard-en.yaml`;
- `portfolio-architect-v1.63.0-dashboard-de.yaml`;
- `portfolio-architect-v1.63.0-bilingual-dashboard.yaml`.

## Zero-exception review presentation

When `sensor.portfolio_architect_accepted_exception_count` is zero, the policy section now shows a green exception state and explicitly says that exception review is not required. The normal and overdue exception-review date tiles are visible only when at least one accepted exception exists. Existing accepted-exception detail entities and governance semantics are unchanged.

## Unchanged contracts

v1.63.0 keeps config-entry schema 13, REST portfolio schema 1, Gateway health schemas through 10, Supervisor discovery schemas 1/2, provider identities, explicit acquisition authority with **no silent fallback** and `fallback_policy: none`, evidence clocks, freshness thresholds, LKG/anti-rollback/source-set atomicity, planner and funding economics, advisory-only behavior, verified private-PKI/bearer authentication, and the **authenticated DKB FinTS** research gate unchanged. Authenticated DKB FinTS remains disabled.

All four official Gateway Apps are version-aligned to v1.63.0; their runtime/provider behavior is unchanged. Portfolio Architect remains advisory-only: there is **no trading**, order placement, or automated money movement. The historical Comdirect LEGACY App remains removed from the active repository; the canonical provider-qualified Comdirect App remains the supported package.

## Preserved compatibility and security contracts

The release remains bounded by the established contracts used by older regression gates:

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 10 remains current, and schemas 1–9 remain supported;
- presentation schema 2 remains unchanged;
- broker schemas 1/2/3 remain unchanged;
- the v1.33.0 source-freshness and plan-schedule separation remains in force: recurring review scheduling is anchored to the latest valid Portfolio Architect evaluation and v1.63.0 does not change any configured freshness threshold;
- authenticated DKB FinTS acquisition remains disabled; the earlier v1.19.0-rc2 experimental brokerage direction is not promoted by this release;
- Trade Republic PDF parsing remains provider-local in its Gateway App; v1.63.0 does not move PDF parsing into Portfolio Architect;
- No trading, order, transfer, payment, or transaction-history capability is added;
- the historical Comdirect LEGACY slug is not reused after removal from the active repository;
- runtime/provider functionality outside the static dashboard/localization scope is not included.
