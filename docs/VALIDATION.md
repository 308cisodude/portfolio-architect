# v1.23.0 validation

Portfolio Architect v1.23.0 retains the complete publication/privacy and runtime
regression pipeline and adds provider-boundary and health-schema-6 contracts.

Validation must prove:

- the common Gateway server depends on `PortfolioProvider`, not `ComdirectClient`;
- the current Comdirect client implements the provider identity, refresh cadence
  and provider-neutral snapshot contract;
- health schema 6 adds only a bounded `provider_id` and schemas 1–5 remain
  negotiable for backward compatibility;
- the Home Assistant REST client parses schema 6 strictly and advertises older
  health media types as fallbacks;
- Gateway status attributes/diagnostics expose provider identity without account,
  depot, IBAN or credential material;
- the existing Comdirect App slug and private data paths remain stable while its
  visible name becomes provider-specific;
- DKB and Trade Republic App names/slugs are architecture reservations only and
  no unsupported acquisition capability is published;
- payload schema 8, REST portfolio schema 1, authorized-cash, LKG and v1.21
  actionability semantics remain unchanged;
- source, Git history and built artifacts still pass the v1.22 fail-closed privacy
  controls and immutable Gitleaks publication gate; and
- release archives remain reproducible and pass checksum, manifest, ZIP path and
  payload-alignment verification.

Run the complete supported local validation with:

```bash
./tools/release_check.sh
```

Protected GitHub Validate release, HACS and hassfest jobs remain mandatory before
merge/tagging.
