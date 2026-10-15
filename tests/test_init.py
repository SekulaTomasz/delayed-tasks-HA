"""Test Delayed Tasks integration initialization and services."""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.delayed_tasks.const import DOMAIN


async def test_setup_and_unload_entry(hass: HomeAssistant) -> None:
    """Test setting up and unloading config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Delayed Tasks",
        data={},
        entry_id="test_entry_1",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.delayed_tasks.manager.Store.async_load",
        return_value={"tasks": []},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    # Check services registered
    assert hass.services.has_service(DOMAIN, "schedule_task")
    assert hass.services.has_service(DOMAIN, "cancel_task")
    assert hass.services.has_service(DOMAIN, "clear_all")

    # Unload entry
    assert await hass.config_entries.async_unload(entry.entry_id) is True
    await hass.async_block_till_done()

    # Check services removed when last entry is unloaded
    assert not hass.services.has_service(DOMAIN, "schedule_task")
    assert not hass.services.has_service(DOMAIN, "cancel_task")
    assert not hass.services.has_service(DOMAIN, "clear_all")


async def test_service_schedule_and_cancel(hass: HomeAssistant) -> None:
    """Test calling schedule_task and cancel_task services."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Delayed Tasks",
        data={},
        entry_id="test_entry_2",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.delayed_tasks.manager.Store.async_load",
        return_value={"tasks": []},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    manager = hass.data[DOMAIN][entry.entry_id]

    # Schedule a task via service
    await hass.services.async_call(
        DOMAIN,
        "schedule_task",
        {
            "action": "switch.turn_on",
            "name": "Test Service Schedule",
            "delay": {"minutes": 5},
            "target": {"entity_id": "switch.test"},
        },
        blocking=True,
    )

    assert len(manager.tasks) == 1
    task = next(iter(manager.tasks.values()))
    assert task.name == "Test Service Schedule"
    assert task.action == "switch.turn_on"

    # Cancel task via service
    await hass.services.async_call(
        DOMAIN,
        "cancel_task",
        {"task_id": task.task_id},
        blocking=True,
    )

    assert len(manager.tasks) == 0

    # Schedule and clear_all
    await hass.services.async_call(
        DOMAIN,
        "schedule_task",
        {
            "action": "light.turn_off",
            "delay": {"minutes": 10},
        },
        blocking=True,
    )
    assert len(manager.tasks) == 1

    await hass.services.async_call(DOMAIN, "clear_all", {}, blocking=True)
    assert len(manager.tasks) == 0

    await hass.config_entries.async_unload(entry.entry_id)
