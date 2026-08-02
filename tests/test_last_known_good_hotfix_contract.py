"""v1.10.2 Home Assistant-side last-known-good resilience contracts."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def test_private_atomic_last_known_good_store_is_bounded_and_source_bound() -> None:
    cache = (COMPONENT / "last_known_good.py").read_text()
    assert "private=True" in cache
    assert "atomic_writes=True" in cache
    assert "serialize_in_event_loop=False" in cache
    assert "_MAX_CACHE_BYTES = 4 * 1024 * 1024" in cache
    for field in (
        '"endpoint_url"',
        '"configuration_sha256"',
        '"snapshot_generated_at"',
        '"snapshot_sha256"',
        '"snapshot_position_count"',
        '"payload"',
    ):
        assert field in cache
    for forbidden in (
        "bearer_token",
        "refresh_token",
        "access_token",
        "client_secret",
        "username",
        "password",
    ):
        assert f'"{forbidden}"' not in cache


def test_cache_is_restored_before_first_gateway_refresh() -> None:
    setup = (COMPONENT / "__init__.py").read_text()
    restore = "await coordinator.async_restore_last_known_good()"
    refresh = "await coordinator.async_refresh()"
    assert restore in setup
    assert setup.index(restore) < setup.index(refresh)


def test_transport_outage_returns_cached_calculation_as_successful_update() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text()
    assert "_use_home_assistant_last_known_good" in coordinator
    assert "return data" in coordinator
    assert 'return "last_known_good"' in coordinator
    assert 'return "transport_error"' in coordinator
    assert "_last_known_good_configuration_sha256 != configuration_sha256" in coordinator
    assert "await self._last_known_good_store.async_save" in coordinator


def test_cached_operation_remains_visible_in_entities_and_diagnostics() -> None:
    binary = (COMPONENT / "binary_sensor.py").read_text()
    diagnostics = (COMPONENT / "diagnostics.py").read_text()
    assert "using_home_assistant_last_known_good" in binary
    assert '"home_assistant_cache_active"' in binary
    assert '"home_assistant_last_known_good"' in diagnostics
    assert '"active": coordinator.using_home_assistant_last_known_good' in diagnostics


def test_cache_canonicalises_engine_decimals_before_home_assistant_storage() -> None:
    cache = (COMPONENT / "last_known_good.py").read_text()
    serializer = (COMPONENT / "cache_payload.py").read_text()
    assert "payload_copy = json_safe_payload(payload)" in cache
    assert "isinstance(value, Decimal)" in serializer
    assert 'return format(value, "f")' in serializer
