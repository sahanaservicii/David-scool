# Архитектура FreeVoice (v0.3.0)

## Обзор

`FreeVoice` — модульный оффлайн-first ассистент для домашнего сервера: текст/голос (через UI-клиент), NLU маршрутизация, навыки, интеграции (Home Assistant, поиск, homelab), мультирум-контекст и HTTP API для Web/Android/спутников.

```
[Web UI / Android APK / Satellite] --HTTP--> [assistant.web.server]
                                                  |
                                                  v
                                          [assistant.core.engine]
                                            |   |    |      |
                                     router | config rooms storage
                                            |   |    |
                                            v   v    v
                                         [skills/*]  [integrations/*]
                                            |            |
                                            +--> HA REST / LLM / Search / Homelab
```

## Основные модули

- `assistant/core/config.py` — загрузка `config/config.json` + `config/config.local.json` + env overrides (server/HA/LLM).
- `assistant/core/rooms.py` — нормализация комнат, разрешение комнаты по id/alias/тексту/контексту/`satellite_id`, сводка для API.
- `assistant/core/context.py` — контекст диалога/сессии (история, слоты: `room`, `room_name`, `room_media_player`, `satellite_id`).
- `assistant/core/engine.py` — оркестрация: контекст/комната, таймеры, NLU, dispatch навыков, fallback, ответ (`text/speak/room/satellite/data`), статус.
- `assistant/core/storage.py` — SQLite: заметки, таймеры, история (опционально).
- `assistant/nlu/router.py` — rule-based интенты + извлечение сущностей (время, таймеры, заметки, поиск, HA/media/control, homelab и др.).
- `assistant/skills/*` — навыки (smalltalk/time/calc/notes/timer/weather/system/search/homelab/web/app/ha/fallback/help).
  - `ha_skill.py`: статус HA, запрос состояний/датчиков, управление устройствами, мультирум-медиа (выбор `media_player` по комнате, play/pause/stop/next/prev/volume, best-effort play_media для HA/Music Assistant).
  - `fallback_skill.py`: локальный LLM (OpenAI-compatible) при настройке, иначе поиск/подсказка.
- `assistant/integrations/homeassistant.py` — HA REST клиент, обнаружение URL (config/env/homelab.json), токен из env/config/secrets_file, safe_status, поиск/разрешение сущностей.
- `assistant/llm/provider.py`, `assistant/stt/base.py`, `assistant/tts/base.py`, `assistant/search/provider.py` — провайдерные абстракции/реализации.
- `assistant/web/server.py` — HTTP сервер (ThreadingHTTPServer): статика, JSON API, лимиты/валидация, опциональный API token.
- `assistant/web/static/*` — Web UI (чат, выбор комнаты, browser STT/TTS) и музыкальный терминал (`/music`, `music.html/js`).
- `android-app/` — WebView-клиент к серверу.

## Поток запроса (чат/спутник)

1. Клиент вызывает `POST /api/chat` или `POST /api/satellite` (`text`, `session_id`, `room`/`satellite_id`).
2. Сервер валидирует размер/поля и auth (если токен настроен), вызывает `engine.process(...)`.
3. Engine нормализует комнаты, определяет активную комнату (satellite → hint → text → context), обновляет контекст/метаданные.
4. Router определяет intent/skill/entities; engine дополняет room/satellite в entities.
5. Skill выполняет действие (локально или через интеграцию, напр. HA) и возвращает `SkillResponse`.
6. Engine формирует ответ: `text`, `speak`, intent/skill, `room` summary, `satellite`, `data`. `/api/satellite` добавляет `satellite_hints`.

## Мультирум и музыка

- Источник правды по комнатам: `config.rooms[]` (нормализуется в `core.rooms`).
- Комната определяет целевые `media_player`/`tts_player` и привязку `satellite_id`.
- Медиа-команды маршрутизируются в `ha` skill (`media_control`), который:
  - выбирает плеер комнаты (config → поиск сущности в HA),
  - вызывает транспорт/громкость сервисы HA,
  - для «включи <запрос>» пробует MA/HA `play_media` сервисы (best-effort, зависит от провайдеров).
- Дальнейшая координация TTS↔музыка (ducking/resume) и always-listening — ответственность спутников/voice-pipeline (см. `docs/MULTIROOM_HA.md`).

## API (основное)

- `GET /api/health` — без сетевых проб
- `GET /api/status?quick=0` — статус + HA probe
- `GET /api/rooms` — комнаты (summary)
- `GET /api/music` (или `/api/music/status?room=`), `GET /api/music/config` — состояние музыки/пресеты
- `POST /api/music` — управление воспроизведением по комнате (HA media_player)
- `POST /api/chat` — обработка текста
- `POST /api/satellite` — `ping|hello|utterance` от спутника

## Расширение

- Новый навык: наследовать `Skill`, зарегистрировать в `engine._register_skills`, добавить intents/правила в router при необходимости.
- Новая интеграция: модуль в `assistant/integrations/`, вызывать из навыка с graceful-ошибками.
- Комнаты/спутники: расширять `core.rooms` и конфиг-схему; сохранять обратную совместимость `id/name/aliases/media_player`.

## Ограничения

- NLU rule-based (LLM усиливает fallback-диалог, но не заменяет детерминированные навыки для управления).
- Реальная музыка/устройства зависят от доступности HA, корректных entity_id и провайдеров MA.
- Серверный STT/TTS и wake-word не встроены как единый daemon в репозитории; предусмотрены интерфейсы/интеграционные точки.
