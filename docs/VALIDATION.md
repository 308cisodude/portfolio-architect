# v1.25.0 validation

Portfolio Architect v1.25.0 retains the complete provider-App,
publication/privacy and runtime regression pipeline and adds focused Trade Republic
statement-import contracts. Validation must prove:

- all integration and three provider App package versions align with 1.25.0;
- the established Comdirect App remains stable under `portfolio_architect_gateway`;
- DKB remains an experimental, manual-only, fail-closed shell;
- Trade Republic remains independently isolated and gains only the provider-specific
  statement-import modules/dependency;
- the eight shared provider-neutral runtime files remain byte-identical to the
  canonical Gateway source while the two Trade Republic importer modules are not
  copied into Comdirect or DKB;
- a wholly synthetic text statement maps to canonical quantities, ISINs, names,
  instrument types, values and snapshot timestamp;
- a wholly synthetic PDF exercises the actual PDF extraction path without storing a
  public PDF fixture;
- encrypted/non-PDF/image-only/unsupported/ambiguous/internally inconsistent
  documents fail closed;
- position count and EUR portfolio total are cross-checked against the document
  summary;
- imported account-holder/depot attribution does not enter the normalized snapshot;
- multipart upload accepts only a bounded CSRF nonce plus one PDF document;
- the original uploaded PDF is never persisted by the importer;
- `pypdf` is exact-version/hash locked only for the Trade Republic App and CI;
- the release builder/verifier includes all three provider App ZIPs and the Trade
  Republic dependency file;
- protected workflows build all provider images and start DKB/TR containers;
- payload schema 8, REST schema 1, health schema 6, authorized-cash, LKG and
  actionability semantics remain unchanged;
- source, Git history and every built artifact pass the v1.22 privacy/Gitleaks gates;
  and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

A private real Trade Republic statement may be used during maintainer acceptance to
confirm the current layout, but it is never copied into the repository, generated
artifacts, CI fixtures, logs or release notes.
