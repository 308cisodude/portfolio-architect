# v1.24.1 validation

Portfolio Architect v1.24.1 retains the complete v1.24 provider-App, publication/privacy and runtime regression pipeline and adds explicit startup validation for the reduced DKB/TR packages. Validation must prove:

- all integration and three provider App package versions align with 1.24.1;
- the established Comdirect App remains stable under `portfolio_architect_gateway`;
- DKB/TR remain experimental, manual-only and independently isolated;
- the DKB/TR package runtime subset contains no `config.py`, Comdirect client, transport or authentication implementation;
- the common `server.py` imports `GatewayConfig` only under `TYPE_CHECKING` and uses `ServerConfig` at runtime;
- `pending_app` imports successfully from each exact reduced shell source tree;
- each DKB/TR Dockerfile imports the real startup module during build;
- protected GitHub validation starts both built shell containers, requires them to remain running and verifies listeners on ports 8099 and 8787;
- provider-shell acquisition still fails closed without fabricating a snapshot;
- release builder/verifier still emits and validates all three provider App archives;
- all physical App runtime copies remain byte-identical to their canonical Gateway source files;
- payload schema 8, REST schema 1, health schema 6, authorized-cash, LKG and actionability semantics remain unchanged;
- source, Git history and every built artifact pass the v1.22 privacy/Gitleaks gates; and
- release archives remain reproducible and pass checksum, manifest, ZIP path and payload-alignment verification.
