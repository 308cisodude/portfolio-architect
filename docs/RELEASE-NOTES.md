# Portfolio Architect 1.18.2

Version 1.18.2 is a stable Home Assistant compatibility maintenance release based
on the v1.18.1 known-good baseline.

## Monetary sensor metadata

Home Assistant does not permit `SensorStateClass.MEASUREMENT` for sensors using
`SensorDeviceClass.MONETARY`. Portfolio Architect previously applied that state
class to several advisory and planning values, causing Home Assistant to report
invalid sensor-metadata warnings during integration setup.

Version 1.18.2 removes the state class from those monetary entities while retaining
their monetary device class, EUR unit, values, entity IDs, unique IDs, and display
precision. The affected categories are:

- contribution and recommendation amounts;
- available, remaining, deferred, and additionally required investment cash;
- estimated transaction fees and cash outlay;
- per-instrument proposed purchases.

These values are current/advisory amounts rather than accumulating counters, so
`TOTAL` semantics are deliberately not introduced.

## Regression protection

A static sensor-metadata contract now discovers monetary sensor classes through
inheritance and rejects the invalid `MEASUREMENT` state class on them. The contract also
confirms that valid `MEASUREMENT` state classes remain present on non-monetary
percentage, duration, quantity, and diagnostic sensors.

## Stability boundary

- Portfolio payload schema 8, REST schema 1, and Gateway health schema 5
  are unchanged.
- Portfolio values, allocation, policy, target corridor, recommendation distribution,
  execution-cost calculation, reserve behavior, Plan Delta semantics, and holding
  quantity semantics are unchanged.
- Existing entity IDs, unique IDs, configuration entries, dashboards, and stored
  options remain compatible.
- Gateway runtime behavior is unchanged from v1.16.0; Gateway App 1.18.2 is package
  alignment only.
- The experimental v1.19.0 brokerage-diagnostic work is not included.
