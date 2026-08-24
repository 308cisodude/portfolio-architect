# Upgrade to Portfolio Architect 1.48.0

Version 1.48.0 adds complete explicit Comdirect CSV acquisition inside **Portfolio Architect Gateway — Comdirect** and visually separates live/static acquisition in all provider Apps.

## Normal upgrade from the live-accepted v1.47.0 installation

1. Update the Portfolio Architect Home Assistant integration to **1.48.0** and restart Home Assistant once.
2. Update **Portfolio Architect Gateway — Comdirect** to **1.48.0** in place. Preserve `/data/gateway`; do not reauthenticate solely because of the release.
3. Align the DKB and Trade Republic Gateway Apps to **1.48.0** in place.
4. Open the Comdirect Ingress UI. Confirm **Live acquisition · Comdirect API** is marked ACTIVE and **Static acquisition · Comdirect CSV** is INACTIVE.
5. Confirm normal Comdirect live holdings, authorized investment cash and OAuth/session maintenance remain healthy. Do not import CSVs merely to perform the normal upgrade.
6. Confirm DKB and Trade Republic keep their existing accepted provider state; their acquisition semantics do not change.
7. No dashboard YAML replacement is required.

## Optional Comdirect static CSV mode

To operate Comdirect deliberately without automatic API acquisition:

1. While still in `live_api`, import a current supported Comdirect depot CSV in the static card. This only stages holdings.
2. Optionally import a supported Comdirect Girokonto transaction CSV containing exactly one explicit `Alter Kontostand` opening balance and one explicit `Neuer Kontostand` closing/current balance. The bounded parser validates transaction dates/amounts and requires opening balance plus transaction deltas to reconcile exactly to the closing balance; it never invents cash when those explicit invariants are absent.
3. Verify the static card shows the expected staged evidence timestamps.
4. Select **Activate static CSV mode**. The Gateway validates the static snapshot before persisting the mode change.
5. Confirm health schema 7 reports `provider_id: comdirect` and `acquisition_mode: csv` and Portfolio Architect remains healthy.
6. Confirm automatic Comdirect portfolio acquisition and OAuth/session maintenance stop. API failures cannot cause CSV fallback because there are no automatic API calls in this mode.
7. Re-import holdings and cash independently whenever new static evidence is required. Updating one does not refresh the other.

Switching back to `live_api` is also explicit. The Gateway validates a real live API snapshot before committing the switch. An explicit PhotoTAN bootstrap may be prepared while CSV remains active, but it does not switch acquisition mode.

## Legacy Home Assistant-side Comdirect CSV migration

If an installation still uses the old PA-side `comdirect_csv` primary source, **do not remove it manually first**.

1. Update the integration and Comdirect Gateway to 1.48.0.
2. Import the same current Comdirect depot CSV into the Comdirect Gateway and explicitly activate `csv` mode.
3. Return to Home Assistant and use the discovered Comdirect Gateway migration flow.
4. Enter the existing Gateway bearer token.
5. Portfolio Architect verifies private-CA HTTPS, provider identity, health schema 7, explicit CSV mode, snapshot integrity and exact canonical holdings equivalence against the still-configured legacy CSV.
6. Only an exact match atomically replaces the legacy local source with the verified-HTTPS Gateway. Any mismatch leaves the existing configuration untouched.

The legacy file mtime is not a bank-issued timestamp and is intentionally excluded from equivalence. The new Gateway evidence timestamp is the explicit import time.

## Privacy and fail-closed rules

Raw Comdirect CSV documents, filenames, depot/account identifiers and transaction contents remain transient. Static cash requires an explicit balance and never infers overdraft/credit. `live_api` never silently falls back to CSV, and `csv` never silently falls back to the API.
