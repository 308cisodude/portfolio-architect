# Portfolio Architect 1.28.0

Version 1.28.0 opens the DKB acquisition track with a deliberately constrained
**FinTS capability-probe milestone**. It does not claim or enable live DKB holdings.

## Registration-gated anonymous DKB FinTS probe

The experimental manual-only DKB Gateway can now perform one fixed-endpoint,
anonymous FinTS 3.0 BPD capability probe after the project has configured its own
FinTS product registration number.

The probe sends only dialog-initialization segments and reduces the response to
bounded capability metadata. The raw FinTS response is discarded. The principal
research signal is whether bank parameters advertise `HIWPDS`, the parameter segment
associated with the read-only securities-holdings transaction family.

The product registration number is App-private state. Version 1.28.0 requests no DKB
login name, PIN or TAN, performs no authenticated UPD request and publishes no DKB
portfolio snapshot.

## Security decomposition

This release deliberately separates three questions that must not be conflated:

1. **Can Portfolio Architect identify itself as a legitimately registered FinTS
   product?** v1.28.0 requires that gate first.
2. **Does DKB's bank-level BPD advertise a suitable read-only securities capability?**
   v1.28.0 can answer only this question.
3. **Does an authenticated user's UPD actually permit that capability, and can DKB-App
   decoupled authentication be implemented safely?** This remains a later gate.

A positive BPD result therefore never turns the DKB Gateway into a live source.

The probe uses a fixed verified-HTTPS DKB endpoint, bounded request/response handling,
FinTS-aware segment splitting, no ambient proxy/redirect surface, and no external
FinTS runtime dependency. No trading/order/transfer/payment/debit/transaction-history
operation is added.

## Provider isolation and compatibility

- Portfolio payload schema 8: unchanged.
- REST portfolio schema 1: unchanged.
- Gateway health schema 6: unchanged; schemas 1–5 remain supported where previously supported.
- v1.27 private-PKI, hostname-verified HTTPS, bearer authentication, DNS pinning,
  trust migration and no-plaintext-fallback behavior: unchanged.
- Comdirect v1.27.4 provider-specific OAuth/session maintenance: unchanged.
- Comdirect account selection, authorized cash and provider acquisition: unchanged.
- Trade Republic local statement import: unchanged; this release does not move PDF parsing into Portfolio Architect.
- DKB Gateway identity remains `dkb`; DKB CSV remains `dkb_csv`.
- DKB remains experimental/manual-only and is not added as an active portfolio
  source by this release.
- DKB live Gateway acquisition remains a later provider-specific milestone after product registration and authenticated user-capability validation.
- Portfolio calculation, multi-source atomicity, LKG behavior, entity identities and
  dashboard behavior: unchanged.
- No trading, order, transfer, payment, or transaction-history capability is added.
- The historical experimental `v1.19.0-rc2` brokerage diagnostics/fee-probe work remains separate and is not promoted by this release.

See `docs/UPGRADE-1.28.0.md` for the registration and capability-probe acceptance
path. No dashboard YAML migration is required.
