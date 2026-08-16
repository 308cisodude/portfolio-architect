# v1.28.0 validation

Portfolio Architect v1.28.0 retains the complete v1.27 verified-HTTPS/private-PKI,
v1.27.4 Comdirect session-maintenance, v1.27.3 DKB discovery suppression, v1.26.7
cold-restart integrity, multi-provider atomic-LKG, publication/privacy and
reproducible-release regression pipeline while adding a registration-gated DKB FinTS
capability probe.

Release-specific validation must prove:

- integration and all three official provider App package versions align with
  `1.28.0`;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- DKB App remains experimental and `manual_only` with provider identity `dkb`;
- the anonymous FinTS request contains only `HNHBK`, `HKIDN`, `HKVVB` and `HNHBS`;
- the request uses the fixed DKB FinTS HTTPS endpoint/bank code and the configured
  Portfolio Architect product registration number;
- product registration input is strictly bounded and stored only in App-private
  mode-`0600` state;
- v1.28.0 contains no DKB login/PIN/TAN form and performs no authenticated UPD or
  holdings request;
- synthetic FinTS BPD responses are reduced to bounded parameter-segment identifiers,
  return codes, BPD version, timestamp and `HIWPDS` presence while raw payload data is
  discarded;
- malformed/unbounded FinTS envelopes, segment counts, binary fields and response
  sizes fail closed;
- the DKB probe transport uses normal TLS/hostname verification against the fixed
  endpoint without a user-configurable URL, ambient proxy handler or redirect path;
- the DKB provider REST snapshot remains unavailable through `PendingProvider` and no
  portfolio refresh loop is started;
- no external FinTS runtime dependency or broad write-capable banking API is added;
- common Gateway runtime files remain byte-identical across provider packages;
- `dkb` versus `dkb_csv` discovery/scope collision behavior remains green;
- v1.27.4 Comdirect provider-specific session-maintenance contracts remain green;
- v1.27 HTTPS/trust/downgrade-resistance contracts remain green;
- Trade Republic statement import remains green;
- source and release artifacts pass publication/privacy gates; and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

## Live acceptance

General release acceptance starts from live-accepted v1.27.4:

1. update the integration and all installed official Gateway Apps in place;
2. restart Home Assistant once to load the 1.28.0 integration;
3. verify existing Comdirect/Trade Republic sources remain healthy and their
   verified-HTTPS CA fingerprints are unchanged;
4. verify Comdirect retains its provider-specific session-maintenance behavior;
5. verify the DKB App still does not become an active portfolio source.

The new DKB capability probe has a separate external prerequisite: Portfolio
Architect's own FinTS product registration number. Until that registration is issued,
`registration_required` is the expected DKB probe state and does not block release
publication.

After registration is available, first-probe acceptance is successful when the
admin-only DKB Web UI can execute the bounded anonymous BPD probe and report only the
sanitized capability fields documented in `docs/UPGRADE-1.28.0.md`. Whether `HIWPDS`
is present is research evidence for the next gate, not a pass/fail criterion for the
safety of v1.28.0 itself.

No dashboard YAML migration is required.
