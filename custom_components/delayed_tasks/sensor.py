"""Sensor entity reporting pending delayed tasks."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_TASKS_UPDATED
from .manager import TaskManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    manager: TaskManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DelayedTasksCountSensor(entry, manager)])


class DelayedTasksCountSensor(SensorEntity):
    """Sensor showing active pending tasks count and details in attributes."""

    _attr_has_entity_name = True
    _attr_name = "Oczekujące zadania"
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, entry: ConfigEntry, manager: TaskManager) -> None:
        self._entry = entry
        self._manager = manager
        self._attr_unique_id = f"{entry.entry_id}_tasks_count"

    @property
    def native_value(self) -> int:
        """Return the count of pending tasks."""
        return len(self._manager.tasks)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of tasks with details."""
        sorted_tasks = sorted(
            self._manager.tasks.values(),
            key=lambda t: t.execute_at,
        )
        return {
            "tasks": [t.to_dict() for t in sorted_tasks]
        }

    async def async_added_to_hass(self) -> None:
        """Register dispatcher callbacks for real-time state updates."""
        @callback
        def _update() -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_TASKS_UPDATED, _update)
        )
