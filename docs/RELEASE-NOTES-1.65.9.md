# Portfolio Architect v1.65.9 — DKB manual portfolio preparation

The DKB Gateway now provides admin-only selection of one eligible EUR account, a single **Refresh portfolio now** action for the existing read-only holdings and booked-balance requests, and **Investment cash authorization**. The obsolete anonymous BPD probe section is removed from Ingress; its previous bounded status and endpoints remain for compatibility.

Account discovery lists masked choices for five minutes. The App saves only a keyed binding of the chosen account to the banking user and a four-digit display suffix, not a full IBAN or account inventory. A later cash read checks the exact binding even if several accounts share a suffix. The key and selection are excluded from backups; restoration requires selection again. Changing selection invalidates the old cash shadow.

The manual refresh reads the one authorized depot and then the selected account. DKB may request approval at either stage. The extra in-memory password copy needed between stages has a scheduled five-minute expiry. The five-minute detailed review, 24-hour research shadow state, and 72-hour system-ID hint retain their own scopes. Booked cash may differ from spendable cash when transactions are pending.

Investment cash authorization offers all eligible cash, a EUR cap, or a retained EUR reserve. Saving it immediately affects **authoritative CSV cash**. The default remains all eligible CSV cash. On rollback, v1.65.8 ignores a saved cap or reserve and would again authorize all eligible CSV cash.

**DKB CSV remains authoritative for both holdings and cash.** FinTS observations do not enter the planner. An explicit source switch, independent FinTS provenance and 14-day hard expiry, no-fallback recovery behavior, and live acceptance require a separate release.
