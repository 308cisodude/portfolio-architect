# Security by design

Portfolio Architect treats every configured CSV, REST response, and YAML input as untrusted data.

## Implemented controls

- `yaml.safe_load` only; no dynamic code evaluation;
- no public-network or third-party service dependency inside the integration;
- optional REST traffic is confined to an explicitly configured local endpoint;
- no shell command construction inside the engine or integration;
- bounded architecture/payload size of 32 positions;
- safe fund-ID character set: lowercase ASCII letters, digits, and underscore;
- bounded printable instrument names and identifiers;
- duplicate fund ID, WKN, and ISIN rejection;
- finite numeric values and explicit range validation;
- target weights must total 100%;
- current percentage totals must match whether the portfolio has value;
- coverage is independently derived in the integration and cross-checked
  against the engine summary;
- malformed or unavailable source data fails closed;
- diagnostics omit instrument names and monetary values;
- entity IDs and migrations use stable non-secret identifiers.

## Trust boundaries

The integration reads only explicitly configured relative paths below the Home
Assistant configuration directory. The calculation engine is bundled inside the
custom component and performs no shell invocation or network access. v1.4 adds a
separate bounded transport layer for an explicitly configured local REST gateway;
the engine remains provider-neutral and network-free.

Backups must never be placed as sibling directories below
`/config/custom_components`, because Home Assistant treats every directory
there as a potential integration package.

## v0.5.1 localization controls

- language selection is delegated to Home Assistant's authenticated user
  profile;
- Portfolio Architect does not store, infer, or write user-language settings;
- the optional shortcut performs navigation only;
- translation placeholders are populated exclusively from already validated,
  bounded instrument names;
- icon selection is declarative and contains no executable templates.

## v0.5.2 dashboard localization controls

Localized dashboards are static YAML. They introduce no executable JavaScript,
external URLs, privileged service calls, dynamic code evaluation, or new data
sources. Internal state keys and entity IDs remain language-neutral.

## v0.5.4 bilingual dashboard controls

The language-selection architecture uses separate native Lovelace views. It
introduces no JavaScript, helper state, profile writes, network calls, or new
integration permissions. English and German views consume the same read-only
entities.


## v0.5.4 dashboard controls

- language selection is ordinary Home Assistant view navigation;
- no profile mutation, helper entity, JavaScript, Browser Mod, or custom card;
- no translated text is used as a machine identifier or calculation input;
- both views reference the same bounded, read-only entity set.

## v0.6.0 monthly-plan and runtime-health controls

- monthly contribution, recommendation totals, and per-position purchases are
  finite, non-negative, and explicitly bounded;
- recommended purchases may not exceed the monthly contribution;
- the recommendation total and purchase count are independently recalculated
  from the validated positions and cross-checked against the engine summary;
- unknown future payload schemas fail closed;
- runtime version and timestamp fields have strict length, format, and timezone
  validation;
- a payload timestamp more than five minutes in the future is not considered
  fresh;
- stale data cannot leave the monthly plan in a ready state;
- health entities remain available during source failure so the failure is
  visible, while calculated entities follow coordinator availability;
- diagnostics report readiness and counts but omit monetary amounts and fund
  names;
- the options flow bounds the freshness threshold to 1–168 hours;
- no new network access, write operation, shell interpolation, JavaScript, or
  third-party dependency was introduced.

## v0.7.0 policy-compliance controls

- policy finding lists are bounded to 256 entries;
- rule, severity, and status values use explicit allowlists;
- instrument IDs must match a validated recommendation;
- duplicate instrument/rule findings are rejected;
- messages, exception IDs, and rationale text are length-bounded;
- observed and expected values are limited to bounded JSON scalars;
- exception metadata is rejected on non-exception findings;
- accepted exceptions require an ID and bounded rationale;
- review dates must be valid ISO dates;
- schema-6 policy summary counts are cross-checked against every finding;
- diagnostics expose only finding keys and counts, not rationale text or
  portfolio values;
- active finding entities become unavailable when the finding is resolved,
  rather than retaining a plausible stale state.

## v0.8.0 allocation and review controls

- portfolio value is independently recomputed from validated position values;
- allocation counts are independently recomputed from validated position states;
- each allocation status is checked against the configured corridor and its
  signed percentage-point deviation;
- schema 7 requires the complete allocation and exception-review contracts;
- past exception review dates cannot be presented as a future review;
- overdue review counts and dates are bounded and derived from accepted
  exceptions only;
- diagnostics expose allocation counts and governance dates but omit portfolio
  values and exception rationale text;
- no network, shell, write, or third-party dependency was added.

## v0.9.0 complete-portfolio controls

- CSV input is bounded to 4096 rows and 512 imported positions.
- WKN, ISIN, names, source types and values are validated before use.
- Duplicate WKNs and duplicate holding identities fail closed.
- Instrument type never grants strategy membership; scope is resolved only by exact
  configured WKN membership.
- Unknown instrument types remain neutral `other` holdings.
- Outside-scope holdings cannot carry target, drift or proposed-purchase metadata.
- Whole-portfolio percentages and values are independently recalculated by the Home
  Assistant integration.
- Diagnostics expose counts, stable IDs, types and scopes but omit financial values
  and holding names.

## v1.1.0 self-contained source controls

- source paths are relative to `/config`, normalised, resolved, and checked for
  path traversal and symlink escape;
- `.storage` and `custom_components` are denied as user-data source roots;
- the CSV is capped at 10 MiB and each YAML document at 1 MiB;
- all blocking file I/O and calculations run in Home Assistant's executor;
- the integration uses a bounded 15-minute local polling interval and can also
  be refreshed on demand;
- the portfolio evaluation timestamp comes from the CSV modification time, so
  unchanged polling cannot silently postpone a due review;
- absolute configuration paths are not exposed in payloads or diagnostics;
- the deprecated command-line source remains available only as a migration
  fallback and can be removed after local-file mode is verified.

## v1.2.0 native plan controls

- UI plan overrides are stored as bounded config-entry options and never written
  back into the source YAML documents;
- the selectable scope is built only from exact configured or imported
  identifiers; names and instrument types never grant scope membership;
- plans contain 1–32 instruments with unique bounded IDs, WKNs, and ISINs;
- target weights must be finite, positive, at most 100%, and total exactly 100%;
- proportional normalisation requires an explicit confirmation step;
- at least one selected instrument must remain eligible for purchases;
- plan budgets are finite, positive, and capped at EUR 10,000,000;
- frequency, budget basis, execution days, execution month, and review lead time
  use explicit allowlists and numeric bounds;
- the complete engine result is recalculated and independently parsed before a
  plan override is persisted;
- schedule-aware freshness uses the validated CSV timestamp and local calendar
  dates; changing options cannot disguise an old holdings snapshot as new;
- resetting the UI plan removes only plan-related options and preserves source
  paths and runtime safeguards;
- no network access, shell invocation, custom frontend, or write access to broker
  accounts was introduced.

## v1.3.0 provider-adapter controls

- provider selection uses an explicit allowlist;
- encodings, delimiters, number formats, and header rows are bounded allowlists;
- generic mappings refer only to headers read from the selected local file;
- duplicate headers and duplicate instrument identifiers are rejected;
- generic market values must be finite, non-negative, bounded, and already in
  EUR;
- optional currency mapping rejects every non-EUR row;
- no spreadsheet formulas, macros, external URLs, or executable content are
  interpreted;
- the import adapter returns canonical positions before any plan, policy, or
  recommendation logic runs;
- diagnostics expose non-secret mapping metadata but omit portfolio values.
## v1.4.0 local REST gateway controls

- bank credentials, MFA state, and bank-specific sessions remain outside Home
  Assistant; only a dedicated local-gateway bearer token is stored;
- the adapter implements GET only and exposes no order, trade, transfer, or
  account-write operation;
- URL user information, query strings, and fragments are rejected;
- immediately before every request, the operating-system resolver is called once
  and every returned address must be loopback, link-local, or private; mixed
  local/public answers fail closed;
- the validated address set is bound to a request-scoped `aiohttp` resolver, so
  connection establishment cannot perform an independent second DNS lookup;
- the original hostname remains in the URL, preserving the HTTP Host header, TLS
  SNI, and certificate-name validation;
- redirects, environment proxies, persistent cookies, DNS caching, and connection
  reuse are disabled for the authenticated local REST boundary;
- requests use a 15-second total timeout, a 1 MiB streamed portfolio limit, and a
  16 KiB streamed health limit;
- only UTF-8 JSON with an application/json-compatible content type is accepted;
- ambiguous duplicate JSON object keys are rejected;
- schema version, currency, position count, identifiers, ISINs, strings, monetary
  decimals, and source timestamps are strictly validated;
- monetary values must be canonical JSON strings, avoiding binary-float
  conversion;
- duplicate identifiers and ISINs, non-EUR values, empty portfolios, and future
  timestamps fail closed;
- HTTP 401/403 invokes Home Assistant reauthentication; HTTP 429 honours only a
  bounded integer-seconds Retry-After value;
- ETag and Last-Modified validators reduce polling while local YAML changes still
  force recalculation from the last validated snapshot;
- diagnostics expose endpoint and transport limits but never the bearer token or
  financial values.

The request-scoped session is a deliberate exception to shared-session reuse: its
custom resolver is the security control that binds validation and connection. A
literal private address remains operationally simple, but it is no longer needed
as a workaround for a validation/connection DNS race. HTTPS remains recommended
whenever the local token crosses a network segment.
## v1.5 gateway controls

The separate Comdirect gateway adds a second explicit trust boundary:

- exact outbound bank origin and small method/path allowlist;
- authentication/session writes only, with no trading or transfer code;
- bank username/password available only during one-shot bootstrap;
- persisted OAuth/session state protected as a secret and absent from Home Assistant;
- authenticated GET-only local API with no values in health output;
- atomic last-known-good cache whose original timestamp remains visible;
- non-root, read-only, capability-free reference container;
- source-IP firewall restriction and TLS required by deployment policy whenever
  the local token crosses a less-trusted network segment.

Because Comdirect may issue a brokerage token with write-capable scope, OAuth
scope alone is not treated as the read-only control. Read-only behaviour is
enforced by gateway code, absence of trading endpoints, container isolation, and
network policy.



## v1.5.1 Home Assistant App controls

The native App deployment preserves a container boundary between the Portfolio
Architect integration and bank authentication while sharing the HAOS/Supervisor
trust domain. It requests no host network, device, Supervisor API, Home Assistant
API, Auth API, Docker API, privileged capability, or Home Assistant configuration
mapping.

The App's Ingress listener accepts only the Supervisor ingress source address
and authenticated-user headers. The bank username/password are handled only in
memory during bootstrap. API client credentials, the generated local bearer
token, and snapshots use mode `0600` in the private `/data/gateway` directory.
OAuth/session state is excluded from Home Assistant backups so a restored system
must prove possession of the PhotoTAN factor again.

The internal REST endpoint remains bearer-authenticated even though it is not
published to the LAN. This protects against unrelated workloads in the shared
internal App network and keeps the custom integration/gateway interface explicit.


## v1.9.0 refresh-operation controls

- the bearer-authenticated portfolio and health API remains GET-only;
- manual refresh is available only through authenticated Home Assistant Ingress;
- the manual POST requires a per-process CSRF token and an exact bounded form;
- requests are limited to one accepted manual refresh per minute;
- one non-blocking execution lock prevents overlapping startup, scheduled,
  bootstrap, and manual refresh operations;
- manual refresh does not rotate, display in logs, or accept the Gateway bearer
  token;
- refresh telemetry is bounded and contains no credentials, account metadata,
  instrument names, quantities, or monetary values;
- scheduled polling retains a fixed cadence independent of manual requests and
  prior request duration.

## v1.10.0 classified recovery controls

- health schema 5 exposes only bounded failure classes, timestamps, recommended
  actions, and retry intervals;
- raw Comdirect response bodies, cookies, credentials, bearer tokens, account
  identifiers, holdings, and monetary values are excluded;
- retry guidance is bounded before publication;
- a successful refresh clears prior failure guidance;
- Home Assistant Repair issues contain translation keys and severity only, not
  secret or financial context;
- transient single refresh failures remain observable without immediately
  creating persistent operator noise;
- integrity failure, snapshot unavailability, repeated refresh failure,
  refresh overdue, and reauthentication remain distinct fail-closed conditions.

## v1.10.1 private last-known-good controls

The Home Assistant integration stores one calculated REST result in private,
atomic `.storage` data. The document is size-bounded and tied to both the REST
endpoint and a SHA-256 fingerprint of all calculation configuration inputs. It
contains calculated portfolio data and snapshot integrity metadata, but never
the Gateway bearer token, Comdirect username/password, API client secret, OAuth
access/refresh token, or qSession cookie.

OAuth error bodies are read only within a 64 KiB limit for token endpoints. The
Gateway retains only a restricted lowercase OAuth error code and discards all
other fields immediately; descriptions and raw response bodies never enter
state, health documents, diagnostics, or logs.

## v1.10.2 cache serialization controls

The private last-known-good cache is written from a detached canonical copy of
an already validated calculated payload. Only JSON primitives, string-keyed
objects, and arrays are accepted. Finite decimals are represented as exact
plain-decimal strings; non-finite and unsupported values fail closed. Restored
content is never trusted directly and must pass the complete payload parser
before publication. No authentication or session material is added to the
cache.

## v1.17.1 publication and transport hardening

- every reusable GitHub Action is pinned to a full 40-character commit SHA;
- the HACS and hassfest validators are executed from immutable GHCR SHA-256
  digests because their upstream wrappers currently delegate to mutable images;
- local and release validation reject mutable action refs, mutable image tags,
  and GHCR workflow images without an explicit digest;
- workflow token permissions are explicit and minimal for each job;
- the publication configurator writes an active `.github/CODEOWNERS` file,
  explicitly protects workflows and release tooling, and removes the inactive
  example file;
- strict publication validation checks the ownership rules but GitHub branch
  protection or a repository ruleset remains responsible for requiring approval;
- authenticated local REST requests use one validated and connection-pinned DNS
  answer, eliminating the prior resolver time-of-check/time-of-use window;
- executable regressions verify pinned-address connection, original Host-header
  preservation, mixed-address rejection, and rejection of mutable workflow
  dependencies.

## v1.17.2 release-archive boundary validation

- HACS and manual installation archives are staged independently according to their extraction boundaries;
- the HACS asset must expose the integration manifest at the archive root and may not contain a `custom_components/` prefix;
- the manual drop-in must contain the exact `custom_components/portfolio_architect/` wrapper;
- release verification compares every payload file and SHA-256 after normalizing the manual archive prefix; and
- a regression test requires the verifier to reject the prior nested-HACS layout.

## v1.18.0 decision-trace storage controls

- exactly two provider-neutral validated evaluations are retained in private,
  atomic Home Assistant storage;
- the document is size-bounded, carries a canonical SHA-256 integrity value, and
  strict field validation rejects unknown, malformed, duplicated, non-finite, or
  non-deterministically ordered content;
- the trace excludes credentials, account identifiers, ISIN/WKN values, source
  paths, raw source records, and transaction history;
- REST last-known-good replay never advances the trace;
- trace persistence is non-authoritative and cannot suppress a valid portfolio
  update;
- detailed trace attributes are excluded from recorder history; and
- diagnostics intentionally omit monetary trace deltas.

## v1.20.0 graceful-degradation controls

- a failed, timestamp-regressed, or integrity-inconsistent incoming REST snapshot
  cannot replace the previously accepted validated calculation;
- Home Assistant last-known-good retention is explicitly bounded by the positive
  Gateway-advertised maximum cache age when available, with a seven-day fallback;
- cached holdings and allocation are informational only: REST investment cash,
  proposed purchases, fees/outlay, and reserve-derived execution state require a
  fresh, healthy, live source before they are exposed as actionable values;
- configuration binding remains mandatory for cache replay, so changing portfolio
  inputs prevents restoration of a calculation produced for a different setup;
- refresh-overdue state requires a health observation obtained after the scheduled
  deadline plus grace while the Gateway still advertises the miss; local time
  alone cannot upgrade stale schedule telemetry into failure evidence;
- snapshot age and retention countdown are calculated from the accepted snapshot
  timestamp rather than trusting a frozen age value from an earlier health poll;
  and
- AI-assisted development is disclosed in `AI_POLICY.md`; publication remains an
  explicit maintainer-controlled process rather than an autonomous agent action.


## v1.20.1 degraded-state publication controls

A degraded update is a security-relevant state transition even when the trusted last-known-good portfolio calculation is unchanged. Portfolio Architect therefore notifies entity listeners for every completed coordinator cycle so stale live-state entities cannot continue to expose authorized cash or recommendation values after actionability has been revoked. Integrity-failure Repairs are tied to current integrity evidence; unrelated transport or calculation failures do not inherit an older mismatch reason.

## v1.21 schedule and actionability evidence boundary

Portfolio Architect does not treat a scheduled execution date, a past scheduled date, or a holding-quantity change as evidence that a trade occurred. Version 1.21.0 exposes current actionability as bounded advisory state derived from freshness, integrity, Gateway/LKG health, and execution readiness. The new entity has no write path to a bank or broker and does not alter the read-only Gateway security boundary.

## v1.22 publication confidentiality controls

Publication is fail-closed on both Portfolio Architect-specific privacy checks and
an independently pinned Gitleaks scan. The protected workflows scan the tracked
source tree, complete Git patch history, and generated release contents before a
release can be attested or published. The Gitleaks container is pinned by SHA-256
and runs without network access or Linux capabilities.

The privacy checker also rejects raw broker documents, unapproved exports,
unexpected images/screenshots, private key material, valid IBANs, and suspicious
provider identity literals unless they are unmistakably synthetic test values.
Findings never print exact private-literal contents.

## v1.23 provider-isolation controls

The hardened Gateway HTTP server now depends on a minimal provider protocol rather
than directly on the Comdirect client. The provider supplies only a bounded
`provider_id`, validated refresh cadence, and a validated provider-neutral snapshot.
Health schema 6 exposes the provider ID for operational provenance while retaining
schemas 1 through 5 for compatibility.

The existing Comdirect App keeps its historical slug and `/data/gateway` private
storage so the architectural split does not migrate or copy authentication state.
Reserved future DKB and Trade Republic App identities are separate security
boundaries with separate private state; v1.24.0 does not ship either acquisition
runtime. No provider contract introduces a trading, order, transfer, payment, or
transaction-history write path.
