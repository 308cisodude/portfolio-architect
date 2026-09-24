# Portfolio Architect v1.64.3 — DKB HKWPD account conversion

The first live v1.64.2 read-only holdings observation reported `eligible depots: 1`, `failure stage: holdings_request`, `failure category: type_error`, and no bank return codes after approved login. Inspection of pinned PyFinTS 5.0.0 found a deterministic local cause consistent with that observation: its HKWPD5/6 account conversion indexes the BIC to derive the bank country, while v1.64.2 passed `None` because PyFinTS `get_information()` does not expose a BIC. Both conversions raise `TypeError` before constructing the HKWPD request.

For the fixed DKB endpoint, this release supplies DKB's published BIC `BYLADEM1001` after checking that the one eligible UPD depot has the expected DKB bank code `12030000`. PyFinTS's HKWPD5/6 conversion uses the BIC for country derivation; the command account fields contain the UPD account number and bank identifier. The BIC is public bank metadata, not a user account identifier. Source: https://www.dkb.de/ueber-uns/impressum

This removes the demonstrated local conversion failure, but the previous live observation cannot prove that it was the only possible failure. One new live observation is required. v1.64.2's bounded failure diagnostics remain available. DKB CSV stays the sole authoritative holdings/cash source; no planner, acquisition, fallback, wire or dashboard changes occur.
