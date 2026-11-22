# Ночной аудит Wi-Fi (только чтение)

Скрипт: `homelab/wifi_audit.py`. Запуск: `python3 homelab/wifi_audit.py`.

## Что делает
- Читает роутер 192.168.1.1 через `homelab.py router` (`uci wireless`, `iwinfo`,
  `iwinfo <iface> assoclist`, `logread`, `router status`). **Только чтение**.
- Проверяет SSID `RT-WIFI-47` (реальное имя из UCI; в запросе было `rt-wifi-47`).
  `sahanovschi` в `homelab.json` — хост `sahanovschi.v6.rocks`, а не SSID; по
  выбору пользователя как SSID не проверяется и в отчёте помечается отдельно.
- Считает клиентов, каналы, мощность, сигнал; ищет ошибки ассоциации, DHCP,
  подозрительные попытки SSH.
- Маскирует PSK/пароли (строки с `.key=`/`password`/`token` отбрасываются) и MAC
  (остаётся только OUI + `xx:xx:xx`). Сырые `wifi status` с полем `key` не используются.

## Артефакты
- Отчёт: `reports/wifi-audit-YYYY-MM-DD.md` (атомарная перезапись).
- Статус: `homelab/state/wifi_audit.json` (`ok`, `radios`, `findings`, `fixes_applied`, `fix_proposals`).

## Авто-фиксы и границы
Разрешены **только локальные** действия: создание каталогов, повтор неудавшейся
команды, восстановление повреждённого JSON, атомарная перезапись отчёта.
На роутере ничего не меняется: нет `uci set/commit`, `wifi reload`, `reboot`,
правок firewall и macfilter. Такие действия перечисляются в разделе
`fix_proposals` и требуют отдельного подтверждения пользователя днём.

## Расписание
OpenChamber: «Ночной аудит Wi-Fi (Вс 03:30 МСК, только чтение)»,
cron `30 3 * * 0`, `Europe/Moscow`, агент `domovoy`, уведомления ночью запрещены.
ID: `1f56c63e-1615-4399-b6e7-62566f5d4763`.

## Откат
Удалить расписание по ID выше и/или удалить `homelab/wifi_audit.py`. Состояние
роутера изменениями не затронуто.
