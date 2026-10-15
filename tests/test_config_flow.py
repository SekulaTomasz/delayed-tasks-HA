"""Test the Delayed Tasks config flow."""
import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.delayed_tasks.const import DOMAIN


async def test_flow_user_step_creates_entry(hass: HomeAssistant) -> None:
    """Test standard user step creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Delayed Tasks"
    assert result2["data"] == {}


async def test_flow_single_instance_abort(hass: HomeAssistant) -> None:
    """Test that creating a second entry is aborted."""
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Delayed Tasks",
        data={},
        source=config_entries.SOURCE_USER,
    )
    hass.config_entries._entries[entry.entry_id] = entry

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
