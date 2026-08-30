# Portfolio Architect Gateway — Comdirect v1.60.0

Version 1.60.0 adds read-only authoritative capability-evidence availability and UTC timestamps to the existing Acquisition authority cards. The evidence clocks come only from the canonical snapshot of the explicitly active method; prepared inactive CSV evidence is deliberately excluded. Existing explicit Comdirect live API/CSV activation and `fallback_policy: none` are unchanged.
