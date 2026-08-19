# v1.35.4 validation

Portfolio Architect v1.35.4 is prepared from the exact published v1.35.3 tracked-source baseline.
It is a narrow Comdirect Ingress amount-parsing and validation-UX hotfix. Cash-policy mathematics,
provider funding semantics, broker behavior, wire schemas and transport contracts are unchanged.

Required evidence:

- all integration/common Gateway/provider App version markers align at `1.35.4`;
- common Gateway and Comdirect App source mirrors remain byte-identical for `cash_policy.py` and
  `app.py`;
- both capped and retained cash forms accept decimal comma and decimal point;
- German/English grouped forms and supported space/apostrophe groupings normalize to the same
  canonical `Decimal` value;
- malformed/mixed separators, signs, exponent notation, extra fractional precision and other unsafe
  syntax fail closed before persistence;
- invalid cash amount input returns via the bounded relative Ingress error path rather than a generic
  browser HTTP 400 and does not reflect the rejected token;
- the previous valid private cash policy remains unchanged after rejected input;
- persisted schema-1/schema-2 cash-policy state remains strict/canonical and existing authorization
  math remains exact;
- the complete v1.35.2 retained-cash and v1.35.3 broker-menu regression sets remain green;
- the full regression suite remains green;
- Python compilation and all tracked JSON/YAML parsing pass;
- strict publication-readiness and source-privacy checks pass;
- three independent release builds are byte-identical;
- release verification, internal `SHA256SUMS` verification and artifact-privacy checks pass;
- the Git overlay and independent binary patch each reproduce the final tracked tree from the exact
  v1.35.3 baseline, including executable-bit semantics.

Local Docker availability is environment-dependent. Protected GitHub **Validate release** remains
authoritative for actual provider-App Docker/private-PKI smoke execution when local Docker is
unavailable.
