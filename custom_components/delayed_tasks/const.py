"""Constants for the Delayed Tasks integration."""
from typing import Final

DOMAIN: Final = "delayed_tasks"
STORAGE_KEY: Final = f"{DOMAIN}_tasks"
STORAGE_VERSION: Final = 1

SIGNAL_TASKS_UPDATED: Final = f"{DOMAIN}_tasks_updated"

ATTR_TASK_ID: Final = "task_id"
ATTR_NAME: Final = "name"
ATTR_EXECUTE_AT: Final = "execute_at"
ATTR_DELAY: Final = "delay"
ATTR_ACTION: Final = "action"
ATTR_TARGET: Final = "target"
ATTR_DATA: Final = "data"
ATTR_MISSED_ACTION: Final = "missed_action"

CONF_MISSED_EXECUTE: Final = "execute"
CONF_MISSED_DISCARD: Final = "discard"
