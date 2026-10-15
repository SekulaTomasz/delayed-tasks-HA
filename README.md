# ⏱️ Delayed Tasks (Home Assistant Custom Integration)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub release](https://img.shields.io/github/v/release/SekulaTomasz/delayed-tasks-HA)](https://github.com/SekulaTomasz/delayed-tasks-HA/releases)

Integracja dla **Home Assistant** umożliwiająca łatwe tworzenie **jednorazowych zadań odłożonych w czasie** (np. *„włącz przełącznik w piątek o 12:00”* lub *„wyłącz grzejnik za 45 minut”*). 

Po zrealizowaniu akcji zadanie **automatycznie znika**. Wszystkie zaplanowane zadania są trwale zapisywane, dzięki czemu **przetrwają restart Home Assistanta**!

---

## ✨ Główne cechy

* 📅 **Zadania jednorazowe:** Wykonanie dowolnej usługi Home Assistant w ściśle określonym czasie (`execute_at`) lub z relatywnym opóźnieniem (`delay`).
* 🧹 **Samoczynne sprzątanie (Self-cleanup):** Po poprawnym wykonaniu akcji zadanie jest automatycznie usuwane z kolejki i pamięci.
* 💾 **Odporność na restarty (Persistence):** Zadania są zapisywane w magazynie HA (`Store`). Jeśli Home Assistant zrestartuje się przed nadejściem wyznaczonej godziny, zadanie nie przepadnie.
* 🔄 **Wielozadaniowość:** Możliwość równoległego planowania wielu różnych zadań.
* 📊 **Encja stanu (`sensor.delayed_tasks_oczekujace_zadania`):** Pokazuje liczbę oczekujących zadań, a w swoich atrybutach udostępnia pełną listę z detalami (do wyświetlenia na Dashboardzie).
* 🎛️ **Zarządzanie:** Usługi `delayed_tasks.schedule_task`, `delayed_tasks.cancel_task` oraz `delayed_tasks.clear_all`.
* 🔔 **Zdarzenia na szynie zdarzeń:** Emisja zdarzeń `delayed_task_executed` oraz `delayed_task_failed` po zakończeniu zadania.

---

## 📦 Instalacja

### Metoda 1: HACS (Zalecana)
1. Otwórz **HACS** w Home Assistant.
2. Przejdź do **Integrations**, kliknij trzy kropki w prawym górnym rogu i wybierz **Custom repositories**.
3. Wklej adres repozytorium: `https://github.com/SekulaTomasz/delayed-tasks-HA`
4. Jako kategorię wybierz **Integration** i kliknij **Add**.
5. Wyszukaj **Delayed Tasks** i kliknij **Download**.
6. Zrestartuj Home Assistant.

### Metoda 2: Ręczna
1. Pobierz zawartość katalogu `custom_components/delayed_tasks`.
2. Skopiuj go do katalogu `config/custom_components/delayed_tasks` w Twojej instalacji Home Assistant.
3. Zrestartuj Home Assistant.

---

## ⚙️ Konfiguracja

1. W Home Assistant przejdź do: **Ustawienia** -> **Urządzenia oraz usługi** -> **Dodaj integrację**.
2. Wyszukaj **Delayed Tasks** i kliknij, aby zatwierdzić.

---

## 🛠️ Dostępne Usługi (Actions)

### 1. `delayed_tasks.schedule_task`
Planuje nowe zadanie.

| Pole | Typ | Wymagane | Opis |
| :--- | :--- | :---: | :--- |
| `action` | String | Tak | Pełna nazwa usługi HA (np. `switch.turn_on`, `light.turn_off`). |
| `name` | String | Nie | Przyjazna nazwa zadania (np. *"Włączenie pompy"*). |
| `execute_at` | Datetime | Nie* | Dokładna data i godzina (np. `2026-10-16 12:00:00`). |
| `delay` | Duration | Nie* | Relatywne opóźnienie (np. `01:30:00` lub `minutes: 30`). |
| `target` | Object | Nie | Cel usługi (np. `entity_id`, `device_id`, `area_id`). |
| `data` | Object | Nie | Dodatkowe parametry dla usługi (np. `{ "brightness": 255 }`). |
| `missed_action` | Select | Nie | `execute` (domyślnie) - wykonaj po starcie, jeśli czas minął podczas restartu HA; `discard` - odrzuć. |

*\* Wymagane jest podanie `execute_at` LUB `delay`.*

### 2. `delayed_tasks.cancel_task`
Anuluje wyznaczone zadanie.

| Pole | Typ | Wymagane | Opis |
| :--- | :--- | :---: | :--- |
| `task_id` | String | Tak | 8-znakowy identyfikator zadania. |

### 3. `delayed_tasks.clear_all`
Anuluje wszystkie oczekujące zadania jednorazowe.

---

## 💡 Przykłady użycia

### Przykład 1: Włączenie przełącznika w piątek o 12:00
```yaml
action: delayed_tasks.schedule_task
data:
  name: "Włącz zraszacz w piątek"
  execute_at: "2026-10-16 12:00:00"
  action: switch.turn_on
  target:
    entity_id: switch.ogrod_zraszacz
```

### Przykład 2: Wyłączenie światła za 30 minut
```yaml
action: delayed_tasks.schedule_task
data:
  name: "Wyłącz światło w korytarzu"
  delay:
    minutes: 30
  action: light.turn_off
  target:
    entity_id: light.korytarz
```

---

## 📱 Karta na Dashboardzie (Lovelace)

Dzięki atrybutowi `tasks` w encji `sensor.delayed_tasks_oczekujace_zadania`, możesz w łatwy sposób wyświetlić oczekującą listę na dashboardzie za pomocą karty **Markdown**:

```yaml
type: markdown
title: ⏳ Zaplanowane zadania
content: >
  {% set tasks = state_attr('sensor.delayed_tasks_oczekujace_zadania', 'tasks') %}
  {% if tasks and tasks | length > 0 %}
    | Czas | Nazwa | Akcja | ID |
    | :--- | :--- | :--- | :--- |
    {% for task in tasks %}
    | {{ as_timestamp(task.execute_at) | timestamp_custom('%d.%m %H:%M') }} | {{ task.name }} | `{{ task.action }}` | `{{ task.task_id }}` |
    {% endfor %}
  {% else %}
    _Brak zaplanowanych zadań jednorazowych._
  {% endif %}
```

---

## 📄 Licencja

Projekt udostępniony na licencji [MIT](LICENSE).
