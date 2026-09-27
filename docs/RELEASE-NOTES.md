# Portfolio Architect v1.65.6

DKB cash research now shows bounded private-ID diagnostics for the latest manual read: load reason, ID capture and save outcome, and a short keyed fingerprint. The fingerprint uses an App-private random HMAC key rather than an unkeyed hash of a potentially predictable bank ID. Neither the ID nor the key is displayed, logged, or included in Portfolio Architect state or diagnostics. Both private files are excluded from HA App backups.

This helps locate the v1.65.5 restart-continuity failure before further bank trials. It does not claim that reuse after restart has been accepted. DKB CSV remains the sole cash and holdings source for planning; FinTS remains read-only research, with manual credentials and bank approval when requested. No automated acquisition or source switch is added.

See [details](RELEASE-NOTES-1.65.6.md), the [upgrade guide](UPGRADE-1.65.6.md), and the [previous release](RELEASE-NOTES-1.65.5.md).
