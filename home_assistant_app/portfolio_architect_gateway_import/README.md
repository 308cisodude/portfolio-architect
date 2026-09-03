# Portfolio Architect Gateway — Generic Import v1.62.2

Version 1.62.2 preserves the stable multi-profile Generic Import runtime and changes only source-profile readiness presentation: SETUP REQUIRED is amber and READY is blue, while active/authoritative CSV remains green. Provider identity, acquisition, private state, health schema 10, discovery transport, private-PKI/bearer boundary and no-fallback behavior are unchanged.

Version 1.62.0 graduates Generic Import to **stable** and makes it a supported standalone or supplemental Portfolio Architect provider. One App can host up to eight independent source profiles for otherwise unsupported banks/brokers.

Each new profile receives an immutable generated `generic_<stable-id>` identity and a separately editable name. An existing experimental `generic_csv` source keeps that identity and its legacy `/api/v1/portfolio` path. Profiles have independent mappings, normalized holdings snapshots, optional provider-local EUR investment cash and independent holdings/cash evidence timestamps.

Raw CSV bytes are parsed transiently and are never persisted. A successful holdings import atomically replaces only that profile's holdings while retaining independently recorded cash; a rejected import leaves the prior canonical snapshot untouched. A profile becomes discoverable only after validated holdings exist. Renaming never changes provider identity. Deletion is explicit and profile-scoped; users must first remove an adopted provider from Portfolio Architect because the App deliberately has no Home Assistant API permission.

Supervisor discovery transport schema 2 carries each ready profile's exact REST path and bounded human name. Gateway health schema 10 exposes that name while immutable provider identity and all snapshot/trust checks remain fail-closed. One App-level private CA and bearer secret protect the origin; each logical provider endpoint must still return the exact requested `provider_id`.
