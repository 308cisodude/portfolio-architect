# v1.26.2 validation

Portfolio Architect v1.26.2 retains the complete v1.26.1 provider-App,
publication/privacy, multi-Gateway, atomic-LKG and ISIN-first regression pipeline.
The release adds presentation/diagnostic contracts that must prove:

- all integration and three provider App package versions align with 1.26.2;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- machine-readable entity IDs and state contracts remain stable;
- German reference-dashboard state values use explicit German presentation
  attributes rather than depending on the global Home Assistant frontend language;
- unavailable plan values render explicitly as `Nicht verfügbar` in the German
  reference dashboard;
- the English and German Source unavailable tiles render bounded source summaries;
- one failed Trade Republic supplemental Gateway is identified as `Trade Republic
  Gateway` / `Trade-Republic-Gateway` without exposing its endpoint or token;
- DKB CSV failures expose only bounded instance labels and never configured paths;
- several simultaneous supplemental REST Gateway failures can be collected in one
  refresh rather than stopping after the first failure;
- any supplemental failure still prevents partial aggregation and retains only a
  matching complete Home Assistant LKG or fails closed;
- `supplemental_source_unavailable` is a declared/translatable attention-reason
  state so the dashboard no longer renders `None` for that outage class;
- diagnostics expose only bounded unavailable-source IDs/count/summary and no
  credentials, endpoints, file paths, account identifiers or source documents;
- v1.26.1 ISIN-first identity/collision tests continue to pass unchanged;
- the accepted Trade Republic statement-parser privacy/integrity contracts remain
  unchanged;
- Comdirect authentication/account/cash behavior remains unchanged;
- the common REST API remains authenticated GET-only and no provider App gains
  trading/order/transfer/payment/transaction-history capability;
- source, history and built artifacts continue to pass publication/privacy gates;
  and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

Live acceptance starts from the known-good v1.26.1 three-source/three-provider 7/7
portfolio. After upgrade, that healthy state must remain unchanged. The updated
German reference dashboard must show German presentation values even when the
frontend language is English. Temporarily stopping Trade Republic must retain the
complete 7/7 aggregate as non-actionable LKG, identify the missing source as the
Trade Republic Gateway, and show a translated supplemental-source attention reason.
Restarting Trade Republic must recover to healthy/live 7/7 without reconfiguration
or statement re-import.
