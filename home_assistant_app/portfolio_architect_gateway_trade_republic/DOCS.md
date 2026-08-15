# Portfolio Architect Gateway — Trade Republic v1.27.3

Version 1.27.3 is package alignment for the Portfolio Architect DKB discovery-identity hotfix; Trade Republic statement import, persisted snapshot behavior, TLS trust and bearer authentication are unchanged from v1.27.2.

Uploads remain bounded to 5 MiB and are parsed locally in memory; the original PDF
is discarded. Only the validated provider-neutral holdings snapshot persists.
REST schema 1, health schema 6, provider identity, startup behavior and statement
validation remain unchanged.

Update the Portfolio Architect Home Assistant integration to 1.27.3 before this App
so a configured legacy HTTP source can migrate only after verified HTTPS validation.
