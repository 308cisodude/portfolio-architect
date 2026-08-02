# Supported versions

## Portfolio Architect

The current stable release and the immediately preceding stable release receive
security and correctness fixes while a documented upgrade path exists. Older
releases may continue to work but are not actively supported.

## Home Assistant

The 1.17.x release line requires Home Assistant 2026.7.0 or newer. CI validates
project tests on Python 3.14, HACS metadata, and the deliberately pinned hassfest
validator snapshot. The project targets the current and immediately previous
monthly Home Assistant release.

Scheduled HACS and hassfest workflows re-run the reviewed immutable validator
images. They do not silently adopt upstream image changes. Maintainers must review
and update those digests deliberately when validating against a newer upstream
snapshot.

## Gateway compatibility

Portfolio Architect 1.17.2 accepts the established REST portfolio schema 1 and
Gateway health schemas 1 through 5. Gateway App 1.16.1 and later remain supported
when release notes state that the Gateway protocol is unchanged.

## Security fixes

A release that repairs a security vulnerability will document the affected
versions and remediation path in the corresponding security advisory. Users
should not rely on an unsupported release merely because it still starts.
