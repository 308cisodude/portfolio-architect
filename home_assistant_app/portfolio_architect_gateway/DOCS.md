# Portfolio Architect Gateway — Comdirect v1.26.7

Version 1.26.7 fixes the common Gateway cold-restart snapshot-integrity edge case by preserving optional position quantity through cached-snapshot reload and by giving ETag validation precedence over date validation. Comdirect acquisition, OAuth/session, PhotoTAN, refresh cadence, account selection, authorized cash, REST schema 1 and health schema 6 are unchanged.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
