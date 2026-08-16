# v1.27.4 validation

Portfolio Architect v1.27.4 retains the complete v1.27 verified-HTTPS/private-PKI,
v1.27.3 DKB discovery suppression, v1.26.7 cold-restart integrity, v1.26
multi-provider atomic-LKG, publication/privacy and reproducible-release regression
pipeline while correcting Comdirect OAuth session scheduling.

Release-specific validation must prove:

- integration and all three official provider App package versions align with
  1.27.4;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- Comdirect session maintenance runs on a provider-owned five-minute cadence that is
  independent of the portfolio refresh cadence;
- session maintenance performs no depot, position, instrument, balance, transaction,
  order, payment, or transfer request;
- a simulated 10-minute access-token / 20-minute refresh-session timing window fails
  under the reproduced adverse 15-minute portfolio phase without maintenance but
  survives when the five-minute maintenance path is active;
- a conclusively rejected refresh session is latched locally until interactive
  bootstrap succeeds so repeated scheduled loops do not re-submit the rejected token;
- bounded reauthentication logging retains only machine reason/status classification
  and never remote response bodies or credentials;
- the common provider-neutral Gateway contract contains no Comdirect/OAuth session
  semantics;
- v1.27 private-PKI, hostname verification, private-CA-only trust, DNS pinning,
  bearer authentication, verified-HTTPS-before-write migration, changed-trust
  refusal and no-plaintext-fallback contracts remain green;
- v1.27.3 DKB Gateway-vs-CSV discovery suppression remains green;
- v1.27.1 validate/release provider-shell smoke-test parity remains green;
- v1.26.7 quantity/cache/HTTP-validator and v1.26.6 unavailable-source contracts
  remain green;
- Trade Republic statement import and DKB fail-closed shell behavior remain
  unchanged;
- source and release artifacts pass publication/privacy gates; and
- release archives remain reproducible and pass checksum, manifest, path-safety and
  payload-alignment verification.

`AI_POLICY.md` must also retain the existing human-controlled publication policy and
now describe the separate security-focused AI second-opinion review as
non-authoritative defense-in-depth evidence rather than certification.

## Live acceptance

Start from the live v1.27.3 installation with verified HTTPS already established.
Update Portfolio Architect and the Comdirect Gateway App in place. Do not remove App
private data and do not reauthenticate solely because of the upgrade when the current
session is healthy.

Acceptance is successful when:

1. Comdirect remains or returns `status: ok`, `operating_mode: live`, and snapshot
   integrity remains verified;
2. the Gateway log records successful provider-specific OAuth maintenance at least
   once without a portfolio refresh being required for that renewal;
3. several subsequent 15-minute portfolio refreshes remain live across more than one
   short OAuth lifetime without `reauthentication_required` caused by scheduler phase;
4. verified-HTTPS CA fingerprints remain unchanged; and
5. Trade Republic and DKB behavior remain unchanged after optional package alignment.

No dashboard YAML migration is required.
