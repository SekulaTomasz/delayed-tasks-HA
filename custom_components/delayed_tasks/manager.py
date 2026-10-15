"""Task manager handling scheduling, execution, and persistence."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ACTION,
    ATTR_DATA,
    ATTR_EXECUTE_AT,
    ATTR_NAME,
    ATTR_TARGET,
    ATTR_TASK_ID,
    CONF_MISSED_EXECUTE,
    SIGNAL_TASKS_UPDATED,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class ScheduledTask:
    """Represents a single deferred task."""

    def __init__(
        self,
        task_id: str,
        name: str,
        execute_at: datetime,
        action: str,
        target: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        missed_action: str = CONF_MISSED_EXECUTE,
    ) -> None:
        self.task_id = task_id
        self.name = name
        self.execute_at = execute_at
        self.action = action
        self.target = target or {}
        self.data = data or {}
        self.missed_action = missed_action
        self.unsub_timer: Callable[[], None] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary for storage and sensor attributes."""
        return {
            ATTR_TASK_ID: self.task_id,
            ATTR_NAME: self.name,
            ATTR_EXECUTE_AT: self.execute_at.isoformat(),
            ATTR_ACTION: self.action,
            ATTR_TARGET: self.target,
            ATTR_DATA: self.data,
            "missed_action": self.missed_action,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledTask:
        """Create a ScheduledTask from stored dictionary."""
        dt = dt_util.parse_datetime(data[ATTR_EXECUTE_AT])
        if dt is None:
            raise ValueError(f"Invalid datetime format: {data[ATTR_EXECUTE_AT]}")

        return cls(
            task_id=data[ATTR_TASK_ID],
            name=data.get(ATTR_NAME, "Zadanie"),
            execute_at=dt_util.as_utc(dt),
            action=data[ATTR_ACTION],
            target=data.get(ATTR_TARGET),
            data=data.get(ATTR_DATA),
            missed_action=data.get("missed_action", CONF_MISSED_EXECUTE),
        )


class TaskManager:
    """Manager for scheduling, executing, and persisting tasks."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.tasks: dict[str, ScheduledTask] = {}

    async def async_load(self) -> None:
        """Load stored tasks on startup and reschedule them."""
        data = await self._store.async_load()
        if not data or "tasks" not in data:
            return

        now = dt_util.utcnow()
        for task_dict in data.get("tasks", []):
            try:
                task = ScheduledTask.from_dict(task_dict)
                if task.execute_at <= now:
                    if task.missed_action == CONF_MISSED_EXECUTE:
                        _LOGGER.info("Executing overdue task: %s (%s)", task.name, task.task_id)
                        self.hass.async_create_task(self._async_execute_task(task))
                    else:
                        _LOGGER.info("Discarding overdue task: %s (%s)", task.name, task.task_id)
                    continue

                self.tasks[task.task_id] = task
                self._schedule_point_in_time(task)
            except Exception as err:
                _LOGGER.error("Failed to restore task: %s", err)

        await self._async_save()
        async_dispatcher_send(self.hass, SIGNAL_TASKS_UPDATED)

    async def async_add_task(
        self,
        action: str,
        name: str | None = None,
        execute_at: datetime | None = None,
        delay: timedelta | None = None,
        target: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        missed_action: str = CONF_MISSED_EXECUTE,
    ) -> str:
        """Add and schedule a new one-off task."""
        now = dt_util.utcnow()

        if execute_at is not None:
            target_dt = dt_util.as_utc(execute_at)
        elif delay is not None:
            target_dt = now + delay
        else:
            raise ValueError("Musisz podać 'execute_at' lub 'delay'.")

        if target_dt <= now:
            raise ValueError("Czas wykonania musi być w przyszłości.")

        task_id = str(uuid.uuid4())[:8]
        display_name = name or f"Zadanie ({action} @ {target_dt.strftime('%H:%M')})"

        task = ScheduledTask(
            task_id=task_id,
            name=display_name,
            execute_at=target_dt,
            action=action,
            target=target,
            data=data,
            missed_action=missed_action,
        )

        self.tasks[task_id] = task
        self._schedule_point_in_time(task)

        await self._async_save()
        async_dispatcher_send(self.hass, SIGNAL_TASKS_UPDATED)
        _LOGGER.info("Zadanie %s (%s) zaplanowane na %s", task.name, task_id, target_dt)
        return task_id

    async def async_cancel_task(self, task_id: str) -> bool:
        """Cancel an existing task."""
        task = self.tasks.pop(task_id, None)
        if not task:
            return False

        if task.unsub_timer:
            task.unsub_timer()

        await self._async_save()
        async_dispatcher_send(self.hass, SIGNAL_TASKS_UPDATED)
        _LOGGER.info("Anulowano zadanie %s", task_id)
        return True

    async def async_clear_all(self) -> None:
        """Clear and cancel all tasks."""
        for task in self.tasks.values():
            if task.unsub_timer:
                task.unsub_timer()
        self.tasks.clear()
        await self._async_save()
        async_dispatcher_send(self.hass, SIGNAL_TASKS_UPDATED)

    def _schedule_point_in_time(self, task: ScheduledTask) -> None:
        """Register the timer callback in Home Assistant."""
        def _callback(_now: datetime) -> None:
            self.hass.async_create_task(self._async_execute_task(task))

        task.unsub_timer = async_track_point_in_time(self.hass, _callback, task.execute_at)

    async def _async_execute_task(self, task: ScheduledTask) -> None:
        """Execute the action and remove the task."""
        _LOGGER.info("Uruchamianie jednorazowego zadania: %s (%s)", task.name, task.task_id)

        try:
            if "." not in task.action:
                raise ValueError(f"Nieprawidłowa nazwa akcji: {task.action}")

            domain, service = task.action.split(".", 1)

            await self.hass.services.async_call(
                domain=domain,
                service=service,
                service_data=task.data,
                target=task.target,
                blocking=True,
            )

            self.hass.bus.async_fire(
                "delayed_task_executed",
                {"task_id": task.task_id, "name": task.name, "action": task.action},
            )
        except Exception as err:
            _LOGGER.error("Błąd podczas wykonywania zadania %s: %s", task.task_id, err)
            self.hass.bus.async_fire(
                "delayed_task_failed",
                {"task_id": task.task_id, "name": task.name, "error": str(err)},
            )
        finally:
            self.tasks.pop(task.task_id, None)
            await self._async_save()
            async_dispatcher_send(self.hass, SIGNAL_TASKS_UPDATED)

    async def _async_save(self) -> None:
        """Persist pending tasks to storage."""
        data = {"tasks": [t.to_dict() for t in self.tasks.values()]}
        await self._store.async_save(data)
