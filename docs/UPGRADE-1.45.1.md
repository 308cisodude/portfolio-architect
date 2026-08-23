# Upgrade to Portfolio Architect 1.45.1

Version 1.45.1 fixes the stale-legacy-source migration edge case discovered during live acceptance of v1.45.0. It does not change portfolio calculations, DKB CSV parsing, normal snapshot freshness policy, FinTS capability, or dashboard presentation.

## Upgrade order

1. Update the Portfolio Architect Home Assistant integration to **1.45.1** and restart Home Assistant once.
2. Update **Portfolio Architect Gateway — DKB** to **1.45.1**. Align Comdirect and Trade Republic Gateway Apps to 1.45.1 as normal package-version hygiene.
3. Restore the DKB Gateway's **Maximum cached snapshot age** to the normal intended value if it was temporarily widened for the v1.45.0 workaround. The default remains `604800` seconds (7 days).
4. Keep the legacy PA-side DKB CSV source configured until migration succeeds.
5. Import the exact legacy DKB CSV export currently configured in Portfolio Architect into the DKB Gateway. This remains the equivalence oracle even if it is older than the normal seven-day Gateway serving horizon.
6. Open the discovered **Migrate legacy DKB CSV to the DKB Gateway** flow and enter the DKB Gateway bearer token.
7. Portfolio Architect validates provider identity and health over verified HTTPS. If the snapshot is older than the normal serving-age limit, it uses the DKB-only authenticated migration endpoint for the exact comparison while `/api/v1/portfolio` remains unavailable.
8. Only exact canonical equality completes the atomic cut-over. Any failure leaves the legacy source configured.
9. After successful cut-over, import the current/fresh DKB depot CSV batch into the DKB Gateway.
10. Confirm DKB is represented only by `provider_id: dkb`, no double counting occurred, source freshness/provenance are correct, and normal `/api/v1/portfolio` operation is healthy again.

## Important security and freshness property

The migration endpoint does not make an expired snapshot operationally fresh. It is read-only, bearer-authenticated, private-CA protected, DKB-only, and returns only the canonical normalized snapshot for equivalence checking. Normal Portfolio Architect runtime continues to reject an expired DKB snapshot according to the configured Gateway age policy.

## No other migration

No dashboard replacement, broker configuration change, Comdirect reauthentication, Trade Republic re-import, or FinTS probe is required solely because of v1.45.1.
