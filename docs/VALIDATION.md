# v1.27.3 validation

Portfolio Architect v1.27.3 retains the complete v1.27.2 verified-HTTPS migration,
v1.27.1 release-workflow parity, v1.26.7 cold-restart integrity, v1.26 multi-provider
atomic-LKG, publication/privacy and reproducible-release regression pipeline while
adding an executable DKB Gateway-vs-CSV identity collision contract.

Release-specific validation must prove:

- integration and all three official provider App package versions align with
  1.27.3;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- DKB Gateway provider identity is exactly `dkb`, matching the official DKB App
  environment;
- DKB CSV source identity remains exactly `dkb_csv`;
- the two identities are deliberately distinct and never compared as if they shared
  one namespace;
- a real `dkb` Gateway discovery conflicts with configured DKB CSV scope and is
  suppressed before Home Assistant can present a supplemental-provider Add card;
- the same DKB CSV collision rule is applied during discovered supplemental
  confirmation and manual REST Gateway addition;
- Trade Republic/Comdirect discovery and already-configured REST Gateway migration
  behavior remain unchanged;
- manifest-level `single_config_entry` remains absent while manual setup explicitly
  enforces the single Portfolio Architect config-entry invariant;
- v1.27 private-PKI, hostname verification, private-CA-only trust, DNS pinning,
  bearer authentication, verified-HTTPS-before-write migration, changed-trust
  refusal and no-plaintext-fallback contracts remain green;
- v1.27.1 validate/release provider-shell smoke-test parity remains green;
- v1.26.7 quantity/cache/HTTP-validator and v1.26.6 unavailable-source contracts
  remain green;
- Comdirect acquisition/authentication, Trade Republic statement import and DKB
  fail-closed shell behavior remain unchanged;
- source and release artifacts pass publication/privacy gates; and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

Live acceptance starts from the live-proven v1.27.2 installation: Comdirect and Trade
Republic are already `verified_https`, Home Assistant LKG is inactive, and one pending
Portfolio Architect discovery card remains because the DKB Gateway discovery was not
suppressed despite configured DKB CSV scope. Update only the Home Assistant integration
to v1.27.3 and restart Home Assistant. The pending discovery card must disappear while
Comdirect and Trade Republic remain healthy over verified HTTPS with unchanged CA
fingerprints. Then align installed Gateway App package versions to 1.27.3 in place;
that package alignment must not rotate private CA trust.
