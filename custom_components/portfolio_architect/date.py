"""Read-only Portfolio Architect date presentation entities."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from homeassistant.components.date import DateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION
from .coordinator import PortfolioArchitectCoordinator

_READ_ONLY_ERROR = (
    "Portfolio Architect date presentation entities are read-only; "
    "their values are derived from the authoritative Portfolio Architect sensors"
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up read-only date entities used by the reference dashboards."""
    coordinator: PortfolioArchitectCoordinator = entry.runtime_data
    async_add_entities(
        [
            PortfolioPlannedExecutionDate(coordinator, entry),
            PortfolioNextPlanReviewDate(coordinator, entry),
            PortfolioLastExceptionDecisionDate(coordinator, entry),
            PortfolioNextExceptionReviewDate(coordinator, entry),
            PortfolioOldestOverdueExceptionReviewDate(coordinator, entry),
        ]
    )


class _PortfolioPresentationDate(
    CoordinatorEntity[PortfolioArchitectCoordinator], DateEntity
):
    """Read-only native date counterpart for one authoritative DATE sensor."""

    _attr_has_entity_name = True
    object_id: str
    value_getter: Callable[[PortfolioArchitectCoordinator], date | None]

    def __init__(
        self,
        coordinator: PortfolioArchitectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, context=f"date_presentation:{self.object_id}")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{self.object_id}_date_presentation"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        """Return the stable object ID shared with the authoritative sensor."""
        return self.object_id

    @property
    def native_value(self) -> date | None:
        """Mirror the authoritative date value without transforming it."""
        if not super().available or self.coordinator.data is None:
            return None
        return self.value_getter(self.coordinator)

    @property
    def available(self) -> bool:
        """Match the mirrored value's availability."""
        return self.native_value is not None

    async def async_set_value(self, value: date) -> None:
        """Reject writes: these entities are presentation-only mirrors."""
        raise HomeAssistantError(_READ_ONLY_ERROR)


def _planned_execution_value(
    coordinator: PortfolioArchitectCoordinator,
) -> date | None:
    schedule = coordinator.plan_review_schedule()
    return schedule.planned_execution_on if schedule is not None else None


def _next_plan_review_value(
    coordinator: PortfolioArchitectCoordinator,
) -> date | None:
    schedule = coordinator.plan_review_schedule()
    return schedule.next_review_on if schedule is not None else None


class PortfolioPlannedExecutionDate(_PortfolioPresentationDate):
    """Locale-renderable counterpart of planned_execution."""

    _attr_translation_key = "planned_execution"
    object_id = "planned_execution"
    value_getter = staticmethod(_planned_execution_value)


class PortfolioNextPlanReviewDate(_PortfolioPresentationDate):
    """Locale-renderable counterpart of next_plan_review."""

    _attr_translation_key = "next_plan_review"
    object_id = "next_plan_review"
    value_getter = staticmethod(_next_plan_review_value)


class PortfolioLastExceptionDecisionDate(_PortfolioPresentationDate):
    """Locale-renderable counterpart of last_exception_decision."""

    _attr_translation_key = "last_exception_decision"
    object_id = "last_exception_decision"
    value_getter = staticmethod(
        lambda coordinator: coordinator.data.policy.last_exception_decision_on
    )


class PortfolioNextExceptionReviewDate(_PortfolioPresentationDate):
    """Locale-renderable counterpart of next_exception_review."""

    _attr_translation_key = "next_exception_review"
    object_id = "next_exception_review"
    value_getter = staticmethod(
        lambda coordinator: coordinator.data.policy.next_exception_review_on
    )


class PortfolioOldestOverdueExceptionReviewDate(_PortfolioPresentationDate):
    """Locale-renderable counterpart of oldest_overdue_exception_review."""

    _attr_translation_key = "oldest_overdue_exception_review"
    object_id = "oldest_overdue_exception_review"
    value_getter = staticmethod(
        lambda coordinator: coordinator.data.policy.oldest_overdue_review_on
    )


def _device_info(source_key: str) -> DeviceInfo:
    """Attach presentation entities to the established Portfolio Architect device."""
    return DeviceInfo(
        identifiers={(DOMAIN, source_key)},
        name=NAME,
        manufacturer="Portfolio Architect",
        model="Local portfolio analysis service",
        sw_version=VERSION,
        entry_type=DeviceEntryType.SERVICE,
    )
