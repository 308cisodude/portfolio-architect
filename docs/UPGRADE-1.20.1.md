# Upgrade to Portfolio Architect 1.20.1

Version 1.20.1 is a focused maintenance release for v1.20.0 graceful degradation.

## What is fixed

When Portfolio Architect entered Home Assistant last-known-good mode while retaining the exact same validated portfolio calculation, some coordinator-backed entities could remain frozen in their previous live state. In particular, health entities could still display `live` and actionability-sensitive monetary entities could continue showing their prior values even though the coordinator had already revoked plan actionability.

Version 1.20.1 makes every completed coordinator cycle notify entity listeners, including LKG transitions where only coordinator health/actionability metadata changed. Holdings remain informationally available from trusted LKG data, while authorized cash and recommendation-derived entities fail closed immediately.

The release also prevents an old integrity-failure reason from being carried into an unrelated transport/calculation fallback. Genuine integrity failures still remain explicit and fail closed.

## Upgrade

1. Update **Portfolio Architect Gateway** to 1.20.1 through **Settings → Apps**.
2. Update **Portfolio Architect** to 1.20.1 through HACS.
3. Restart Home Assistant once after the HACS update.
4. Confirm `Version` reports 1.20.1 and normal live health is healthy.

Existing Gateway authentication, bearer token, selected account, cash-policy state, cached snapshot, and Home Assistant configuration remain compatible.

## Live acceptance

A deliberate Gateway stop for one Portfolio Architect polling cycle should now produce an observable LKG state: informational holdings stay available, `Using LKG` turns on, source/live health degrades, authorized investment cash and recommended totals become unavailable, and plan actionability is false. After the Gateway is started again and live authentication is available, the same entities should automatically return to live state without manual cleanup.
