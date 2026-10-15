# ⏱️ Delayed Tasks for Home Assistant

[![CI Test & Validate](https://github.com/SekulaTomasz/delayed-tasks-HA/actions/workflows/test.yml/badge.svg)](https://github.com/SekulaTomasz/delayed-tasks-HA/actions/workflows/test.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub release](https://img.shields.io/github/v/release/SekulaTomasz/delayed-tasks-HA)](https://github.com/SekulaTomasz/delayed-tasks-HA/releases)

A lightweight Home Assistant custom integration that allows you to easily create **one-off, deferred tasks** (e.g. *"turn on the garden sprinkler on Friday at 12:00"* or *"turn off the heater in 45 minutes"*).

Once executed, the task **automatically disappears**. All scheduled tasks are stored persistently, meaning they **survive Home Assistant restarts**!

---

## ✨ Features

* 📅 **One-off Tasks:** Execute any Home Assistant service/action at an exact datetime (`execute_at`) or after a relative duration (`delay`).
* 🧹 **Self-Cleaning:** Once executed, the task automatically deletes itself from storage and the queue.
* 💾 **Restart Survival (Persistence):** Tasks are persisted in Home Assistant storage (`Store`). If Home Assistant reboots before a task's target time, the task is restored and rescheduled seamlessly.
* 🔄 **Concurrency:** Schedule and track multiple independent one-off tasks simultaneously.
* 📊 **Sensor Entity (`sensor.oczekujace_zadania` / `sensor.delayed_tasks_oczekujace_zadania`):** Exposes the count of active pending tasks, along with the complete list and metadata in its attributes (perfect for Lovelace dashboard cards).
* 🎛️ **Service Actions:** Full control with `delayed_tasks.schedule_task`, `delayed_tasks.cancel_task`, and `delayed_tasks.clear_all`.
* 🔔 **Event Notifications:** Fires `delayed_task_executed` and `delayed_task_failed` events on Home Assistant's event bus.

---

## 📦 Installation

### Method 1: HACS (Recommended)
1. Open **HACS** in Home Assistant.
2. Go to **Integrations**, click the three-dots menu in the top right corner, and select **Custom repositories**.
3. Enter the repository URL: `https://github.com/SekulaTomasz/delayed-tasks-HA`
4. Select **Integration** as the category and click **Add**.
5. Find **Delayed Tasks** and click **Download**.
6. Restart Home Assistant.

### Method 2: Manual Installation
1. Download the `custom_components/delayed_tasks` directory.
2. Copy it into the `config/custom_components/delayed_tasks` folder of your Home Assistant installation.
3. Restart Home Assistant.

---

## ⚙️ Configuration

1. In Home Assistant, go to **Settings** -> **Devices & Services** -> **Add Integration**.
2. Search for **Delayed Tasks** and click to add it.

---

## 🛠️ Actions / Services

### 1. `delayed_tasks.schedule_task`
Schedules a new deferred task.

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `action` | String | Yes | Full Home Assistant service/action name (e.g. `switch.turn_on`, `light.turn_off`). |
| `name` | String | No | Friendly task name displayed in UI and sensor attributes. |
| `execute_at` | Datetime | No* | Exact execution datetime (e.g. `2026-10-16 12:00:00`). |
| `delay` | Duration | No* | Relative duration before execution (e.g. `01:30:00` or `minutes: 30`). |
| `target` | Object | No | Service target (`entity_id`, `device_id`, `area_id`). |
| `data` | Object | No | Additional parameters passed to the service (e.g. `{ "brightness": 255 }`). |
| `missed_action` | Select | No | `execute` (default) - execute immediately upon startup if the target time passed while HA was offline; `discard` - drop the task. |

*\* Either `execute_at` OR `delay` must be provided.*

### 2. `delayed_tasks.cancel_task`
Cancels an existing task by its ID.

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `task_id` | String | Yes | The 8-character task identifier. |

### 3. `delayed_tasks.clear_all`
Cancels and removes all currently pending one-off tasks.

---

## 💡 Usage Examples

### Example 1: Turn on a switch on Friday at 12:00
```yaml
action: delayed_tasks.schedule_task
data:
  name: "Turn on garden sprinklers on Friday"
  execute_at: "2026-10-16 12:00:00"
  action: switch.turn_on
  target:
    entity_id: switch.garden_sprinkler
```

### Example 2: Turn off lights in 30 minutes
```yaml
action: delayed_tasks.schedule_task
data:
  name: "Turn off hallway light in 30 min"
  delay:
    minutes: 30
  action: light.turn_off
  target:
    entity_id: light.hallway
```

### Example 3: Cancel a scheduled task
```yaml
action: delayed_tasks.cancel_task
data:
  task_id: "a1b2c3d4"
```

---

## 📱 Dashboard Card (Lovelace)

Using the `tasks` attribute of `sensor.delayed_tasks_oczekujace_zadania`, you can display all upcoming tasks in a neat table with a **Markdown card**:

```yaml
type: markdown
title: ⏳ Scheduled Tasks
content: >
  {% set entity_id = states.sensor | selectattr('attributes.tasks', 'defined') | map(attribute='entity_id') | first %}
  {% set tasks = state_attr(entity_id, 'tasks') if entity_id else [] %}
  {% if tasks and tasks | length > 0 %}
    | Time | Name | Action | ID |
    | :--- | :--- | :--- | :--- |
    {% for task in tasks %}
    | {{ as_timestamp(task.execute_at) | timestamp_custom('%b %d, %H:%M') }} | {{ task.name }} | `{{ task.action }}` | `{{ task.task_id }}` |
    {% endfor %}
  {% else %}
    _No pending scheduled tasks._
  {% endif %}
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
