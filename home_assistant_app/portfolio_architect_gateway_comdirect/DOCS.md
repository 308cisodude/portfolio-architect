# Portfolio Architect Gateway — Comdirect v1.61.0

Version 1.61.0 is package alignment for Portfolio Architect's Home Assistant-side Configure removal-confirmation UX. Comdirect acquisition, health schema 9, canonical evidence clocks, private-PKI transport and no-fallback behavior are unchanged from v1.60.0.

Version 1.60.0 adds read-only authoritative capability-evidence availability and UTC timestamps to the existing Acquisition authority cards. The evidence clocks come only from the canonical snapshot of the explicitly active method; prepared inactive CSV evidence is deliberately excluded. Existing explicit Comdirect live API/CSV activation and `fallback_policy: none` are unchanged.
