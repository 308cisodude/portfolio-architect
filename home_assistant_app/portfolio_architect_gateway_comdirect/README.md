# Portfolio Architect Gateway — Comdirect v1.56.1

Version 1.56.1 fixes the post-cut-over restart lifecycle for migrated installations. OAuth/session state remains forbidden during migration and before the first canonical startup, but a fresh session created later by the canonical runtime after PhotoTAN bootstrap is accepted on restart when the preserved private-PKI leaf genuinely validates for this exact provider-qualified hostname. Same-CA trust, bearer preservation, explicit cut-over and acquisition behavior are unchanged.
