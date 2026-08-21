# Portfolio Architect Gateway — Trade Republic v1.40.1

Version 1.40.1 is package alignment for Portfolio Architect's Home Assistant-side evidence-backed advisory funding-transfer modelling. The live-accepted v1.38.1 signed drift and v1.38.0 cash/ISIN work remain Home Assistant-side, and the v1.37 shared human-input helper remains present but unused by the Trade Republic statement-import path. Statement import/private diagnostics are unchanged and no cash or transaction-history acquisition is added.

Verified HTTPS/private CA trust, bearer
authentication, REST schema 1, health schema 6 and accepted snapshot serving are unchanged.

Upgrade in place to retain App-private TLS state and the accepted provider snapshot. No
statement re-import is required merely because of the upgrade.
