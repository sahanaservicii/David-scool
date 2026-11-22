# Журнал изменений

## 2026-11-21 — Коррекция локаций (квартира/дача), инвентарь и навыки

**Контекст:** по уточнению пользователя активная сеть — квартира `192.168.0.0/24` (шлюз `192.168.0.1`, подтверждённые/местные: `192.168.0.1`, `192.168.0.12`, `192.168.0.17`); устройства из `192.168.1.0/24` (>60% прежнего инвентаря) отнесены к даче/не этой локации, если не подтверждены отдельно.

**Причина неверной информации (анализ):**
- `homelab.json`/`INVENTORY.md` исторически формировались вокруг дачной сети `192.168.1.0/24` (OpenWrt/HA/камеры/IoT) и могли пополняться при доступе к ней (в т.ч. через WireGuard/туннель к даче), из-за чего дачные устройства воспринимались как «текущие».
- В данных и правилах не было явного поля/режима локации, а часть инструкций/навыков жёстко предполагала `192.168.1.0/24` — это приводило к смешиванию контекстов (квартира vs дача) без проверки фактической сети.

**Что исправлено:**
- `homelab.json`: активная локация **apartment** (`network` 192.168.0.0/24, `gateway` 192.168.0.1), добавлены `active_location`, `location_note`, `locations.apartment`/`locations.dacha`, `meta`. Квартирный инвентарь очищен и приведён к подтверждённым фактам; прежние дачные конфиги/устройства сохранены отдельно в `locations.dacha` (в т.ч. OpenWrt, HA, камеры, IoT). `192.168.1.27`, обнаруженный сканом 2026-11-21 (Boa `/admin/login.asp`), добавлен как `unconfirmed`.
- `INVENTORY.md`: переписан с разделением «Квартира (активная) / Наблюдалось, локация не подтверждена / Дача (архив)» и описанием причины.
- Документация: `README.md`, `RUNBOOK.md` — добавлены правила определения локации/сети перед работой и запрет смешивания локаций.
- Инструкции/навыки (предотвращение повтора): `~/.config/opencode/skills/homelab/SKILL.md` — убрано жёсткое «только 192.168.1.0/24», добавлена обязательная проверка `active_location/network/gateway` и подтверждение диапазона; `/root/workspace/AGENTS.md` и `~/.config/opencode/agents/domovoy.md` — обобщены ограничения/шаги на «подтверждённые свои сети/локации» с проверкой контекста.

**Проверка:**
- `python3 -m json.tool homelab/homelab.json` — OK.
- `python3 -m py_compile homelab/homelab.py` — OK.
- `homelab.py doctor`/`inventory` — работают с новым контекстом (192.168.0.0/24); SSH роутера/Android TV недоступны в квартирном профиле, что соответствует фактам.

**Бэкап перед правками:**
- `homelab/backups/pre-location-fix-20261121/` (`homelab.json`, `INVENTORY.md`, `README.md`, `RUNBOOK.md`, `CHANGELOG.md`).

**Откат:**
- Восстановить файлы из `homelab/backups/pre-location-fix-20261121/` (и при необходимости вернуть прежние версии навыка/инструкций из истории/бэкапа системы).

**Риски/примечания:**
- Команды `router`/`ha`/`adb(tv)` в активном квартирном профиле могут быть неприменимы, т.к. целевые устройства относятся к даче; использовать данные `locations.dacha` только при подтверждённом доступе к дачной локации. Принадлежность `192.168.1.1` (Innbox G84) и `192.168.1.27` требует отдельного уточнения.


## 2026-11-19 — навык и помощник уточнения задач (`clarify`)

Добавлено:

- Навык `~/.config/opencode/skills/clarify/SKILL.md`: протокол ровно 3 вопросов
  к каждому запросу (результат, границы, контекст/приоритет), с вариантами
  ответов и строкой «зачем спрашиваем».
- Подагент-помощник `~/.config/opencode/agents/clarify.md` (без прав на
  изменения, shell и вызов других агентов).
- В `domovoy.md`: обязательный шаг уточнения, навык `clarify` в списке
  профильных, подагент `clarify` в списке делегирования и в permissions.
- В `/root/workspace/AGENTS.md`: правило уточнения для любого агента.

Откат:

- Вернуть `domovoy.md` и `AGENTS.md` из
  `homelab/backups/opencode-clarify-20261119-051751/`, удалить каталог навыка
  `clarify` и файл `agents/clarify.md`.

## 2026-11-15 — создан агент «Домовой»

Добавлено:

- Главный агент `domovoy` и подагенты: `network`, `home`, `android`,
  `security`, `backup`, `docs`.
- Навыки: `homelab`, `openwrt-admin`, `home-assistant-local`, `android-local`,
  `ip-cameras`.
- Офлайн-инструмент `/root/workspace/homelab/homelab.py` (stdlib): doctor,
  scan, inventory, HA REST, OpenWrt SSH, Android ADB, камеры, бэкапы, отчёты.
- Инвентарь `homelab.json`, `INVENTORY.md`, этот журнал, `RUNBOOK.md`.
- `default_agent: domovoy` в `~/.config/opencode/opencode.json`.

Откат:

- Убрать `default_agent` из `opencode.json` (или вернуть `build`).
- Удалить `~/.config/opencode/agents/*.md` и новые навыки, если не нужны.
- Инструменты и данные — в `/root/workspace/homelab/`, удаляются отдельно.

## 2026-11-15 — сетевой аудит (по отчёту)

- Закрыт ADB `:5555` на Android TV `192.168.1.139` (`persist.adb.tcp.port=-1`,
  `service.adb.tcp.port=-1`, перезапуск `adbd`). Откат: включить отладку по сети
  в настройках разработчика.
- Удалён мёртвый DNAT `8123 → .156` и дубль правила WireGuard, firewall
  перезагружен. Откат: вернуть правила из `firewall-backup.json` осознанно.
- Камеры XM/NVR: HTTP без TLS, требуется смена паролей/изоляция. Не менялось.

## 2026-11-15 — HA отложен, подготовлен доступ по SSH

- `home_assistant.enabled=false` в `homelab.json`; `doctor` пропускает HA
  (`[--] отложено`), остальные проверки работают.
- `doctor` показывает локальный IP маршрута к `192.168.1.1` — помогает понять,
  активен ли Wi-Fi/WireGuard.
- Сгенерирован ключ `~/.ssh/id_ed25519` (`domovoy@phone`). Публичную часть
  нужно добавить в `/etc/dropbear/authorized_keys` на OpenWrt.
- Включение HA позже: `"enabled": true` и `HASS_TOKEN` в secrets.

## 2026-11-17 — DNAT Home Assistant на WAN:18443 для телефона

По явному подтверждению пользователя на OpenWrt добавлен проброс WAN TCP
`18443 → 192.168.1.156:8123` (Home Assistant). Имена: redirect `HA-phone-only`,
rule `HA-phone-only-allow`; добавлен forwarding `wan → lan`. Доступ ограничен
источником `91.79.32.179/32` — публичный IP, с которого приходят подключения
и который виден как endpoint WireGuard-пира.

Добавлено:

- DNAT и rule в `/etc/config/firewall`, forwarding `wan → lan`.
- `fw4 check` прошёл, firewall перезагружен; SSH и роутер остались доступны.
- В `homelab.json` `home_assistant.enabled` уже `true` (запись от 15.11 об
  «отложенном» HA тем самым устарела).

Проверка:

- TCP `sahanovschi.v6.rocks:18443` открыт.
- `GET /` → 200 с заголовком Home Assistant; `GET /api/` → 401.
- `conntrack`: `src=91.79.32.179 dst=172.25.213.7 dport=18443 → 192.168.1.156:8123`.

Бэкапы перед правкой:

- `/root/workspace/homelab/backups/openwrt-20261117-052939.tar.gz`
- `/root/workspace/homelab/backups/homelab-20261117-052939.tar.gz`
- на роутере: `/root/firewall.bak.ha-1794893394`

Откат:

- Удалить redirect `HA-phone-only`, rule `HA-phone-only-allow` и forwarding
  `wan → lan`, затем `fw4 check && /etc/init.d/firewall reload`.
- Или вернуть `/etc/config/firewall` из `/root/firewall.bak.ha-1794893394`
  (либо из бэкапа выше) и перезагрузить firewall. SSH/WireGuard при этом
  остаются доступны.

Риски (отдельно):

- Трафик идёт по HTTP без TLS.
- Whitelist привязан к `91.79.32.179/32`: при смене публичного IP телефона
  доступ пропадёт, правило нужно обновить.
- WireGuard остаётся предпочтительным каналом; DNAT — запасной путь только
  для этого IP.

## 2026-11-17 — Пространство Home Assistant: 2 дома и комнаты

Через WebSocket API HA (минимальный клиент на stdlib, `/tmp/opencode/ha_ws.py`)
создано 2 Floor и 13 Area. Device/entity-реестры не менялись: 27 устройств с
`area_id` остались на месте и автоматически оказались в доме
`raxmaninova-49`; 194 из 221 устройства без зоны намеренно не трогались.

Добавлено:

- Floors: `raxmaninova-49` (`raxmaninova_49`), `izmailovo-47`
  (`izmailovo_47`).
- 7 прежних Area перенесены в `raxmaninova-49`: Гостиная (49) `[gostinaia]`,
  Кухня (49) `[kukhnia]`, Обородования `[oborodovaniia]`, Спальня (49)
  `[spalnia]`, Электра шиток `[elektra_shitok]`, Улица (49) `[ulitsa]`,
  Квартира `[kvartira]`. Четыре имени получили суффикс `(49)`: HA требует
  уникальности имён Area.
- 6 новых Area для `izmailovo-47`: Ванная `[vannaia]`, Коридор `[koridor]`,
  Гостиная `[gostinaia_2]`, Кухня `[kukhnia_2]`, Спальня `[spalnia_2]`,
  Улица `[ulitsa_2]`.

Проверка (2026-11-17, повторный `.../list`): 2 Floor и 13 Area с нужными
`floor_id`, имена совпадают с описанными выше.

Бэкап реестров до изменений:
`/root/workspace/homelab/backups/ha-registries-20261117.jsonl` (4 строки:
floors 0, areas 7, devices 221, entities 833).

Откат:

- вернуть 7 Area прежние имена (без `(49)`) и `floor_id: null` через
  `config/area_registry/update`; удалить 6 новых Area и оба Floor командами
  `config/area_registry/delete` / `config/floor_registry/delete` (сначала Area,
  затем Floors) — всё через тот же WS-клиент;
- device/entity-реестры откатывать не нужно, они не менялись; полный снимок —
  в бэкапе выше. Подробности и команды — в `RUNBOOK.md`, раздел 9.

## 2026-11-18 — Xray: Facebook/Messenger в туннель + нормальный сервис

Контекст: роутер уже держал прозрачный прокси Xray, но в `rc.local` конфиг
перегенерировался кроном каждую минуту, а апстрим `user.betust.net` перестал
отвечать. Facebook/Messenger шли мимо туннеля (`-> direct`) и висели.

Сделано:

- `/etc/xray/config.json` — добавлены правила: домены Meta
  (`facebook.com, fbcdn.net, facebook.net, fb.com, messenger.com, msngr.com,
  fbsbx.com`) и отдельным правилом `geoip:facebook` → outbound `n01`
  (в одном правиле `domain`+`ip` не работают: Xray объединяет поля по AND).
- Схема переведена на procd: `/etc/init.d/xray` (единственный процесс,
  respawn) и `/etc/init.d/xray-hc` + `/etc/xray/health.sh` (проверка раз в
  60 с, 3 неудачи → режим «напрямую», успех → переадресация обратно).
- Убран крон `* * * * * /bin/sh /etc/rc.local`; `rc.local` заменён заглушкой.
- Исправлен рестарт: в сборке нет `pkill` (только `kill`), из-за чего новые
  конфиги раньше не применялись.

Проверка:

- `xray run -test` → Configuration OK; тег в логе для facebook
  `[redir -> n01]` (было `-> direct`).
- Health-check: 3×`probe=FAIL` → `rules=OFF`, прямой интернет `ya.ru:302`.
- Facebook/Messenger **не открываются**: `user.betust.net` (50.7.169.243)
  не принимает TCP/443 при живом ping; из 42 узлов `test.json` не работает
  ни один. Нужен рабочий конфиг сервера.

Откат:

- `cp /etc/rc.local.xray-legacy-20261118 /etc/rc.local`,
  `cp /etc/crontabs/root.bak-20261118 /etc/crontabs/root`,
  `cp /etc/xray/config.json.bak-20261118 /etc/xray/config.json`,
  `/etc/init.d/xray disable; /etc/init.d/xray-hc disable`, `/etc/init.d/cron restart`.
- Подробности схемы — `XRAY.md`.

## 2026-11-19 — ежедневный бэкап (роутер + HA + конфиг)

- Добавлен `homelab/daily_backup.py`: локальный конфиг + роутер (SSH) + конфиг HA
  (с авто-подъёмом SSH-туннеля при отсутствии прямого доступа). Отчёт — `state/daily_backup.json`.
- Пробный запуск: архивы `homelab-20261119-055222.tar.gz`, `openwrt-...`, `ha-config-...` (HA 2026.11.2), без ошибок.
- Планировщик: системный `cron` в контейнере не стартует → использован OpenChamber schedule,
  `0 3 * * *` Europe/Moscow, id `ac0b81fb-f327-4d63-8f70-92f8d7db541a`.
- Облако `terrabox.com` (74.80.184.159) недоступно ни с хоста, ни с роутера (timeout) —
  загрузка в облако не настроена. Требуется адрес/доступ или локальный NAS в LAN.
