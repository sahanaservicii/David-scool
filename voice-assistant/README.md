# Свободный Голос (FreeVoice Assistant)

Локальный голосовой/чат-ассистент для домашнего сервера: **оффлайн-first**, без подписок, с интеграцией **Home Assistant** и **мультирум-контекстом** (комнаты/спутники/музыка по комнатам).

- Версия: **0.3.0**
- Язык: Python 3.10+ (ядро на stdlib), SQLite, Web UI/API
- Среда: Linux (рекомендуется Debian 12 / Ubuntu Server 24.04 LTS) в локальной сети

## Возможности

- **Чат и навыки:** время/дата, таймеры, заметки, калькулятор, системный статус, поиск (DDG HTML/SearXNG, без ключей), погода, homelab-команды.
- **Умный дом (Home Assistant):** статус, запрос состояний/датчиков, управление устройствами, **мультирум-медиа** (play/pause/stop/next/prev/volume, запуск музыки по запросу) через HA REST API. Best-effort поддержка Music Assistant (`music_assistant/mass.play_media`) и `media_player.play_media`.
- **Мультирум:** комнаты в конфиге (`rooms[]`) с `media_player`, `tts_player`, `satellite_id`, алиасами; выбор комнаты в UI/API; разрешение комнаты по тексту («в кухне»), контексту и спутнику.
- **Спутники (satellites):** HTTP API `POST /api/satellite` для ping/utterance от комнатных микрофонных узлов (wake-word+STT на спутнике → текст в FreeVoice → `speak`/подсказки вывода).
- **Локальный LLM (опционально):** OpenAI-compatible endpoint (Ollama/llama.cpp и т.п.) для свободного диалога.
- **Web UI:** чат, голосовой ввод/озвучка через Web Speech API браузера, выбор комнаты, статус.
- **Android-клиент:** WebView APK (`com.freevoice.assistant`), подключается к серверу FreeVoice (не standalone ассистент).

> HA, LLM, STT/TTS-сервер и «всегда слушающие» спутники разворачиваются отдельно на целевом железе. При недоступности HA/LLM ассистент отвечает диагностикой, без падений.

## Быстрый старт

```bash
cd /root/workspace/voice-assistant
python3 -m unittest discover -s tests -v
python3 main.py --web --host 127.0.0.1 --port 8765
# Web UI: http://127.0.0.1:8765
```

CLI:
```bash
python3 main.py
```

## Конфигурация

- Базовая: `config/config.json`
- Локальная (переопределяет): `config/config.local.json` (не коммитить секреты) — шаблон: `config/config.local.example.json`
- Env-переменные: `ASSISTANT_HOST`, `ASSISTANT_PORT`, `HASS_URL`, `HASS_TOKEN`, `HOMELAB_SECRETS_FILE`, `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`

Ключевые секции:
- `home_assistant`: `url`, `token` или `secrets_file` (по умолчанию `~/.config/opencode/secrets/homelab.env`, ключ `HASS_TOKEN`)
- `llm.openai_compat`: `base_url`, `model`, `api_key`, таймауты
- `rooms[]`: `id`, `name`, `aliases`, `satellite_id`, `media_player`, `tts_player`
- `music.music_assistant.enabled`: предпочтение MA-сервисов для воспроизведения
- `server`: `host/port/allow_lan/api_token`

## API

- `GET /api/health` — быстрый статус (без сетевых проб)
- `GET /api/status?quick=0` — полный статус (включая проверку HA)
- `GET /api/rooms` — комнаты и их медиа/спутники
- `POST /api/chat` — `{"text":"...", "session_id":"...", "room":"kitchen", "satellite_id":"sat_kitchen"}`
- `POST /api/satellite` — `{"type":"ping|utterance", "satellite_id":"...", "room":"...", "text":"..."}`

При `server.api_token` для POST требуется `Authorization: Bearer <token>` или `X-Api-Token`.

## Мультирум-музыка и музыкальный терминал

- **Веб-терминал:** `/music` — комнаты, состояние плееров HA, управление (play/pause/stop/next/prev/volume), запуск радио/пресетов архива (`GET/POST /api/music`).
- Подробная архитектура, конфигурация комнат, протокол спутников, Music Assistant, требования к серверу и план: **[docs/MULTIROOM_HA.md](docs/MULTIROOM_HA.md)**.
- Бюджетные колонки и схема подключения: **[docs/HARDWARE_SPEAKERS_BUDGET.md](docs/HARDWARE_SPEAKERS_BUDGET.md)**.

Примеры команд:
- «включи музыку в этой комнате», «включи джаз в гостиной», «пауза», «громче», «следующий трек»
- «какая температура в спальне», «включи свет в кухне»

## Развёртывание

См. **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** и `deploy/freevoice.service`.

Минимум для продакшена: выделенный сервер в LAN (рекомендуется 6–8 CPU, 32 GB RAM, NVMe, Debian/Ubuntu), Home Assistant, локальная LLM (Ollama/llama.cpp), при необходимости STT/TTS (faster-whisper/Piper) и спутники по комнатам.

## Android APK

- Проект: `android-app/` (Gradle), ручная сборка: `android-app/build-manual-apk.sh`
- Готовые артефакты (если собраны): `dist/FreeVoice-debug.apk`, `assistant/web/static/FreeVoice-debug.apk`
- APK — WebView-клиент к серверу; укажите URL сервера в приложении.

## Тесты

```bash
python3 -m py_compile $(find assistant -name '*.py') main.py tests/test_core.py tests/test_multiroom.py
python3 -m unittest discover -s tests -v
```

## Документация

- [docs/MULTIROOM_HA.md](docs/MULTIROOM_HA.md) — мультирум, HA, музыка, спутники, железо/ПО, план внедрения
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — архитектура модулей
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — развёртывание, безопасность, ограничения
- [SECURITY.md](SECURITY.md) — модель безопасности

## Ограничения

- Свободный диалог «как в чате» требует настроенный локальный LLM endpoint.
- Реальные действия в HA требуют доступный HA и корректный токен/`entity_id`.
- Качество воспроизведения по названию зависит от HA/Music Assistant и провайдеров.
- «Всегда слушать» в комнатах обеспечивают спутники (отдельное железо/ПО), сервер предоставляет маршрутизацию и навыки.
