# v1.26.1 validation

Portfolio Architect v1.26.1 retains the complete provider-App,
publication/privacy and multi-Gateway regression pipeline and adds ISIN-first
instrument-identity contracts. Validation must prove:

- all integration and three provider App package versions align with 1.26.1;
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
- ISIN is the canonical identity whenever available, while WKN is used only as a
  fallback for a position whose ISIN is unavailable;
- a REST position whose `identifier` equals its ISIN is not mislabelled as having a
  WKN;
- an ISIN-only Trade Republic REST position matches the configured Robotics target
  by ISIN and the synthetic Comdirect + Trade Republic + DKB aggregate reaches 7/7;
- WKN fallback still matches a target when the source genuinely lacks ISIN;
- a WKN cannot override a contradictory ISIN, one WKN cannot map to multiple ISINs,
  and one ISIN cannot carry contradictory WKN values; every such collision fails
  closed;
- per-position provenance survives aggregation;
- `source_count` counts source instances while `provider_count` / `provider_ids`
  count distinct providers;
- an unavailable or inconsistent configured additional Gateway never causes silent
  provider dropout: a matching complete HA LKG is retained, otherwise the refresh
  fails closed;
- adding/removing an additional Gateway changes the private source-set LKG
  fingerprint;
- supplemental Gateway diagnostics contain bounded health/provider information and
  never bearer tokens;
- the Source provider reference-dashboard tile uses the provider-summary attribute;
- Trade Republic remains `boot: auto`, while DKB remains experimental and
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

Live acceptance requires the existing private Trade Republic snapshot to join the
Comdirect + DKB portfolio as the third provider, producing **7/7** target coverage
with Robotics sourced from Trade Republic. After that healthy baseline is accepted,
a temporary Trade Republic outage must retain the complete 7/7 aggregate as
non-actionable Home Assistant LKG rather than recomputing a live 6/7 portfolio, and
restarting Trade Republic must recover automatically to healthy/live 7/7.
