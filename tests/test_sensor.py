"""Test Delayed Tasks sensor platform."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.delayed_tasks.const import DOMAIN


async def test_sensor_state_and_attributes(hass: HomeAssistant) -> None:
    """Test the pending tasks count sensor and task list attributes."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Delayed Tasks",
        data={},
        entry_id="test_sensor_entry",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.delayed_tasks.manager.Store.async_load",
        return_value={"tasks": []},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    manager = hass.data[DOMAIN][entry.entry_id]

    sensors = hass.states.async_entity_ids("sensor")
    assert len(sensors) == 1
    sensor_entity_id = sensors[0]

    state = hass.states.get(sensor_entity_id)
    assert state is not None
    assert state.state == "0"
    assert state.attributes["tasks"] == []

    # Add a task
    task_id = await manager.async_add_task(
        action="switch.turn_on",
        name="Turn on switch",
        delay=timedelta(minutes=5),
        target={"entity_id": "switch.bedroom"},
    )
    await hass.async_block_till_done()

    state = hass.states.get(sensor_entity_id)
    assert state.state == "1"
    tasks = state.attributes["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == task_id
    assert tasks[0]["name"] == "Turn on switch"

    # Cancel task
    await manager.async_cancel_task(task_id)
    await hass.async_block_till_done()

    state = hass.states.get(sensor_entity_id)
    assert state.state == "0"
    assert state.attributes["tasks"] == []

    await hass.config_entries.async_unload(entry.entry_id)
