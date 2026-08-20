# v1.37.0 validation

Portfolio Architect v1.37.0 is prepared from the exact published and live-accepted v1.36.1 tracked-source baseline. The release is an infrastructure milestone: reusable human-numeric parsing is centralized in a mirrored Gateway helper, while only the existing Comdirect cash-policy amount fields opt in for this release.

## Required evidence

Release-specific validation must prove:

- all integration/common Gateway/provider App version markers align to 1.37.0;
- the shared `human_input.py` helper is byte-identical across the common Gateway and all three provider App build contexts;
- EUR, percentage, quantity and bounded-integer primitives apply bounded syntax/type/range validation;
- rejected human input never echoes the rejected raw token and overlong/unsafe syntax is rejected;
- quantity syntax that is ambiguous across decimal/grouping conventions is rejected rather than guessed;
- Comdirect capped/retained cash fields preserve every live-proven v1.35.4 locale form while using the shared EUR primitive;
- invalid Comdirect amount input still leaves the previous private policy unchanged;
- DKB FinTS registration and Trade Republic statement import do not opt into human-numeric normalization;
- common Gateway and Comdirect App source mirrors remain byte-identical for `app.py`, `cash_policy.py`, `human_input.py` and `transport.py`;
- all established publication/privacy, provider, presentation, wire-schema, private-PKI and advisory/no-trading regressions remain green.

The complete release gate remains `tools/release_check.sh`. Local preparation environments without Docker must run every available constituent phase independently; the protected GitHub **Validate release** workflow remains authoritative for provider-App Docker/Supervisor/private-PKI smoke execution.
