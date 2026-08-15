# Portfolio Architect Gateway — Trade Republic v1.27.0

Version 1.27.0 retains the supported local German text-PDF **DEPOTAUSZUG** importer
and moves only the common internal Gateway REST/health transport to verified HTTPS.
The App creates a persistent private CA and Supervisor-hostname server certificate
under `/data/gateway/tls`, keeps private keys App-local, and publishes only public
CA trust plus bounded endpoint/provider identity through Supervisor discovery. The
existing bearer token remains required.

Uploads remain bounded to 5 MiB and are parsed locally in memory; the original PDF
is discarded. Only the validated provider-neutral holdings snapshot persists.
REST schema 1, health schema 6, provider identity, startup behavior and statement
validation remain unchanged.

Update the Portfolio Architect Home Assistant integration to 1.27.0 before this App
so a configured legacy HTTP source can migrate only after verified HTTPS validation.
