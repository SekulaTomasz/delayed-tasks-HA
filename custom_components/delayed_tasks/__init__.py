"""Delayed Tasks integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ACTION,
    ATTR_DATA,
    ATTR_DELAY,
    ATTR_EXECUTE_AT,
    ATTR_MISSED_ACTION,
    ATTR_NAME,
    ATTR_TARGET,
    ATTR_TASK_ID,
    CONF_MISSED_DISCARD,
    CONF_MISSED_EXECUTE,
    DOMAIN,
)
from .manager import TaskManager

PLATFORMS = ["sensor"]

SERVICE_SCHEDULE = "schedule_task"
SERVICE_CANCEL = "cancel_task"
SERVICE_CLEAR_ALL = "clear_all"

SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ACTION): cv.string,
        vol.Optional(ATTR_NAME): cv.string,
        vol.Optional(ATTR_EXECUTE_AT): cv.datetime,
        vol.Optional(ATTR_DELAY): cv.time_period,
        vol.Optional(ATTR_TARGET): cv.dict,
        vol.Optional(ATTR_DATA): cv.dict,
        vol.Optional(ATTR_MISSED_ACTION, default=CONF_MISSED_EXECUTE): vol.In(
            [CONF_MISSED_EXECUTE, CONF_MISSED_DISCARD]
        ),
    }
)

CANCEL_SCHEMA = vol.Schema({vol.Required(ATTR_TASK_ID): cv.string})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up via configuration.yaml (optional)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry (UI)."""
    manager = TaskManager(hass)
    await manager.async_load()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = manager

    async def handle_schedule(call: ServiceCall) -> None:
        execute_at = call.data.get(ATTR_EXECUTE_AT)
        delay = call.data.get(ATTR_DELAY)

        await manager.async_add_task(
            action=call.data[ATTR_ACTION],
            name=call.data.get(ATTR_NAME),
            execute_at=execute_at,
            delay=delay,
            target=call.data.get(ATTR_TARGET),
            data=call.data.get(ATTR_DATA),
            missed_action=call.data.get(ATTR_MISSED_ACTION, CONF_MISSED_EXECUTE),
        )

    async def handle_cancel(call: ServiceCall) -> None:
        task_id = call.data[ATTR_TASK_ID]
        await manager.async_cancel_task(task_id)

    async def handle_clear_all(_call: ServiceCall) -> None:
        await manager.async_clear_all()

    hass.services.async_register(DOMAIN, SERVICE_SCHEDULE, handle_schedule, schema=SCHEDULE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL, handle_cancel, schema=CANCEL_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_ALL, handle_clear_all)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        manager: TaskManager = hass.data[DOMAIN].pop(entry.entry_id)
        for task in manager.tasks.values():
            if task.unsub_timer:
                task.unsub_timer()

        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SCHEDULE)
            hass.services.async_remove(DOMAIN, SERVICE_CANCEL)
            hass.services.async_remove(DOMAIN, SERVICE_CLEAR_ALL)

    return unload_ok
