# Upgrade to Portfolio Architect 1.54.0

Version 1.54.0 is a non-schema Gateway UX and release-engineering cleanup on top of the fully live-accepted 1.53.1 baseline.

## Before upgrading

- Keep the existing Portfolio Architect source configuration and Gateway private data volumes.
- Do not re-import static evidence or reauthenticate Comdirect solely for this release.
- No dashboard replacement is required.

## Recommended order

1. Update Portfolio Architect through HACS to 1.54.0 and restart Home Assistant once.
2. Update the installed Comdirect, Trade Republic and DKB Gateway Apps in place to 1.54.0. Update Generic Import too if it is installed.
   If Generic Import is not already intentionally configured, do **not** add its discovery card/source merely to test this release; it remains experimental and the production source set does not need it. Any isolated Generic Import smoke test must not alter the real production source set or broker configuration; if installed only for this standalone smoke test, it should be uninstalled after this standalone smoke test.
3. Confirm all installed Apps report 1.54.0 and all configured verified-HTTPS sources remain healthy.
4. Open each Gateway Ingress page and verify ACTIVE/authoritative acquisition is green. A ready but inactive Comdirect alternative is blue; unavailable/not-ready/research-only acquisition is amber.
5. In Home Assistant App configuration, confirm Trade Republic, DKB and Generic Import no longer present a Gateway cache/freshness-age option. Their static evidence freshness remains owned by Portfolio Architect.
6. In Comdirect configuration, confirm the retained option is labelled `Maximum live LKG snapshot age`; the Live API Ingress section must describe it as a resilience limit rather than a planning-freshness threshold.

## Existing static-App option state

Older installations may still have `max_cached_snapshot_age_seconds` present in Supervisor-managed saved options. v1.54.0 deliberately keeps a bounded parser compatibility bridge so that stale saved state cannot prevent an in-place upgrade. The value is ignored for active static CSV/PDF evidence and is no longer exposed by the v1.54.0 static-App schema. Portfolio Architect remains authoritative for evidence freshness.

## Runtime-package build policy

All provider Dockerfiles continue to use the exact digest-pinned Python 3.14.6 / Alpine 3.24 base image. The OpenSSL CLI is now installed from the current package set of that pinned Alpine branch instead of exact-pinning an APK revision. Protected GitHub validation/publication builds enforce OpenSSL >= 3.5.8 and record the resolved version in their build evidence.

## Rollback

An in-place rollback to 1.53.1 does not require source or broker configuration changes. Static evidence timestamps and provider-private state are unchanged by this release.
