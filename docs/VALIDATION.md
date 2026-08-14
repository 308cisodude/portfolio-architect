# v1.26.0 validation

Portfolio Architect v1.26.0 retains the complete provider-App,
publication/privacy and runtime regression pipeline and adds multi-Gateway
aggregation contracts. Validation must prove:

- all integration and three provider App package versions align with 1.26.0;
- the existing primary REST configuration remains backward compatible;
- up to four additional REST Gateways can be represented in private config-entry
  options while the total supplemental-source bound remains eight;
- additional endpoints remain local-only and bearer-authenticated;
- an additional Gateway is accepted only with health schema 6, a stable unique
  `provider_id`, a live snapshot and matching timestamp/count/fingerprint evidence;
- duplicate REST endpoints/providers are rejected, and DKB is not configured both
  as a REST supplement and an existing DKB CSV supplement;
- all configured REST snapshots are merged through the existing provider-neutral
  aggregation engine without provider-specific calculation branches;
- per-position provenance survives aggregation;
- `source_count` counts source instances while `provider_count` / `provider_ids`
  count distinct providers;
- the current synthetic Comdirect + Trade Republic + DKB aggregate makes all seven
  target positions held, including Robotics from Trade Republic;
- an unavailable or inconsistent configured additional Gateway never causes silent
  provider dropout: a matching complete HA LKG is retained, otherwise the refresh
  fails closed;
- adding/removing an additional Gateway changes the private source-set LKG
  fingerprint;
- supplemental Gateway diagnostics contain bounded health/provider information and
  never bearer tokens;
- the Source provider reference-dashboard tile uses the provider-summary attribute;
- Trade Republic changes to `boot: auto`, while DKB remains experimental and
  `manual_only`;
- the accepted v1.25 Trade Republic PDF parser/privacy/integrity contracts continue
  to pass unchanged;
- the common REST API remains authenticated GET-only and no provider App gains
  trading/order/transfer/payment/transaction-history capability;
- payload schema 8, REST schema 1, health schema 6, authorized-cash and actionability
  semantics remain unchanged;
- source, Git history and every built artifact pass the v1.22 privacy/Gitleaks gates;
  and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

Live acceptance additionally requires the real accepted Trade Republic snapshot to
join the existing Comdirect + DKB portfolio, changing target architecture from 6/7
to 7/7, followed by a temporary Trade Republic outage that proves the complete 7/7
aggregate is retained as non-actionable LKG rather than recomputed as 6/7.
