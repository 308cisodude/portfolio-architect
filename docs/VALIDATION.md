# v1.42.0 validation

Portfolio Architect v1.42.0 is prepared from the exact published/live-accepted v1.41.1 tracked-source baseline. The release adds only Home Assistant-side normalized execution-path presentation, native reference-dashboard rendering, regression coverage, and normal package/version/documentation alignment.

Validation requires:

- all integration/common Gateway/provider App current-version markers align to 1.42.0 while historical release documentation remains historical;
- the execution-path adapter consumes already-decided plan/position fields and contains no route-selection or funded-route-selection dependency;
- local-cash, transfer, and mixed synthetic cases produce deterministic bounded ordered steps and bilingual presentation text;
- zero settlement business days renders as same-business-day availability without claiming an instant-transfer SLA;
- the bilingual reference dashboard contains exactly one execution-path Markdown renderer per locale and its Jinja only reads the integration-owned localized Markdown attribute;
- the dashboard does not infer funding from `funding_transfers`, provider cash, execution-provider attributes, or other business-policy inputs;
- historical native-dashboard contracts continue to prohibit custom cards, card-mod, auto-entities and JavaScript while allowing the deliberately bounded native Markdown renderer introduced here;
- provider-scoped cash, cost-first funding selection, v1.41.1 local-cash preference, Trade Republic holdings/cash acquisition, and all provider runtime behavior remain unchanged;
- payload schema 8, REST portfolio schema 1, Gateway health schema 6, presentation schema 2 and broker schemas 1/2/3 remain unchanged;
- source/release privacy, publication readiness, provider-App source parity, deterministic release builds, and exact Git overlay/binary-patch replay all pass.

Docker remains a protected GitHub-workflow validation boundary when a local Docker daemon is unavailable.
