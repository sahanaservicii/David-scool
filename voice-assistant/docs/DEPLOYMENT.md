# Развёртывание FreeVoice (v0.3.0)

## 1. Требования

- Python **3.10+** (ядро на stdlib)
- Linux сервер в локальной сети (рекомендуется Debian 12 / Ubuntu Server 24.04 LTS)
- Доступ к Home Assistant (опционально, для умного дома/музыки) и локальному LLM endpoint (опционально, для свободного диалога)

Для мультирум-голоса в продакшене дополнительно: Home Assistant (+ Music Assistant), локальный LLM (Ollama/llama.cpp), STT (faster-whisper/whisper.cpp), TTS (Piper), спутники по комнатам (ESPHome/Wyoming/RPi). Подробно: [MULTIROOM_HA.md](MULTIROOM_HA.md).

## 2. Установка

```bash
# копия проекта на сервер
mkdir -p /opt/freevoice
cp -a /path/to/voice-assistant/. /opt/freevoice/
cd /opt/freevoice

python3 -m py_compile $(find assistant -name '*.py') main.py tests/test_core.py tests/test_multiroom.py
python3 -m unittest discover -s tests -v
```

## 3. Конфигурация

Создайте локальный конфиг (не коммитить секреты):

```bash
cp config/config.local.example.json config/config.local.json
# отредактируйте config/config.local.json
```

### Важные параметры

- `server.host` / `server.port` / `server.allow_lan`: для доступа из LAN используйте `0.0.0.0`, порт (напр. `8765`), `allow_lan: true`.
- `server.api_token`: длинный случайный токен для защиты API в LAN (POST `/api/chat`, `/api/satellite` требуют `Authorization: Bearer <token>` или `X-Api-Token`).
- `home_assistant.url`: `http://<HA_IP>:8123`
- `home_assistant.token`: **не хранить в git**; предпочтительно env `HASS_TOKEN` или `home_assistant.secrets_file` (по умолчанию `~/.config/opencode/secrets/homelab.env`, строка `HASS_TOKEN=...`).
- `llm.provider`: `auto` или `openai_compat`
- `llm.openai_compat.base_url` / `model`: локальный OpenAI-compatible сервер (напр. Ollama `http://127.0.0.1:11434/v1`, модель `qwen2.5:7b-instruct`).
- `rooms[]`: для каждой комнаты задайте `id`, `name`, `aliases`, `satellite_id`, `media_player` (HA entity_id), `tts_player`.
- `music.music_assistant.enabled`: `true`, если используете Music Assistant и хотите пробовать MA-сервисы воспроизведения.

### Переменные окружения (переопределяют конфиг)

`ASSISTANT_HOST`, `ASSISTANT_PORT`, `ASSISTANT_LANG`, `ASSISTANT_LOG_LEVEL`, `HASS_URL`/`HOME_ASSISTANT_URL`, `HASS_TOKEN`/`HOME_ASSISTANT_TOKEN`, `HOMELAB_SECRETS_FILE`, `LLM_PROVIDER`, `LLM_BASE_URL`/`OPENAI_BASE_URL`, `LLM_MODEL`/`OPENAI_MODEL`, `LLM_API_KEY`/`OPENAI_API_KEY`.

## 4. Запуск

### Ручной запуск

```bash
cd /opt/freevoice
python3 main.py --web --host 0.0.0.0 --port 8765
# UI: http://<SERVER_IP>:8765
```

CLI: `python3 main.py`

### systemd

```bash
sudo cp deploy/freevoice.service /etc/systemd/system/freevoice.service
# при необходимости отредактируйте User/WorkingDirectory/ExecStart/Environment
sudo systemctl daemon-reload
sudo systemctl enable --now freevoice
sudo systemctl status freevoice
sudo journalctl -u freevoice -f
```

Рекомендуется хранить `HASS_TOKEN`/`LLM_API_KEY` в `EnvironmentFile` с правами `600`, а не в unit-файле.

## 5. Проверка после запуска

```bash
curl -sS http://127.0.0.1:8765/api/health
curl -sS http://127.0.0.1:8765/api/status?quick=0
curl -sS http://127.0.0.1:8765/api/rooms
```

Проверка чата (с токеном при необходимости):
```bash
curl -sS -X POST http://127.0.0.1:8765/api/chat \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>' \
  -d '{"text":"включи музыку в этой комнате","session_id":"test","room":"kitchen"}'
```

Проверка спутника:
```bash
curl -sS -X POST http://127.0.0.1:8765/api/satellite \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>' \
  -d '{"type":"ping","satellite_id":"sat_kitchen"}'
```

Ожидаемое поведение:
- без HA/LLM: сервис стартует, `/api/health` OK, навыки/комнаты доступны, HA/LLM запросы дают диагностические ответы;
- с HA: `home_assistant.reachable=true` в status (при `quick=0`), команды управления/музыки выполняются на корректных `entity_id`;
- с LLM: свободный диалог отвечает через настроенный endpoint.

## 6. Мультирум-музыка (операционные заметки)

- Убедитесь, что `rooms[].media_player` указывает на реальный `media_player` в HA (обычный плеер или Music Assistant player).
- Команды: «включи музыку в <комната>», «пауза», «громче/тише», «следующий трек». «Включи <запрос>» пробует MA/HA `play_media` (результат зависит от провайдеров/поддержки плеера).
- Для спутников передавайте `satellite_id` и/или `room`; используйте `satellite_hints` в ответе для выбора TTS-вывода.
- Координация ducking (приглушить музыку на время TTS) реализуется на стороне спутника/HA-автоматизаций.

## 7. Безопасность

- Не публикуйте порт FreeVoice/HA в интернет без VPN (WireGuard) и строгой аутентификации.
- Включите `server.api_token` в LAN; не логируйте секреты; `config.local.json` и секреты не коммитить.
- `security.log_conversations` по умолчанию `false`.
- Ограничения API: тело запроса ≤ 64 KB, `text` ≤ 4000 символов, `session_id` ≤ 64.
- Не используйте разрушительные действия без явного подтверждения (навыки/интеграции должны запрашивать подтверждение).

## 8. Известные ограничения

- Свободный диалог высокого качества требует локальную LLM (без неё — правила/поиск/подсказки).
- Реальное управление/музыка требуют доступный Home Assistant, валидный токен и корректные `rooms[].media_player`.
- Воспроизведение по произвольному названию зависит от Music Assistant/провайдеров и возможностей плеера.
- Сервер не включает встроенный always-listening wake-word/STT/TTS pipeline; для этого нужны спутники/voice-стек (см. [MULTIROOM_HA.md](MULTIROOM_HA.md)).
- Онлайн-поиск (DDG/SearXNG) зависит от наличия сети; при оффлайне работает локальная функциональность.

## 9. Бэкап и перенос

- Код/конфиги: резервная копия каталога проекта (исключая секреты/данные по политике), `config/config.local.json` хранить отдельно и безопасно.
- Данные: `data/assistant.db` (заметки/таймеры/история при включении).
- Для переноса: распаковать/скопировать проект, восстановить `config.local.json` и секреты, установить/запустить зависимости стека (HA/LLM/STT/TTS) на целевом сервере, прогнать тесты и проверки API.
