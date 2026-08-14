# v1.26.3 validation

Portfolio Architect v1.26.3 retains the complete v1.26.2 presentation/source-outage,
v1.26.1 ISIN-first, v1.26 atomic-LKG, provider-App, publication/privacy, and
reproducible-release regression pipeline.

The release-specific contracts must prove:

- integration and all three provider App package versions align with 1.26.3;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- existing machine-readable entity IDs, states and availability semantics remain
  stable;
- the German Allocated/Purchases dashboard values render through bounded attributes
  of the always-available actionability entity, so `Nicht verfügbar` remains German
  even while the original actionable sensors are unavailable;
- the underlying recommended-total and purchase-count sensors continue to fail
  closed when the source is non-actionable;
- the policy reference dashboard does not render aggregate Checks/Opportunities
  counters while their native entities remain implemented;
- exception count/detail and last-decision/next-review tiles are adjacent and use
  concise English/German lifecycle labels;
- concrete optimisation opportunity tiles remain present;
- conditional policy error/warning tiles remain available when findings require
  attention;
- v1.26.2 failed-source identification and translated attention reason/action remain
  unchanged;
- v1.26.1 ISIN-first identity/collision tests continue to pass unchanged;
- Trade Republic statement-parser privacy/integrity contracts remain unchanged;
- Comdirect authentication/account/cash behavior remains unchanged;
- the common REST API remains authenticated GET-only and no provider App gains
  trading/order/transfer/payment/transaction-history capability;
- source, history and built artifacts continue to pass publication/privacy gates;
  and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

Live acceptance starts from the established three-source/three-provider 7/7
portfolio. After upgrade, the healthy state must remain unchanged. Temporarily
stopping Trade Republic must still retain 7/7 as non-actionable LKG, identify the
failed source, and show German outage diagnostics. In that degraded state the
**Zugeordnet** and **Käufe** tiles must now render **Nicht verfügbar**, not the
frontend-language `Unavailable`. After Trade Republic restarts, the dashboard must
recover to healthy/live 7/7 without reconfiguration or statement re-import.
