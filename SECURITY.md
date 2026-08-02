# Security policy

Do not report suspected vulnerabilities in public issues when they could expose
credentials, authentication material, account metadata, or portfolio data. Use
the public repository's private vulnerability-reporting function.

Supported releases are the current stable release and the immediately previous
stable release while an upgrade path is documented. Banking credentials,
Comdirect OAuth material, the Gateway bearer token, Home Assistant `.storage`
files, raw portfolio snapshots, account identifiers, and transaction data must
never be included in a report.

A useful private report includes the affected Portfolio Architect, Gateway, and
Home Assistant versions; a minimal reproduction; the affected trust boundary;
and sanitized logs or diagnostics. Do not test against accounts or systems you do
not own or have explicit permission to assess.

See `docs/SECURITY.md` for the trust boundaries, secret handling, network model,
and recovery controls. See `SUPPORT.md` for the supported-version window.
