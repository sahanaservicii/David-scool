# Домовой — домашний sysadmin-агент

Личный офлайн-агент для домашней инфраструктуры: OpenWrt, Home Assistant, Android TV,
телефон, IP-камеры, бэкапы и документация. Работает **только с локальными сетями
своих локаций**, без облаков, подписок и платных сервисов. Все инструменты — Python
stdlib + системные `ssh`/`tar`, ничего не нужно покупать.

> **Локации (актуально с 2026-11-21):** инвентарь разделён на `active_location` и `locations.*` в `homelab.json`.
> Сейчас активна **квартира** (`192.168.0.0/24`, шлюз `192.168.0.1`). Данные **дачи** (`192.168.1.0/24`, OpenWrt/HA/камеры и др.) сохранены отдельно в `locations.dacha` и в `INVENTORY.md` — не смешивать с квартирным контекстом без подтверждения.

## Что создано

```
~/.config/opencode/agents/
  domovoy.md      главный агент (оркестратор)      primary
  network.md      OpenWrt, DHCP, DNS, firewall      subagent
  home.md         Home Assistant, автоматизации     subagent
  android.md      Android TV и телефон по ADB       subagent
  security.md     аудит сети, камеры, hardening     subagent
  backup.md       бэкапы и восстановление           subagent
  docs.md         инвентаризация, runbook, отчёты   subagent

~/.config/opencode/skills/
  homelab/            как пользоваться инструментами
  openwrt-admin/      рецепты OpenWrt
  home-assistant-local/  локальный REST API HA
  android-local/      ADB + мост телефона
  ip-cameras/         XM/NVR, ONVIF, RTSP, изоляция

homelab/
  homelab.py          CLI-инструмент (stdlib)
  homelab.json        инвентарь устройств (без секретов)
  state/              результаты сканов
  backups/            бэкапы
  README.md           этот файл
```

## Быстрый старт

```bash
cd homelab

python3 homelab.py doctor          # что доступно сейчас + активная локация/маршрут
python3 homelab.py scan            # скан активной сети (или --hosts <подсеть/список>)
python3 homelab.py inventory       # известные/неизвестные устройства
python3 homelab.py ha states       # Home Assistant (если относится к активной локации)
python3 homelab.py router status   # роутер (если настроен для активной локации)
python3 homelab.py tv devices      # Android TV
python3 homelab.py notify --message "Привет"
python3 homelab.py backup --with-router --with-ha
python3 homelab.py report
```

В чате достаточно сказать: «Домовой, проверь сеть», «выключи свет в зале»,
«перезагрузи приставку», «сделай бэкап роутера и HA».

## Секреты (один раз)

Создай файл `~/.config/opencode/secrets/homelab.env`, права `600`:

```bash
mkdir -p ~/.config/opencode/secrets
cat > ~/.config/opencode/secrets/homelab.env <<'EOF'
HASS_TOKEN=вставь_долгоживущий_токен_HA
HOMELAB_SSH_KEY=/root/.ssh/id_ed25519
EOF
chmod 600 ~/.config/opencode/secrets/homelab.env
```

- **HA-токен:** Home Assistant → профиль пользователя → «Долгоживущие токены»
  → создать. Хранится только на телефоне.
- **SSH-ключ роутера:** `ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519`,
  затем добавить публичный ключ в `/etc/dropbear/authorized_keys` на OpenWrt
  (LuCI → System → Administration → SSH keys, либо через уже открытый доступ).
- Пароли в файлах и в переписке не храним и не выводим.

## Android TV / телефон

- **Телефон (это устройство):** управление через локальный мост, без ADB:
  уведомления, будильники, буфер обмена, файлы, камера, открытие ссылок.
- **Android TV:** на приставке включить «Отладка по USB/сети» **только на время
  работ**. `homelab.py tv devices` покажет доступность. Если порт 5555 не
  открыт — включи отладку по сети в настройках разработчика.
- **Безопасность:** сетевой ADB = удалённый shell. После работ выключить:
  ```bash
  python3 homelab.py tv shell "setprop persist.adb.tcp.port -1; setprop service.adb.tcp.port -1; setprop ctl.restart adbd"
  ```
  (выполнять только на своей приставке; для этого нужен root/ADB-доступ).

## Офлайн и «без подписок»

| Слой | Чем работает | Нужен интернет? |
|---|---|---|
| Инструменты | Python stdlib, ssh, tar | нет |
| Роутер | SSH в LAN | нет |
| Home Assistant | локальный REST API | нет |
| Android | локальный ADB/мост | нет |
| Камеры | HTTP/RTSP/ONVIF в LAN | нет |
| LLM (мозг) | текущая модель OpenCode | зависит от модели |

Важно: **инструменты и автоматизация полностью локальные**, но сам языковой
модели нужен либо интернет (бесплатные модели OpenCode), либо локальная модель
на домашнем сервере (Ollama/llama.cpp). Агенты не привязаны к конкретной
модели — они наследуют модель сессии. Если поднимешь Ollama на ПК/NAS в этой
же сети, агенты продолжат работать без интернета: инструменты уже офлайновые.

## Безопасность

- Сканирование — только своей сети `192.168.1.0/24`. Чужие сети не трогаем.
- Разрушительные действия (reboot, firewall, sysupgrade, удаление автоматизаций)
  требуют явного подтверждения и бэкапа.
- Сетевой ADB и UPnP/DMZ/пробросы на WAN держим выключенными.
- Секреты — только в `secrets/homelab.env`, не в `homelab.json`, отчётах и чате.
- Камеры XM/NVR — в отдельный VLAN/гостевую сеть, без выхода в интернет.

## Восстановление

```bash
# бэкап роутера
python3 homelab.py backup --with-router
# на роутере: загрузить архив в /tmp и выполнить
sysupgrade -r /tmp/openwrt-YYYYmmdd-HHMMSS.tar.gz

# бэкап HA (конфиг + метаданные)
python3 homelab.py backup --with-ha
```

Полное восстановление HA — через снапшот самого HA (Settings → System →
Backups). Локальные бэкапы дополняют его, но не заменяют.

## Расписание

Периодические задачи (скан, бэкап) можно повесить на планировщик OpenChamber
или на cron домашнего сервера. Облачные cron-сервисы не нужны.
