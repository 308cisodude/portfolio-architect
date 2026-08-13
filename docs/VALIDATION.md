# v1.24.0 validation

Portfolio Architect v1.24.0 retains the complete publication/privacy and runtime regression pipeline and adds distinct-provider-App packaging/isolation contracts. Validation must prove:

- three unique App slugs exist and all package versions align with 1.24.0;
- the established Comdirect App remains stable and retains `portfolio_architect_gateway`;
- DKB/TR are experimental, manual-only, least-privilege and independently isolated;
- the DKB/TR source packages contain only the audited provider-neutral runtime subset and no Comdirect client/transport implementation;
- provider-shell portfolio acquisition fails closed and its Ingress API is read-only;
- `GatewayState` and `create_server()` depend only on provider-neutral `ServerConfig`;
- the release builder emits and verifier requires three distinct Gateway App ZIPs;
- all physical App runtime copies remain byte-identical to the canonical Gateway source files;
- payload schema 8, REST schema 1, health schema 6, authorized-cash, LKG and actionability semantics remain unchanged;
- source, Git history and every built artifact pass the v1.22 privacy/Gitleaks gates; and
- release archives remain reproducible and pass checksum, manifest, ZIP path and payload-alignment verification.

Run the supported validation with `./tools/release_check.sh`. Protected GitHub Validate release, HACS and hassfest jobs remain mandatory before merge/tagging.

Protected GitHub validation and immutable release each build all three provider App Docker contexts for amd64 without publishing images.
