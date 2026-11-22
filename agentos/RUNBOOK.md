# RUNBOOK — agentos

## 1. Первый запуск после изменений

```bash
cd /root/workspace/agentos
./bin/agentos selftest        # 113 агентов, 50/50, ИТОГ: ВСЁ РАБОТАЕТ
#   (на Linux Windows-агенты показываются как skip — это норма)
./bin/agentos doctor
```

Если selftest падает — смотри `-v`: там traceback первых трёх сбоев.

## 2. Запрос не понят

```bash
./bin/agentos route "твоя фраза"      # покажет топ-8 агентов с оценками
./bin/agentos run <id> "аргументы"    # прямой запуск, без угадывания
```

Порог уверенности — `min_score` (по умолчанию 3.0). Понижать:
`./bin/agentos ask "..." --min-score 1.5`.

## 3. Агент отвечает «dry-run»

Это защита по умолчанию. Реальное выполнение:

```bash
./bin/agentos run hl.backup "router" --live
```

Перед изменениями роутера/HA — бэкап: `./bin/agentos run hl.backup "router ha" --live`.

## 4. Сброс памяти

```bash
mv data/memory.sqlite data/memory.sqlite.bak   # журнал, задачи, заметки
./bin/agentos doctor                            # создаст пустую базу
```

Конфиг: `data/config.json` (создаётся при первом запуске с дефолтами).
Удалить → вернутся дефолты.

## 5. Поднять локальную LLM (когда появится модель)

```bash
# llama.cpp
llama-server -m /models/qwen2.5-0.5b-instruct-q4.gguf --port 8080 --host 127.0.0.1

# или ollama
ollama serve            # слушает 11434, /v1 совместим
```

Проверка: `./bin/agentos run ai.status ""`. Система сама найдёт эндпоинт
(модель можно задать: `"llm": {"model": "qwen2.5:0.5b"}` в `data/config.json`).
Без модели всё остальное продолжает работать.

## 6. Зависший агент

Каждый вызов ограничен: shell — 15 с, `homelab.py` — 180 с (report/scan — 300 с,
notify — 60 с), HTTP — 4 с.
Если ждёте дольше — проверьте `agentos mem runs` (последний запуск) и
`agentos doctor`. Принудительно: `Ctrl+C`, состояние БД не портится (SQLite
с commit после каждой записи).

## 7. HTTP API

```bash
./bin/agentos serve --open              # браузер: http://127.0.0.1:8765/?token=…
./bin/agentos serve --host 0.0.0.0      # доступ из своей LAN (для телефона)
```

Страница `/` — интерфейс; `/health` без токена, `/agents` и `/ask` — по токену.
Токен печатается, сохраняется в `server.token` (`data/config.json`) и входит
в ссылку. Занят порт → `--port 8766`. Наружу не выставлять: `0.0.0.0` — только
локальная сеть. Тело запроса ≤ 64 КиБ; без `--live` — dry-run.

Проверка API:

```bash
curl -s localhost:8765/health
curl -s -H "Authorization: Bearer $TOKEN" localhost:8765/agents
```

## 7a. Windows-агенты (cmd, PowerShell)

```bash
./bin/agentos run win.help                       # список и текущая платформа
./bin/agentos run win.ps "Get-Service"           # dry-run: печатает команду
./bin/agentos run win.ps "Get-Service" --live    # выполнить (только Windows)
./bin/agentos run win.cmd "ipconfig" --live
```

Если что-то не так:

| Симптом | Причина / что делать |
|---|---|
| «работает только в Windows» | запущено на Linux/Android — это ожидаемо; выполнять на Windows |
| `командлет ... не разрешён` | только чтение: `Get-*`, `Test-*`, `Resolve-DnsName`; для журнала — `win.eventlog` |
| `запрещено ';'` или `'|'` | конвейеры и цепочки не поддерживаются — берите готовый агент (`win.process`, `win.services`) |
| `нужно подтверждение` | добавьте `подтверждаю` (или `confirm=да`); изменения только с `--live` |
| `нет powershell.exe` | Windows 10 без PowerShell 5.1 — восстановить компонент или использовать `win.cmd` |
| служба не стартует | нужны права администратора: запустить консоль от имени администратора |
| кракозябры | вывод декодируется UTF-8 → cp866 → cp1251; проверьте `chcp` |

Безопасность: `win.cmd` — фиксированный allowlist без аргументов; `win.ps` —
allowlist командлетов и запрет метасимволов; kill процесса и стоп службы
требуют подтверждения. Никаких `Invoke-Expression`, `Remove-*`, записи в файлы.

## 8. Перед изменением кода

```bash
python3 -m unittest discover -s tests -v
./bin/agentos selftest
```

Оба зелёные — можно менять. После правки агентов не забыть
`./bin/agentos catalog` (обновит `CATALOG.md`).

## 9. Интеграция с homelab

Агенты `net.*`, `hl.*`, `sec.*` вызывают `../homelab/homelab.py`, поэтому
сначала должен работать он:

```bash
cd ../homelab && python3 homelab.py doctor
```

Если homelab.py недоступен — 32 агента (`net.*`, `hl.*`, `sec.*`) вернут
понятную ошибку, остальные 68 продолжат работать (изоляция сбоев на уровне
агента).

## 10. Переносимый комплект и телефон

```bash
python3 tools/build_portable.py            # dist/agentos-portable/ + zip
cd dist/agentos-portable && ./run.sh selftest
```

Комплект самодостаточен: python3 + папка. Данные — `data/` рядом (иначе
`~/.local/share/agentos`), переопределяются `AGENTOS_DATA`/`AGENTOS_OUT`,
корень — `AGENTOS_HOME`. На Termux: `pkg install python`, распаковать zip,
`./run.sh selftest`. Windows 10: распаковать и запустить `start.cmd`
(браузер) или `run.cmd selftest`; Python 3.12 уже в комплекте, ставить нечего.
`start-lan.cmd` открывает доступ из LAN. Сервер на телефоне — `127.0.0.1:8765`,
браузер того же телефона. `homelab.py` в комплекте уже переносимый: отчёты пишутся в
`reports/` рядом с папкой.
