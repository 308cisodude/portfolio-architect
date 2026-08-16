# Portfolio Architect Gateway — Comdirect v1.27.4

Version 1.27.4 fixes a timing-dependent Comdirect OAuth renewal race. Short-lived
OAuth session maintenance now runs every five minutes inside the Comdirect provider
package, independently of portfolio snapshot polling. The maintenance path performs
no holdings, balance, instrument, transaction, order, payment, or transfer request;
it only exercises the existing OAuth renewal path when the current access token is
no longer safely usable.

A conclusively rejected refresh session is latched until interactive PhotoTAN
bootstrap succeeds, avoiding repeated submission of the same rejected refresh token.
The Gateway logs only a bounded non-secret rejection reason.

Verified HTTPS/private CA trust, bearer authentication, portfolio acquisition,
account selection, authorized cash, REST schema 1, health schema 6, and the read-only
boundary are unchanged. Upgrade in place and never remove `/data/gateway` during a
normal update.
