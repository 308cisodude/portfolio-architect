# Portfolio Architect 1.31.1

Version 1.31.1 is a narrow Home Assistant-side live-acceptance hotfix prepared from the
exact immutable v1.31.0 source baseline. It fixes the failure exposed immediately after
the v1.31 current-plan migration: a Trade Republic position can legitimately have an ISIN
without a WKN, but the Home Assistant payload parser still required every whole-portfolio
holding to carry a non-empty WKN.

## Live failure fixed

The v1.31 target migration correctly moves distributing Robotics
`IE00BYWZ0333` outside current plan scope while accumulating `IE00BYZK4552` / `A2ANH0`
becomes the active target. In the live multi-provider portfolio, the distributing holding
comes from Trade Republic and carries its canonical ISIN but no WKN.

The engine correctly preserved that provider-neutral identity as:

```text
position_id: holding_ie00bywz0333
wkn: ""
isin: IE00BYWZ0333
strategy_scope: outside_scope
```

Portfolio Architect's Home Assistant model then rejected the otherwise valid payload with
`holdings[13].wkn is invalid`, leaving the new configuration fingerprint without a usable
calculated payload.

Version 1.31.1 restores the established ISIN-first contract: a whole-portfolio holding may
omit WKN when a non-empty ISIN is present. Empty WKN placeholders do not participate in
duplicate-WKN detection, so multiple independent ISIN-only holdings remain representable
without inventing metadata. A holding with neither ISIN nor WKN still fails closed. Existing
duplicate non-empty WKN and duplicate ISIN checks remain unchanged.

## Exact regression topology

The new regression reproduces the live failure rather than testing only a synthetic parser
object. It combines a Comdirect portfolio with a Trade Republic-only distributing Robotics
position whose WKN is empty, aggregates sources by ISIN, calculates the v1.31 migrated plan,
and passes the complete resulting payload through the Home Assistant model parser.

The required result is:

- seven active targets, six held;
- accumulating Robotics remains the missing active target;
- distributing `IE00BYWZ0333` remains visible as `holding_ie00bywz0333`;
- that holding is `outside_scope`, retains its Trade Republic source provenance and empty WKN;
- accepted active exceptions remain zero; and
- no automatic sell behavior is introduced.

## Preserved boundaries

- v1.31 canonical Robotics target and superseded-exception history: unchanged
- broker schema 2 and provider-aware execution evidence: unchanged
- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- provider acquisition and aggregation: unchanged
- v1.27 private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery,
  DNS pinning and no-plaintext fallback: unchanged
- Comdirect OAuth/session maintenance: unchanged
- Trade Republic statement import/private snapshot behavior: unchanged; this release does not move PDF parsing into Portfolio Architect
- DKB v1.28 registration-gated anonymous FinTS capability probe: unchanged; DKB live Gateway acquisition remains a later authenticated milestone
- No trading, order, transfer, payment, or transaction-history capability is added
- no automatic sell capability is added

The historical `v1.19.0-rc2` experimental brokerage probe remains excluded and is not promoted by this release.

The three official Gateway Apps are version-aligned to 1.31.1 but contain no provider
runtime change for this hotfix.

See `docs/UPGRADE-1.31.1.md` and `docs/UPGRADE-1.31.0.md`.
