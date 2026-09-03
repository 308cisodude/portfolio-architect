# Portfolio Architect v1.62.4 release notes

v1.62.4 is a narrow Home Assistant runtime hotfix on top of v1.62.3. Clean-room first-run acceptance exposed two independent integration-side lifecycle/async-hygiene defects after the v1.62 architecture itself had already validated correctly.

## Immediate first-run activation no longer fails to unload

A newly initialized Portfolio Architect entry deliberately loads in `source_required` / `plan_required` without a coordinator or forwarded `sensor`, `binary_sensor` or `date` platforms. After the initial plan wizard successfully staged, calculated and atomically installed the four validated YAML documents, v1.62.3 persisted `configured` and immediately requested a Home Assistant config-entry reload.

The unload handler incorrectly decided what to unload from the newly persisted setup-state. It therefore tried to unload normal PA platforms even though that loaded lifecycle had never created them, causing Home Assistant to report **Failed to unload**. A subsequent Home Assistant restart loaded the same generated configuration normally, proving that the files and configured cold-start path were valid.

v1.62.4 makes runtime presence authoritative for unload behavior. If `entry.runtime_data` is `None`, unload succeeds without forwarding platform teardown. Once a normal configured coordinator/runtime exists, the established platform-unload path remains unchanged. The validated `plan_required` → `configured` transition can therefore reload immediately and create normal entities without requiring a Home Assistant restart.

## Private-CA normalization is event-loop safe

Live Home Assistant logs also showed `ssl.create_default_context(cadata=...)` / `load_verify_locations` being called synchronously from REST/private-CA normalization during config/discovery handling. Home Assistant correctly flagged this as blocking work on the event loop.

v1.62.4 keeps only bounded PEM envelope/base64 decoding in synchronous normalization. Semantic X.509/private-CA trust loading remains fail-closed in `_rest_ssl_context()`, where authenticated health and snapshot requests already construct the hostname-verifying TLS context through `hass.async_add_executor_job()`.

This does **not** weaken private-PKI validation. Invalid trust material still fails before a Gateway can be adopted or consumed; the expensive trust-store operation merely stays on the executor boundary where it belongs.

## Compatibility and preserved contracts

The v1.62.3 complete bounded German Trade Republic cash-date month matrix is unchanged. Trade Republic parsing/reconciliation, Generic multi-profile acquisition, Comdirect acquisition, DKB CSV acquisition and the DKB research-only FinTS probe are unchanged.

**Comdirect LEGACY remains removed from the active repository.** REST portfolio schema 1, payload schema 8, presentation schema 2, broker schemas 1/2/3, config-entry schema 13, Gateway health schemas 1–10, Supervisor discovery schemas 1/2, `fallback_policy: none`, evidence freshness, verified private-PKI HTTPS, bearer authentication, DNS pinning, LKG/anti-rollback/source-set atomicity and planner/funding semantics remain intact. **Authenticated DKB FinTS remains disabled** and research-only. There is **no silent fallback** between acquisition methods. No trading, order, transfer, payment, transaction-history, sell or withdrawal capability is introduced.

The v1.33.0 source-freshness and plan-schedule separation remains in force. No configured freshness threshold changes. Trade Republic provider-specific PDF parsing stays in its Gateway; this release does not move PDF parsing into Portfolio Architect. No dashboard YAML replacement is required.

## Preserved historical release invariants

For regression clarity, v1.62.4 explicitly preserves these established contracts:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 10 is current; schemas 1–9 remain supported
- config-entry schema 13: unchanged
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- setup states `source_required`, `plan_required`, `configured`: unchanged
- recurring schedule anchoring continues to use the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold.
- Trade Republic provider-specific PDF parsing stays in its Gateway; the complete v1.62.3 German cash-date matrix remains unchanged.
- authenticated DKB FinTS acquisition remains disabled and research-only.
- No trading, order, transfer, payment, or transaction-history capability is introduced.
- Comdirect LEGACY remains removed from the active repository and the historical slug is not reused.
- Acquisition remains explicit with no silent fallback.
- The v1.38.1 dynamic drift presentation is included through the established presentation schema; it is not included as a separate alternate calculation path.
- The historical `v1.19.0-rc2` brokerage-probe idea is not promoted by this release.
