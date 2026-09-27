# Portfolio Architect v1.65.8 — bounded FinTS system-ID storage

The live v1.65.7 read reported `capture reason non_alphanumeric`. PyFinTS models the bank's HISYN customer system ID as a string with a 30-character bound; PA's ASCII-only storage gate was narrower. This release accepts nonempty, printable IDs of up to 30 characters other than the `0` sentinel. It serializes them as escaped JSON in the existing mode-0600 App-private, backup-excluded file and computes the existing keyed fingerprint over UTF-8 bytes. Control characters remain rejected. The diagnostic reason for a rejected printable-bound failure is now `non_printable`.

This is an offline correction, not proof that DKB will return a reusable ID or waive approval after an App restart. The 72-hour fixed expiry, product/user binding, manual read-only flow and five-minute detailed cash review remain. DKB CSV cash is still the planning authority; FinTS observations do not feed the planner.
