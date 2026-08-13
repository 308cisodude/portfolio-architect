# v1.21.0 validation

Portfolio Architect v1.21.0 keeps the established publication-readiness pipeline and adds focused execution-semantics regression coverage.

Validation must prove:

- past scheduled execution dates remain schedule context and do not imply a transaction or automatic expiry;
- the new bounded actionability states distinguish schedule timing, execution readiness, and source actionability;
- `planned_execution` keeps its existing entity ID/unique ID while its display wording becomes **Scheduled execution**;
- the reference English/German dashboards expose scheduled execution, current actionability, and last evaluation separately;
- snapshot freshness wording explicitly describes the freshness window and retains the v1.20 boolean semantics;
- payload schema 8, REST schema 1, Gateway health schema 5, authorized-cash behavior, and LKG fail-closed behavior remain unchanged;
- the standalone Gateway and Home Assistant App packages remain version/source aligned;
- release archives are reproducible and pass ZIP/checksum/manifest verification.

Run the complete supported validation with:

```bash
./tools/release_check.sh
```

GitHub HACS and hassfest workflows remain the authoritative external Home Assistant/HACS validation on the reviewed immutable validator images.
