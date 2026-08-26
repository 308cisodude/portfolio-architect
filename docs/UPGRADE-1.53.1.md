# Upgrade to Portfolio Architect v1.53.1

Version 1.53.1 is a correctness hotfix for the published v1.53.0 acquisition-control-plane release. Upgrade in place; do not delete Gateway App data or re-import provider documents merely because of this update.

The final release candidate also refreshes the exact Alpine 3.24 OpenSSL CLI package pin from `3.5.7-r0` to `3.5.8-r0` after repository rotation. This has no migration or operator action beyond installing the final v1.53.1 App packages.

## Required upgrade order

1. Update the Portfolio Architect Home Assistant integration to v1.53.1 and restart Home Assistant once.
2. Update the installed Comdirect, DKB and Trade Republic Gateway Apps to v1.53.1 in place. If Generic Import is installed for a real use case, align it as well; otherwise do not install it solely for this hotfix.
3. Preserve all App-private `/data` state, verified private-PKI trust material, provider tokens/sessions, selected accounts and staged/imported evidence.
4. Keep any temporary Trade Republic `max_cached_snapshot_age_seconds=1209600` workaround until the v1.53.1 Trade Republic App has been updated and restarted. After v1.53.1 is active, static PDF evidence is no longer expired by that setting; it may be returned to the new default `0` at convenience.

## Live acceptance

Start from healthy `comdirect=live_api`, `trade_republic=pdf`, `dkb=csv` with the normal evidence-kind freshness policy. Then:

1. Confirm the existing staged Comdirect holdings+cash CSV candidate remains `READY`.
2. Explicitly activate Comdirect CSV. Portfolio Architect must accept the same canonical `comdirect` provider even if the CSV holdings timestamp predates the previously accepted live-API snapshot. The source summary must change to `acquisition_mode: csv`, freshness must use the configured CSV threshold, HA LKG must remain inactive, and `Source unavailable` must not render `None`.
3. Explicitly return to Comdirect live API. Activation must perform a real live provider read. If Comdirect requires PhotoTAN, reauthenticate while CSV remains active, then retry; failed activation must leave CSV authoritative. A successful return must produce a fresh `live_api` snapshot.
4. Confirm Trade Republic continues serving its currently accepted statement without requiring re-import merely because its historical Gateway cache-age value was shorter than PA's configured imported-statement freshness threshold.
5. Confirm DKB CSV and, if installed, Generic Import CSV likewise remain servable according to PA freshness rather than a separate static Gateway TTL.
6. Confirm supplemental snapshot unavailability, if naturally encountered, reports `snapshot_unavailable`/source unavailable rather than a snapshot-integrity failure; do not deliberately corrupt production state to force this path.

No dashboard replacement or config-entry migration is required.

## Generic Import isolation

Generic Import remains experimental. If it is not already installed for a real mapped-CSV use case, do **not** add its discovery card/source to the production Portfolio Architect config entry solely for v1.53.1 acceptance. Any standalone synthetic Generic Import smoke test must not alter the real production portfolio or configured provider set, and the temporary App should be uninstalled after this standalone smoke test.
