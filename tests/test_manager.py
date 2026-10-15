"""Test the Delayed Tasks manager."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.delayed_tasks.const import (
    CONF_MISSED_DISCARD,
    CONF_MISSED_EXECUTE,
)
from custom_components.delayed_tasks.manager import ScheduledTask, TaskManager


def test_scheduled_task_serialization() -> None:
    """Test ScheduledTask serialization and deserialization."""
    now = dt_util.utcnow()
    task = ScheduledTask(
        task_id="abc12345",
        name="Test Task",
        execute_at=now,
        action="switch.turn_on",
        target={"entity_id": "switch.test"},
        data={"param": 1},
        missed_action=CONF_MISSED_EXECUTE,
    )
    task_dict = task.to_dict()
    assert task_dict["task_id"] == "abc12345"
    assert task_dict["name"] == "Test Task"
    assert task_dict["execute_at"] == now.isoformat()
    assert task_dict["action"] == "switch.turn_on"

    restored = ScheduledTask.from_dict(task_dict)
    assert restored.task_id == task.task_id
    assert restored.name == task.name
    assert restored.execute_at == task.execute_at
    assert restored.action == task.action
    assert restored.target == task.target
    assert restored.data == task.data


def test_scheduled_task_invalid_datetime() -> None:
    """Test ScheduledTask with invalid datetime string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid datetime format"):
        ScheduledTask.from_dict({
            "task_id": "1",
            "execute_at": "invalid-date",
            "action": "switch.turn_on",
        })


async def test_add_task_with_delay(hass: HomeAssistant) -> None:
    """Test adding a task with a delay."""
    manager = TaskManager(hass)
    task_id = await manager.async_add_task(
        action="switch.turn_on",
        name="Delayed Switch",
        delay=timedelta(minutes=15),
        target={"entity_id": "switch.test"},
    )

    assert len(task_id) == 8
    assert task_id in manager.tasks
    task = manager.tasks[task_id]
    assert task.name == "Delayed Switch"
    assert task.action == "switch.turn_on"
    assert task.unsub_timer is not None

    await manager.async_clear_all()


async def test_add_task_with_execute_at(hass: HomeAssistant) -> None:
    """Test adding a task with an absolute execute_at datetime."""
    manager = TaskManager(hass)
    future_time = dt_util.utcnow() + timedelta(hours=2)

    task_id = await manager.async_add_task(
        action="light.turn_off",
        execute_at=future_time,
        target={"entity_id": "light.living_room"},
    )

    assert task_id in manager.tasks
    task = manager.tasks[task_id]
    assert task.execute_at == future_time

    await manager.async_clear_all()


async def test_add_task_validation_errors(hass: HomeAssistant) -> None:
    """Test validation errors when adding tasks."""
    manager = TaskManager(hass)

    # Missing both execute_at and delay
    with pytest.raises(ValueError, match="Musisz podać 'execute_at' lub 'delay'"):
        await manager.async_add_task(action="switch.turn_on")

    # Time in the past
    past_time = dt_util.utcnow() - timedelta(minutes=5)
    with pytest.raises(ValueError, match="Czas wykonania musi być w przyszłości"):
        await manager.async_add_task(action="switch.turn_on", execute_at=past_time)


async def test_cancel_task(hass: HomeAssistant) -> None:
    """Test cancelling a task."""
    manager = TaskManager(hass)
    task_id = await manager.async_add_task(
        action="switch.turn_on",
        delay=timedelta(minutes=10),
    )

    assert task_id in manager.tasks
    cancelled = await manager.async_cancel_task(task_id)
    assert cancelled is True
    assert task_id not in manager.tasks

    # Cancelling again returns False
    assert await manager.async_cancel_task(task_id) is False


async def test_clear_all_tasks(hass: HomeAssistant) -> None:
    """Test clearing all scheduled tasks."""
    manager = TaskManager(hass)
    await manager.async_add_task(action="switch.turn_on", delay=timedelta(minutes=5))
    await manager.async_add_task(action="switch.turn_off", delay=timedelta(minutes=10))

    assert len(manager.tasks) == 2
    await manager.async_clear_all()
    assert len(manager.tasks) == 0


async def test_async_execute_task_success(hass: HomeAssistant) -> None:
    """Test successful task execution and self-cleanup."""
    manager = TaskManager(hass)
    task_id = await manager.async_add_task(
        action="test.service",
        delay=timedelta(minutes=10),
        data={"key": "val"},
    )
    task = manager.tasks[task_id]

    events = []
    hass.bus.async_listen("delayed_task_executed", lambda e: events.append(e))

    with patch.object(hass.services, "async_call", new_callable=AsyncMock) as mock_call:
        await manager._async_execute_task(task)
        mock_call.assert_called_once_with(
            domain="test",
            service="service",
            service_data={"key": "val"},
            target={},
            blocking=True,
        )

    await hass.async_block_till_done()

    assert task_id not in manager.tasks
    assert len(events) == 1
    assert events[0].data["task_id"] == task_id


async def test_async_execute_task_failure_handles_gracefully(hass: HomeAssistant) -> None:
    """Test task execution failure fires failed event and still cleans up."""
    manager = TaskManager(hass)
    task_id = await manager.async_add_task(
        action="test.broken_service",
        delay=timedelta(minutes=10),
    )
    task = manager.tasks[task_id]

    fail_events = []
    hass.bus.async_listen("delayed_task_failed", lambda e: fail_events.append(e))

    with patch.object(
        hass.services, "async_call", side_effect=RuntimeError("Connection lost")
    ):
        await manager._async_execute_task(task)

    await hass.async_block_till_done()

    assert task_id not in manager.tasks
    assert len(fail_events) == 1
    assert fail_events[0].data["task_id"] == task_id
    assert "Connection lost" in fail_events[0].data["error"]


async def test_async_load_restores_future_and_overdue_tasks(hass: HomeAssistant) -> None:
    """Test loading stored tasks on startup."""
    manager = TaskManager(hass)
    now = dt_util.utcnow()

    future_task = ScheduledTask(
        task_id="future1",
        name="Future Task",
        execute_at=now + timedelta(hours=1),
        action="switch.turn_on",
    )
    overdue_exec_task = ScheduledTask(
        task_id="overdue1",
        name="Overdue Exec Task",
        execute_at=now - timedelta(minutes=10),
        action="switch.turn_on",
        missed_action=CONF_MISSED_EXECUTE,
    )
    overdue_discard_task = ScheduledTask(
        task_id="overdue2",
        name="Overdue Discard Task",
        execute_at=now - timedelta(minutes=10),
        action="switch.turn_on",
        missed_action=CONF_MISSED_DISCARD,
    )

    fake_data = {
        "tasks": [
            future_task.to_dict(),
            overdue_exec_task.to_dict(),
            overdue_discard_task.to_dict(),
        ]
    }

    with patch.object(manager._store, "async_load", return_value=fake_data), \
         patch.object(manager, "_async_execute_task", new_callable=AsyncMock) as mock_exec:
        await manager.async_load()

        assert "future1" in manager.tasks
        assert manager.tasks["future1"].unsub_timer is not None

        mock_exec.assert_called_once()
        assert mock_exec.call_args[0][0].task_id == "overdue1"
        assert "overdue2" not in manager.tasks

    await manager.async_clear_all()
