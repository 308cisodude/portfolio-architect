# v1.29.0 validation

Portfolio Architect v1.29.0 is a native reference-dashboard presentation release
based on the published and live-accepted v1.28.2 runtime. Validation must prove the
new visual hierarchy without widening any entity, policy, provider, network or
publication contract.

Release-specific validation must prove:

- integration, engine, common Gateway and all three App package versions are
  `1.29.0`;
- English and German policy-compliance references contain exactly one conditional
  native Heading card labelled `Optimisation opportunities` / `Optimierungsmöglichkeiten`;
- the Heading uses `heading_style: subtitle`, `mdi:lightbulb-on-outline`, full-width
  layout and is visible only while
  `sensor.portfolio_architect_optimisation_opportunity_count > 0`;
- the Heading badge references that existing count entity, shows the state without a
  duplicate icon and opens normal Home Assistant more-info;
- the subtitle is ordered after the accepted-exception decision/review lifecycle and
  before all four concrete savings-plan fee-opportunity tiles;
- the four concrete opportunity tiles remain blue, full-width and individually
  inspectable;
- standalone English/German policy fragments, full localized views and the bilingual
  dashboard encode the same hierarchy;
- the policy presentation adds no custom card, `card_mod`, JavaScript or Markdown
  card surface;
- entity IDs, unique IDs, policy calculations, machine states and availability
  semantics remain unchanged;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain
  unchanged;
- v1.27 private-PKI verified HTTPS, bearer authentication, DNS pinning, Supervisor
  trust discovery and no-plaintext-fallback behavior remain unchanged;
- Comdirect OAuth/session maintenance, Trade Republic statement import and v1.28 DKB
  registration/capability-probe behavior remain unchanged;
- v1.28.1 immutable GitHub Actions pins and v1.28.2 Dependabot grouping remain
  unchanged; and
- no trading, order, transfer, payment or transaction-history capability is added.

The protected GitHub `Validate release` workflow remains authoritative for provider-App
Docker/TLS smoke validation. Live acceptance must additionally verify the updated
reference dashboard in Home Assistant because dashboard rendering is a frontend
behavior that source tests cannot fully prove.
