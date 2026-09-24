# Portfolio Architect v1.64.0 — DKB FinTS user-capability research

This release adds a one-shot authenticated dialog to the DKB Gateway's existing research panel. The user enters the DKB FinTS identifier and PIN through admin Ingress for one observation, including a DKB app confirmation or login TAN if required. The App does not persist either credential, system-ID cache, raw UPD, account identifiers, bank challenge, or response payload. PyFinTS 5.0.0 and its transitive packages are pinned with SHA-256 hashes for both supported Alpine architectures.

The observation records only the authenticated outcome (`authenticated`, `authentication_failed`, `sca_required`, `approval_pending`, or `approval_expired`), UPD received/version, account-level securities capability (`yes`, `no`, or `unknown`), numeric authentication-method identifier, UTC timestamp, and up to 32 four-digit return codes. A required DKB app confirmation or login TAN is handled in a transient five-minute dialog; failed or expired approval remains inconclusive. A missing UPD or account record produces `unknown`.

The anonymous BPD evidence remains independent. A sanitized fixture records the earlier BPD 29 / HIWPDS advertised / 0010 observation. No raw bank response or user data is included.

DKB CSV holdings and Girokonto cash remain authoritative. FinTS is `research_only` and cannot be selected as an acquisition method. No holdings, balance, transaction, order, transfer or payment command is implemented. HKTAN is used only to complete the login challenge. The Portfolio Architect planner, provider-neutral contracts, REST and health schemas, security boundary, source arbitration and other provider Apps are unchanged. Conflict normalization is deferred to v1.65.0; Tactical Tilt and Trade Republic combined-CSV reconciliation remain outside this release.

## Validation and live checkpoint

1. Install integration and four aligned Gateway Apps; verify existing DKB CSV holdings and cash timestamps and acquisition authority remain intact.
2. In DKB admin Ingress, inspect the anonymous fixture/reference evidence and perform one authenticated capability observation using your own credentials. Complete the DKB app confirmation or login TAN when requested, then check the bounded UPD result.
3. Verify no identifier, PIN, account/UPD payload or bank challenge appears in App logs, status, HA diagnostics or stored observation. No real-bank authenticated test is run during offline preparation.
