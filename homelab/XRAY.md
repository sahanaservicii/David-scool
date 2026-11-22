# Xray на роутере (прозрачный прокси для LAN)

Роутер: OpenWrt 25.12.5, `sahanovschi.v6.rocks` / `192.168.1.1`, Xray 26.11.9
(`/etc/xray/xray`). Схема переведена на procd 18.11.2026.

## Как устроено

```
LAN 192.168.1.0/24 --(nft redirect tcp 80,443)--> xray :12345 (dokodemo-door)
                                                   |
                                                   +-- правило домена/IP --> outbound n01 (VLESS+Reality)
                                                   +-- всё остальное ------> direct
localhost:10808 socks — для проверок из shell
```

| Что | Где |
|---|---|
| конфиг (статичный, не генерируется) | `/etc/xray/config.json` |
| сервис xray (procd, respawn) | `/etc/init.d/xray` |
| сторожевой цикл (procd) | `/etc/init.d/xray-hc` → `/etc/xray/health.sh` |
| журнал проверок | `/tmp/xray-hc.log` |
| бэкапы | `/etc/xray/config.json.bak-20261118`, `/etc/rc.local.xray-legacy-20261118`, `/etc/crontabs/root.bak-20261118` |

## Логика health-check

Раз в 60 с `curl` через `127.0.0.1:10808` на `https://www.facebook.com/`:

- ответ 200/204/301/302/303/307/308 → таблица `inet xrayredir` есть (трафик LAN
  идёт через прокси);
- 3 неудачи подряд → таблица удаляется, LAN ходит напрямую (интернет не
  ломается);
- первый успех → переадресация возвращается.

Сам процесс xray при этом **не перезапускается** (раньше `rc.local` по крону
раз в минуту перегенерировал конфиг и дёргал процесс — источник миганий).

## Диагностика

```sh
/etc/init.d/xray status; /etc/init.d/xray-hc status
tail -5 /tmp/xray-hc.log
nft list table inet xrayredir            # пусто = режим "напрямую"
curl -sS -m 10 --socks5-hostname 127.0.0.1:10808 -o /dev/null -w '%{http_code}\n' https://www.facebook.com/
logread -e xray | tail
```

Тег в логе xray (`[redir -> n01]` / `[redir -> direct]`) показывает, каким
апстримом реально пошёл поток.

## Правила маршрутизации (сейчас)

1. `domain:facebook.com, fbcdn.net, facebook.net, fb.com, messenger.com,
   msngr.com, fbsbx.com` → `n01`
2. `ip: geoip:facebook` → `n01` (для соединений по IP без SNI)
3. `domain:youtube.com, googlevideo.com, ...` → `n01`
4. `geoip:private` → `direct`
5. `tcp,udp` → `direct`

Важно: поля в одном правиле Xray объединяет по **AND** — `domain` и `ip` в одной
записи никогда не сработают вместе, их нужно держать отдельными правилами.

## Что проксируется

Только **TCP 80/443**. QUIC/UDP 443 в туннель не попадает: приложения сами
откатываются на TCP (это добавляет задержку на старте, но работает). Если нужны
UDP-сценарии (звонки Messenger) — нужен TPROXY-инбаунд с `network: udp`.

## Известные ограничения

- Единственный апстрим `user.betust.net:443` (VLESS+Reality) с 18.11.2026 не
  принимает TCP — прокси фактически выключен, health-check держит режим
  «напрямую». Нужен рабочий конфиг сервера.
- `test.json` — набор из 42 чужих конфигов (разные UUID), для работы не
  использовался: ни один узел из него Facebook не открывает.
