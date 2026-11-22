# Мультирум голосовой помощник + Home Assistant (локально, без подписок)

Этот документ описывает целевую и практическую архитектуру «Свободный Голос» (FreeVoice) как **полностью локального** голосового ассистента на домашнем сервере: диалог + управление умным домом + микрофоны/колонки в каждой комнате + музыка по комнатам.

> Статус в репозитории (v0.3.0): сервер/движок, Web UI/API, навык Home Assistant, мультирум-контекст (комнаты, `media_player`/`tts_player`, `satellite_id`), маршрутизация музыки по комнатам через HA/MA (best-effort), HTTP API для спутников (`/api/satellite`), Android WebView-клиент.  
> Для «всегда слушающих» спутников (wake-word), серверного STT/TTS и локального LLM в продакшене требуется развёртывание компонентов на выделенном сервере и/или спутниках (ниже). Всё — локально и без подписок.

## 1. Целевая архитектура

```
[Комната: satellite]
  ├─ микрофон + wake-word (openWakeWord/Porcupine-local/ESPHome)
  ├─ STT (локально на спутнике или на сервере: whisper.cpp/faster-whisper)
  └─ динамик/TTS-вывод (Piper или системный TTS) / media_player в HA
        │  LAN (HTTP/Wyoming/MQTT)
        ▼
[Сервер FreeVoice]
  ├─ API: /api/chat, /api/satellite, /api/rooms, /api/status
  ├─ NLU + навыки (время, таймеры, заметки, поиск, умный дом, мультирум-музыка)
  ├─ LLM (локально): Ollama / llama.cpp (OpenAI-compatible)
  └─ Интеграция: Home Assistant REST API (+ Music Assistant для музыки)
        │  LAN
        ▼
[Home Assistant]
  ├─ устройства (свет, датчики, климат, сценарии)
  ├─ media_player по комнатам (колонки/TV/AVR/Sonos/MA players)
  └─ Music Assistant (локальная библиотека, радио, очереди, группы комнат)
```

### Режимы спутников (satellites)
- **Режим A (рекомендуется для качества):** спутник делает wake-word + STT локально и отправляет распознанный текст в `POST /api/satellite` с `satellite_id`/`room`. Ответ (`speak`) озвучивается локально (Piper) или через `tts_player` в HA.
- **Режим B (тонкий клиент):** спутник шлёт аудио в voice-стек (Wyoming/отдельный STT-сервис), который передаёт текст в FreeVoice. Интеграция на уровне оркестрации (HA Voice / Rhasspy / кастом).
- **Режим C (браузер/телефон как спутник):** Web UI/APK использует Web Speech API браузера для STT/TTS и вызывает `/api/chat` с выбранной `room`.

Текущий FreeVoice готов как центральный HTTP-движок для режимов A/C и как backend-логика для режима B.

## 2. Что уже реализовано в коде (готово к переносу)

- **Музыкальный веб-терминал:** `/music` (`music.html/js`) + API `GET/POST /api/music`, `GET /api/music/config` — просмотр комнат и состояния `media_player` (через HA), пресеты радио/архива, управление воспроизведением по комнате (graceful при недоступном HA/не настроенных плеерах).

- **Комнаты и контекст:** `config.rooms[]` (id/name/aliases/satellite_id/media_player/tts_player), определение комнаты по `room` в запросе, `satellite_id`, контексту сессии и тексту («в кухне», «здесь»).
- **API:**
  - `GET /api/health` — быстрый health-check (без сетевых проб).
  - `GET /api/status?quick=0` — статус + HA/LLM/skills/комнаты.
  - `GET /api/rooms` — список комнат с целевыми `media_player`/`tts_player`/`satellite_id`.
  - `POST /api/chat` — `{text, session_id?, room?, satellite_id?}` → ответ + `room`, `speak`, `data`.
  - `POST /api/satellite` — события спутника: `type=ping|hello|utterance`, `{satellite_id, room, text|transcript, session_id}`; для utterance возвращает ответ чата + `satellite_hints` (куда озвучивать/какой player).
- **Home Assistant навык:** статус HA, запрос состояний/датчиков, управление устройствами, мультирум-медиа (play/pause/stop/next/prev/volume), выбор `media_player` по комнате, best-effort воспроизведение по запросу (HA `media_player.play_media` и, при наличии, `music_assistant/mass.play_media`).
- **UI:** выбор комнаты, отображение `media_player`/satellite в контексте, голосовой ввод/озвучка в браузере.
- **Конфиг:** `config/config.local.json` (переопределяет `config.json`), env-переменные для HA/LLM/server.

## 3. Конфигурация комнат, спутников и музыки

Пример (`config/config.local.json`, см. `config/config.local.example.json`):

```json
{
  "server": {"host": "0.0.0.0", "port": 8765, "allow_lan": true, "api_token": "CHANGE_ME"},
  "home_assistant": {
    "url": "http://192.168.1.156:8123",
    "token": "",
    "secrets_file": "~/.config/opencode/secrets/homelab.env"
  },
  "llm": {"provider": "auto", "openai_compat": {"base_url": "http://127.0.0.1:11434/v1", "model": "qwen2.5:7b-instruct"}},
  "music": {"prefer": "home_assistant", "music_assistant": {"enabled": true}},
  "rooms": [
    {
      "id": "kitchen",
      "name": "Кухня",
      "aliases": ["на кухне", "кухне"],
      "satellite_id": "sat_kitchen",
      "media_player": "media_player.kitchen",
      "tts_player": "media_player.kitchen"
    },
    {
      "id": "bedroom",
      "name": "Спальня",
      "aliases": ["в спальне"],
      "satellite_id": "sat_bedroom",
      "media_player": "media_player.bedroom_ma",
      "tts_player": "media_player.bedroom_ma"
    }
  ]
}
```

### Поля комнаты
- `id` — стабильный идентификатор (используется в API/сессиях).
- `name`, `aliases` — распознавание комнаты в тексте («в кухне», «в спальне»).
- `satellite_id` — идентификатор спутника; запросы от него автоматически привязываются к комнате.
- `media_player` — HA `entity_id` плеера/колонки комнаты (основной для музыки).
- `tts_player` — куда выводить озвучку ответа (если отличается; можно = `media_player`).
- `microphone`/`speaker` — информативно/для интеграций.

### Токены/секреты
- `HASS_TOKEN` берётся из `home_assistant.token`, env `HASS_TOKEN`, или файла `home_assistant.secrets_file` (по умолчанию `~/.config/opencode/secrets/homelab.env`, формат `HASS_TOKEN=...`). **Не печатать и не коммитить.**
- Для LAN доступа к FreeVoice задайте `server.api_token` и передавайте `Authorization: Bearer <token>` или `X-Api-Token`.

## 4. Мультирум-музыка: как это работает

1. Пользователь говорит/пишет: «включи джаз в гостиной» (или выбирает комнату в UI / спутник передаёт `room`).
2. FreeVoice определяет комнату и находит `media_player` (из конфигурации комнаты, иначе пытается подобрать в HA по имени комнаты).
3. Навык HA вызывает сервисы воспроизведения (best-effort, с учётом совместимости):
   - если включён Music Assistant: пробуются `music_assistant.play_media` / `mass.play_media` с `media_id` и типом (track/playlist/radio);
   - стандартный HA: `media_player.play_media` с `media_content_id`/`media_content_type` (music/playlist/track/channel).
4. Управление: `media_play/pause/stop`, `media_next/previous_track`, `volume_up/down` на плеере комнаты.

### Поддерживаемые команды (примеры)
- «Включи музыку в этой комнате» / «Продолжи воспроизведение»
- «Включи джаз в гостиной» / «Поставь радио в кухне»
- «Пауза», «Стоп музыка», «Следующий трек», «Предыдущий трек»
- «Сделай громче/тише в спальне»

> Фактическая поддержка поиска по названию трека/радио/плейлиста зависит от настроенных провайдеров в Home Assistant/Music Assistant и возможностей `media_player`. Для максимально предсказуемой музыки рекомендуется Music Assistant + локальная библиотека/радио-URL/избранные плейлисты.

### Музыка и TTS одновременно (важно для спутников)
- Ответ ассистента возвращается в `speak`/`text`; `satellite_hints.tts_target_player` и `room.tts_player` подсказывают, куда озвучить.
- Стратегии: (а) озвучка на спутнике (локальный TTS) без прерывания колонки; (б) ducking — приглушить/пауза `media_player`, озвучить через `tts_player`/HA TTS, восстановить (реализуется на стороне оркестрации/HA-автоматизаций или спутника).
- В текущей серверной логике команды музыки и диалога обрабатываются отдельно; координация duck/resume — задача satellite/voice pipeline (см. план внедрения).

## 5. API спутников (HTTP)

`POST /api/satellite` (JSON), при настроенном `server.api_token` — с токеном.

- **Ping/hello:**
```json
{"type":"ping","satellite_id":"sat_kitchen"}
```
Ответ: версия, привязанная `room`, провайдеры tts/stt.

- **Utterance (распознанный текст):**
```json
{"type":"utterance","satellite_id":"sat_kitchen","text":"включи музыку в этой комнате","session_id":"sat_kitchen"}
```
Ответ: обычный ответ `/api/chat` + `satellite_hints`:
```json
{
  "text": "...", "speak": "...",
  "room": {"id":"kitchen","name":"Кухня","media_player":"media_player.kitchen","tts_player":"media_player.kitchen"},
  "satellite_hints": {"speak": true, "tts_target_player": "media_player.kitchen", "media_target_player": "media_player.kitchen"}
}
```

Спутник должен: (1) определить комнату по `satellite_id`, (2) озвучить `speak` локально или через `tts_target_player`, (3) при необходимости координировать с `media_target_player`.

## 6. Рекомендуемое ПО (локально, без подписок)

| Компонент | Рекомендация | Назначение |
|---|---|---|
| ОС сервера | Debian 12 / Ubuntu Server 24.04 LTS | Стабильная база, systemd |
| Умный дом | Home Assistant OS или Container | Устройства, автоматизации, медиа |
| Музыка | Music Assistant (в HA) | Локальная/потоковая музыка, мультирум, очереди |
| Диалог/LLM | Ollama (`qwen2.5:7b-instruct` / `llama3.1:8b`) или llama.cpp | Свободный чат локально |
| STT | faster-whisper / whisper.cpp | Распознавание речи (сервер/спутник) |
| TTS | Piper | Качественная локальная озвучка (ru/en) |
| Wake-word | openWakeWord | Локальное ключевое слово на спутнике |
| Голосовой pipeline (опц.) | HA Voice / Wyoming / Rhasspy | Связка mic↔wake↔STT↔assist↔TTS↔speaker |
| Спутники | ESP32-S3 (ESPHome voice) / Raspberry Pi / Android как тонкий клиент | Микрофон+динамик по комнатам |
| Аудио в комнатах | Snapcast/Mopidy или HA media_player (колонки/TV) | Синхронный/зональный звук |

## 7. Требования к серверу

| Вариант | CPU | RAM | Диск | Для чего |
|---|---|---|---|---|
| Минимум (HA + FreeVoice + лёгкий LLM/STT) | 4 ядра x86_64 | 16 GB | 256 GB SSD | 1–2 комнаты, небольшая модель |
| Рекомендуемый | 6–8 ядер (i5/Ryzen 5+) | 32 GB | 512 GB–1 TB NVMe | Несколько комнат, комфортный LLM 7B + STT + TTS |
| Комфортный | 8+ ядер / iGPU/NPU (опц.) | 64 GB | 1–2 TB NVMe | Быстрый диалог, несколько спутников, музыка/библиотека |

- Сеть: Gigabit LAN; сервер и HA по проводу предпочтительно. mDNS/доступ к HA/LLM из LAN.
- Текущая среда (~10 GB RAM, swap pressure) **не подходит** для комфортного продакшен-стека LLM+STT; использовать как разработческую/управляющую.

## 8. Пошаговый план внедрения

1. **Сервер/ОС:** Debian 12/Ubuntu Server 24.04, статика/DHCP-резерв IP, SSH, firewall в LAN.
2. **Home Assistant + Music Assistant:** поднять HA, добавить устройства и `media_player` по комнатам, установить/настроить MA, создать long-lived token.
3. **FreeVoice:** развернуть из репозитория/архива, создать `config/config.local.json` (HA URL/token, `rooms[]`, `server.api_token`, `llm`), запустить `python3 main.py --web --host 0.0.0.0 --port 8765` или systemd (`deploy/freevoice.service`), проверить `/api/health`, `/api/status?quick=0`, `/api/rooms`.
4. **Локальный LLM:** установить Ollama, скачать модель (`ollama pull qwen2.5:7b-instruct`), прописать `llm.openai_compat.base_url=http://127.0.0.1:11434/v1`, проверить диалог.
5. **Локальный STT/TTS:** Piper + faster-whisper/whisper.cpp (сервер) или на спутниках; для HA Voice — Wyoming интеграции.
6. **Спутники по комнатам:** ESPHome voice satellite / Raspberry Pi + wake-word + STT, привязать `satellite_id` к комнате, отправлять utterance в `/api/satellite`, озвучивать `speak`.
7. **Музыка:** проверить команды «включи музыку в этой комнате/в <комната>», пауза/громкость/следующий трек; настроить MA-провайдеры (локальная папка, радио) и маппинг `rooms[].media_player`.
8. **Проверка и hardening:** `python3 -m unittest discover -s tests -v`, ограничить доступ API токеном, не публиковать порты наружу, резервные копии конфигов.

## 9. Выбор колонок и подключение (простота и бюджет)

Практические рекомендации по бюджетным колонкам/плеерам, критериям выбора и схеме подключения (HA + Music Assistant + FreeVoice, `/music`): **[HARDWARE_SPEAKERS_BUDGET.md](HARDWARE_SPEAKERS_BUDGET.md)**.

## 10. Ограничения и честные ожидания

- Без локальной LLM свободный диалог ограничен правилами/поиском; для «как в чате» нужен запущенный LLM endpoint.
- Качество мультирума/музыки зависит от корректных `entity_id` в HA, интеграций плееров и (для поиска музыки) Music Assistant/провайдеров.
- «Всегда слушать» во всех комнатах — функция спутников (железо+ПО), а не только серверного кода; сервер обеспечивает маршрутизацию, навыки и HA/музыку.
- HA должен быть доступен по сети с сервера; при недоступности FreeVoice возвращает диагностическое сообщение.
