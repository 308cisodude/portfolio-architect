# Portfolio Architect Gateway — Trade Republic v1.26.7

Version 1.26.7 retains the supported local import of the German text-PDF **DEPOTAUSZUG** statement family and fixes only the common Gateway cached-snapshot/HTTP conditional-request layer. Optional position quantity now survives cached-snapshot reload byte-for-byte, and ETag validation takes precedence over `If-Modified-Since`.

The upload remains bounded to 5 MiB, parsed locally in memory, and the original PDF is discarded. Only the validated provider-neutral holdings snapshot is stored in `/data/gateway`. REST schema 1, health schema 6, provider identity, startup behavior and statement-parser validation are unchanged.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
