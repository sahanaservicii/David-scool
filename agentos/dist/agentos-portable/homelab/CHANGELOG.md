# Журнал изменений

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
