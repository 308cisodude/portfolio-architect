# v1.35.3 validation

Portfolio Architect v1.35.3 is prepared from the exact published v1.35.2 tracked-source baseline.
It is a narrow Home Assistant options-menu presentation hotfix for the native execution-policy
editor. Broker semantics, funding topology, provider runtimes and wire schemas are unchanged.

Validation requires:

- all integration/common Gateway/provider App version markers align at `1.35.3`;
- English and German translation JSON parse successfully;
- every literal menu option emitted by the four broker-editor `async_show_menu()` steps has a
  non-empty translated label in both languages;
- each menu label matches the established title of its destination step;
- the focused v1.35.2 execution-policy/retained-cash plus v1.35.3 menu-label set passes **12/12** tests;
- the complete regression suite passes **554/554** tests in four disjoint runs (**139 + 139 + 138 + 138**);
- Python compilation and all tracked JSON/YAML parsing pass;
- strict publication-readiness and source-privacy checks pass;
- three independent release builds are byte-identical;
- release verification, internal `SHA256SUMS` verification and artifact-privacy checks pass;
- the Git overlay and independent binary patch each reproduce the final tracked tree from the exact
  v1.35.2 baseline, including executable-bit semantics.

Local Docker availability is environment-dependent. Protected GitHub **Validate release** remains
authoritative for actual provider-App Docker/private-PKI smoke execution when local Docker is
unavailable.
