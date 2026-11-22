# Навыки (Skills)

Навык — модуль, обрабатывающий одно или несколько намерений (intents) и возвращающий ответ.

## Интерфейс
```python
from assistant.skills.base import Skill
from assistant.nlu.intents import IntentResult, SkillResponse

class MySkill(Skill):
    name = "my_skill"
    description = "Что делает навык"
    intents = ["my_intent"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        return SkillResponse(text="Ответ", speak="Текст для озвучки", data={})
```

- `intent.entities` — извлечённые параметры (слоты).
- `ctx` — контекст диалога (история, язык, pending/slots).
- `self.storage` — локальное хранилище (заметки, таймеры, kv, история).
- `self.cfg` — конфигурация.

## Добавление навыка
1. Создать `assistant/skills/my_skill.py` с классом-наследником `Skill`.
2. Добавить правила распознавания в `assistant/nlu/router.py` (`add(intent, skill, patterns, extractor=...)`).
3. Зарегистрировать в `assistant/core/engine.py` (`_register_skills`) и, при желании, в `config.skills.enabled`.
4. (Опционально) добавить тест в `tests/`.

## Встроенные навыки
| Навык | Интенты | Описание |
|---|---|---|
| smalltalk | greeting, how_are_you, who_are_you, thanks, goodbye | Базовый диалог |
| time | time_now, date_today | Время и дата |
| calc | calc | Безопасный калькулятор |
| notes | note_add, note_list, note_find | Заметки (SQLite) |
| timer | timer_set, timer_list, timer_cancel | Таймеры (SQLite) |
| search | search, fallback* | Поиск без подписки (онлайн) + локальный fallback |
| weather | weather | Погода через открытый источник (онлайн) |
| system | system_info | Статус ОС/ресурсов |
| homelab | homelab | Мост к `homelab.py` |
| web | open_url | Открытие ссылки (для клиента) |
| app_control | app_open | Запуск приложений (allowlist) |
| help | help | Справка |
| fallback | fallback | LLM (опц.) → поиск → подсказка |

## Идеи навыков (roadmap)
- Напоминания по дате/времени, календарь (локальный CalDAV/ICS).
- Музыка/медиа (локальные файлы, MPC/MPD).
- Умный дом: прямые вызовы Home Assistant API / MQTT (локально).
- Новости/RSS (без аккаунтов), чтение вслух.
- Рутины: «доброе утро» = погода + календарь + новости.
- Словарь/перевод (офлайн-словари), конвертер величин.
- Файлы/документы: поиск по локальной папке заметок.
