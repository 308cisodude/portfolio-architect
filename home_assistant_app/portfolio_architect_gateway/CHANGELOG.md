# Changelog

## 1.26.3

- Version alignment for Portfolio Architect 1.26.3.
- No Comdirect acquisition, authentication, authorized-cash or REST contract change; v1.26.3 is Home Assistant dashboard/presentation polish.

## 1.26.2

- Version alignment for Portfolio Architect 1.26.2.
- No Comdirect acquisition, authentication, authorized-cash or REST contract change; v1.26.2 is Home Assistant presentation/diagnostic polish.

## 1.26.1

- Version alignment for Portfolio Architect 1.26.1.
- No Comdirect acquisition, authentication, authorized-cash or REST contract change; the ISIN-first hotfix is Home Assistant-side.

## 1.26.0

- Version alignment for Portfolio Architect 1.26.0.
- No Comdirect acquisition, authentication, cash-policy or REST contract change.

## 1.25.0

- Version alignment for Portfolio Architect 1.25.0; Comdirect OAuth, account selection, authorized-cash behavior and REST contracts are unchanged.
- Trade Republic statement parsing remains isolated in the separate Trade Republic App and is not included in this image.

## 1.24.1

- Aligns the Comdirect App package with the v1.24.1 provider-shell startup hotfix.
- Keeps the established Comdirect runtime, slug, credentials/session state, selected account, cash policy, API token and cached snapshot unchanged.
- Uses the provider-neutral common server with the Comdirect configuration import restricted to type checking only.

## 1.24.0

- Renames the visible App to **Portfolio Architect Gateway — Comdirect** while retaining the existing slug and private App data.
- Implements the provider-neutral Gateway runtime contract through the existing Comdirect client.
- Adds health schema 6 with bounded `provider_id: comdirect`; health schemas 1–5 remain available.
- Preserves Comdirect OAuth/session state, account selection, cash authorization, REST schema 1, GET-only behavior, and cached-snapshot recovery semantics.

## 1.22.0

- Aligns Gateway App package metadata with Portfolio Architect v1.22.0 publication/privacy hardening.
- Keeps Gateway banking runtime behavior, REST portfolio schema 1, and health schema 5 unchanged from v1.20.1.
- Adds no provider capability, authentication change, trading path, or transaction-history behavior.

## 1.21.0

- Aligns Gateway App package metadata with Portfolio Architect v1.21.0.
- Keeps Gateway banking runtime behavior, REST portfolio schema 1, and health schema 5 unchanged from v1.20.1.
- Execution scheduling/actionability semantics remain Home Assistant integration concerns; no trading or transaction capability is added.

## 1.20.1

- Aligns Gateway App package metadata with Portfolio Architect v1.20.1.
- Keeps Gateway runtime and REST/health contracts unchanged from v1.20.0.
- Adds release regression coverage confirming cached snapshot integrity metadata remains available while Comdirect reauthentication is required.

## 1.20.0

- Aligns Gateway App package metadata with Portfolio Architect v1.20.0 graceful degradation and trustworthy freshness handling.
- Preserves the v1.19.1 Gateway runtime, authenticated REST schema 1, health schema 5, OAuth/session state, account selection, and authorized-cash policy behavior.
- Requires no new account selection or PhotoTAN solely because of this package update.

## 1.19.1

- Fixes switching Investment cash authorization from **Cap eligible cash** back to **All eligible cash** when the previous cap remains in the submitted form.
- Canonicalizes `all_available` server-side to a policy with no cap, while retaining strict validation of persisted policy files.
- Clears and disables the cap control in the Ingress UI outside capped mode as a usability aid only; server-side validation remains authoritative.
- Preserves the read-only Gateway surface, cash calculations, REST/health schemas, authentication state, and App-private policy storage.

## 1.19.0

- Adds an admin-only Ingress policy for authorizing all eligible investment cash or capping it at a configured EUR amount.
- Keeps booked account balance, eligible cash, authorized cash, policy, and optional cap semantically distinct.
- Publishes additive provider-neutral `investment_cash` metadata while preserving the legacy reserve field as the authorized amount.
- Stores non-secret policy state atomically in App-private data and rejects malformed capped policies.
- Adds no trading, transfer, payment, or transaction-history operation.

## 1.18.2

- Aligns Gateway App package metadata with the Portfolio Architect v1.18.2 Home Assistant sensor-metadata maintenance release.
- Gateway runtime and REST/health contracts remain unchanged from v1.16.0.

## 1.18.1

- Aligns Gateway App package metadata with the Portfolio Architect v1.18.1 Plan Delta & Decision Trace release.
- Gateway runtime and REST contracts remain unchanged from v1.16.0.

## 1.17.1

- Aligns the Gateway App package with the Portfolio Architect v1.17.1 publication-readiness release.
- Gateway runtime and REST contracts remain unchanged from v1.16.0.

## 1.16.3

- Aligns the Gateway App package with the Portfolio Architect v1.16.3 Home Assistant hotfix.
- Gateway account discovery, selection, reserve publication, OAuth/session state, and REST runtime are unchanged from v1.16.0.
- Requires no new account selection or PhotoTAN unless Comdirect independently requires reauthentication.

## 1.16.0

- Adds an optional, explicitly selected Comdirect investment-reserve account.
- Publishes only the conservative lower of booked balance and available cash,
  clamped at zero, with a bounded timestamp.
- Keeps account identifiers, IBANs, labels, transactions, credit limits, and raw
  balance responses out of REST, diagnostics, entities, and logs.
- Adds protected Ingress discovery, selection, and clearing using short-lived
  opaque browser tokens.
- Keeps the public API GET-only and adds no trading, transfer, payment, or
  transaction-history capability.
- Marks the first deployment as a release candidate pending live balance-semantic
  confirmation.

## 1.15.0

- Aligns the stable Gateway App package with the v1.15.0 interaction-consistency patch.
- Gateway runtime, OAuth recovery, REST schema, health schema, and cached-snapshot behavior are unchanged.

## 1.14.0

- Aligns the stable Gateway App package with the v1.14.0 native-dashboard Stardust release.
- Preserves the proven v1.13.0 Gateway runtime, OAuth recovery, authenticated REST API, health schema 5, cached snapshots, and live Ingress synchronization unchanged.
- Requires no new PhotoTAN bootstrap unless Comdirect rejects the existing bank-issued session.

## 1.13.1

- Aligns the stable Gateway App package with the v1.13.1 release-hygiene patch.
- Preserves the proven v1.13.0 Gateway runtime, OAuth recovery, authenticated REST API, health schema 5, cached snapshots, and live Ingress synchronization unchanged.
- Requires no new PhotoTAN bootstrap unless Comdirect rejects the existing bank-issued session.

## 1.13.0

- Aligns the stable Gateway App package with Portfolio Architect v1.13.0.
- Corrects the Dockerfile default build-version label to 1.13.0.
- Preserves the proven v1.12.2 Gateway runtime, OAuth recovery, authenticated REST API, health schema 5, cached snapshots, and live Ingress synchronization unchanged.
- Requires no new PhotoTAN bootstrap unless Comdirect rejects the existing bank-issued session.

## 1.12.2

- Aligns the stable Gateway App package with Portfolio Architect v1.12.2.
- Preserves the proven v1.12.0 Gateway runtime, OAuth recovery, authenticated REST API, health schema 5, and live Ingress synchronization unchanged.
- Requires no new PhotoTAN bootstrap unless Comdirect rejects the existing bank-issued session.

## 1.12.0

- Aligns the stable Gateway App package with Portfolio Architect v1.12.0.
- Preserves the proven v1.10.1 Gateway runtime, authenticated REST API, OAuth recovery, cached snapshot, health schema 5, and live Ingress synchronization.
- Requires no new PhotoTAN bootstrap unless Comdirect rejects the existing bank-issued session.

## 1.11.0

- Aligns the stable Gateway App with the Portfolio Architect v1.11.0 publication-readiness release.
- Adds reproducible packaging, SPDX SBOM, package manifests, CI validation, and maintenance documentation in the complete source release.
- Preserves the proven v1.10.1 Gateway runtime, OAuth recovery, REST, health, cache, and live Ingress synchronization behaviour.

## 1.10.1

- Classified OAuth refresh rejection separately from connectivity, rate-limit, upstream-service, and malformed-response failures.
- Limited OAuth error-body inspection to 64 KiB and retained only a bounded error code.
- Reported invalid API client credentials as configuration errors instead of demanding PhotoTAN.
- Updated every mutable Ingress runtime field and status colour during two-second polling.
- Fixed successful PhotoTAN recovery remaining amber until a manual page reload.
- Preserved the GET-only bearer API, App-private authentication data, Gateway token, and cached snapshot.

## 1.10.0

- Added backward-compatible authenticated health schema 5.
- Added sanitized last-failure time, failure class, recommended action, and bounded retry guidance.
- Classified authentication, rate-limit, upstream-service, transport, response, configuration, and internal failures without retaining raw upstream content.
- Cleared active failure guidance after a successful refresh.
- Added the recovery metadata to the protected Ingress status page.
- Preserved schemas 1 through 4, the GET-only bearer API, and all App-private authentication and snapshot data.

## 1.9.0

- Added backward-compatible authenticated health schema 4.
- Added refresh-in-progress, duration, trigger, next-scheduled-refresh, and manual-refresh-interval telemetry.
- Kept scheduled polling on a fixed cadence without cumulative request-duration drift.
- Added a CSRF-protected manual refresh action to the authenticated Ingress UI.
- Prevented overlapping refreshes and rate-limited manual requests to one accepted request per minute.
- Kept the bearer-authenticated portfolio API GET-only and preserved all App-private data during in-place update.

## 1.8.0

- Added backward-compatible authenticated health schema 3.
- Added explicit live, last-known-good, reauthentication-required, and unavailable operating modes.
- Added last refresh attempt, consecutive failure count, snapshot age, and remaining cache-window telemetry.
- Marked cached fallback as degraded instead of reporting a misleading healthy state.
- Expanded the protected Ingress status page without exposing secrets or financial values.
- Preserved all App-private credentials, OAuth/session data, bearer token, and cached snapshot during in-place update.

## 1.7.0

- Added SHA-256 and position-count metadata to every portfolio response.
- Added opt-in authenticated health schema 2 with snapshot fingerprint, position count, polling interval, and cache-age configuration.
- Retained the original health document for clients that do not request schema 2.
- Added snapshot integrity details to the protected Ingress UI.
- Preserved all App-private credentials, OAuth/session data, bearer token, and cached snapshot during in-place update.

## 1.6.1

- Promoted the Home Assistant App from experimental to stable after successful live HAOS, Ingress, PhotoTAN, scheduled-refresh, and in-place-upgrade validation.
- Added the Gateway version to the authenticated health document consumed by Portfolio Architect.
- Retained the validated Comdirect protocol and persistent authentication state unchanged.

## 1.6.0

- Added Portfolio Architect icon and logo assets for the Home Assistant App store.
- Retained the proven v1.5.6 Comdirect bootstrap and read-only gateway runtime.
- Made no configuration, credential, session, REST-contract, or persistence migration.

## 1.5.6

- Corrected the Comdirect session-TAN validation request to send the exact
  three-field activation intent.
- Set both `sessionTanActive` and `activated2FA` to `true` during validation, as
  required before Comdirect creates the PhotoTAN challenge.
- Reused the same minimal document for activation instead of reflecting the
  complete session-status response back to the API.
- Added a regression test for the exact validation payload.
- Updated the Gateway user agent and package version.

## 1.5.5

- Corrected the Comdirect `x-http-request-info` request ID to the required
  unique nine-digit decimal format; the client session ID remains a
  32-character hexadecimal value.
- Added sanitized bootstrap diagnostics containing only the failed protocol
  stage and HTTP status, never response bodies or credentials.
- Updated the Gateway user agent and package version.

## 1.5.4

- Fixed HTTP 411 responses when the Home Assistant Ingress proxy forwards the
  bootstrap form as a streamed HTTP/1.1 request without `Content-Length`.
- Disabled unnecessary Ingress streaming for the small bootstrap form.
- Added strict, bounded support for `Transfer-Encoding: chunked` as a defensive
  compatibility path.
- Kept the 16 KiB request limit, CSRF validation, credential zeroing, and
  generic request logging unchanged.

## 1.5.3

- Fixed startup on HAOS installations where Supervisor keeps
  `/data/options.json` readable only by root.
- Parse and strictly validate the non-secret App options before dropping to
  UID/GID 65532.
- Pass the immutable parsed options into the unprivileged runtime; no options
  file or privileged file descriptor remains open.
- Retained the single-interpreter startup correction from v1.5.2.

## 1.5.2

- Fixed the HAOS startup failure in which the post-`setuid` Python re-exec could
  not import the standard-library `encodings` package.
- Start the already initialized gateway runtime in the original process after
  dropping privileges instead of starting a second Python interpreter.
- Replaced the unvalidated custom AppArmor profile with Home Assistant's
  maintained default AppArmor profile; AppArmor remains enabled.
- Added an explicit Python executable path and a build-time standard-library
  import check.

## 1.5.1

- Added native Home Assistant App packaging.
- Added an admin-only Ingress setup and reauthentication UI.
- Kept the provider-neutral REST endpoint on the internal App network only.
- Generated the local bearer token inside the App-private data directory.
- Kept Comdirect username and password out of persistent App configuration.
- Added non-root runtime execution.
