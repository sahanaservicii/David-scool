# Аудит домашней Wi-Fi/локальной сети и план устранения рисков

- **Дата отчёта:** 16.11.2026
- **Сеть:** `192.168.1.0/24`, шлюз `192.168.1.1`
- **Область:** домашняя сеть пользователя. Чужие сети, интернет-сервисы и подбор паролей не используются.
- **Статус данных:** все сетевые факты в этом отчёте — **по состоянию на 15.11.2026** (собраны с роутера и из артефактов того дня) и **требуют перепроверки** при восстановлении доступа. Свежий скан в этой сессии **не выполнялся** (см. раздел A).

> Обозначения достоверности:
> **[ФАКТ]** — подтверждено ранее собранными данными (файлы-источники в разделе H).
> **[ПРОВЕРИТЬ]** — предположение/не подтверждено, требует отдельной проверки.
> **[НЕИЗВЕСТНО]** — данных нет.

---

## A. Почему полный Wi-Fi-скан сейчас невозможен

Сканирование в этой сессии не выполнялось и не могло быть выполнено. Ниже — проверенные причины (16.11.2026), по пунктам.

1. **Нет Wi-Fi-адаптера и утилит для беспроводного сканирования.** Локальная проверка подтвердила отсутствие `iw`, `iwinfo`, `airodump-ng`, `nmcli`, `nmap`, `arp`.
   - `/sys/class/net` недоступен (`Permission denied`), `ip` не установлен — перечислить интерфейсы и беспроводные устройства из этой среды нельзя.
   - У хоста, по ранее проверенным данным, доступен только интерфейс `lo`. Wi-Fi-интерфейса для пассивного/активного скана эфира нет.
   - **[ФАКТ]** Проверено 16.11.2026: `ls /sys/class/net` → `Permission denied`; `iw`/`iwinfo`/`airodump-ng`/`nmcli` → missing.

2. **Роутер `192.168.1.1` недостижим.**
   - SSH `:22` — timeout, DNS `:53` — timeout (проверено ранее).
   - **[ФАКТ]** Локальный адрес, которым хост «дошёл бы» до `192.168.1.1`, — `10.20.30.178`. Это **другая сеть**, а не домашний `192.168.1.0/24`. Маршрута в домашнюю сеть нет.
   - То есть даже если бы утилиты были, из этой среды виден не домашний LAN, а чужой/транзитный сегмент.

3. **TCP-скан в этой среде даёт ложные результаты — использовать его нельзя.**
   - Промежуточный прокси принимает TCP-соединения на `80`/`8080` для **любого** IP. Проверено ранее на заведомо несуществующих адресах (`203.0.113.7`, `192.168.1.99`).
   - Поэтому результат вида «154 хоста» — **артефакт прокси**, а не карта сети. Он здесь не приводится и не трактуется.
   - Соответственно, `homelab.py scan` в этой сессии **не запускался** и его вывод как факт не используется.

**Вывод:** достоверные данные о домашней сети можно получить только **изнутри** неё. Пока хост находится в `10.20.30.0/24` без доступа к роутеру, новый скан невозможен. Всё, что есть в разделах C–D, опирается на артефакты от 15.11.2026 и помечено как требующее перепроверки.

### Что нужно от пользователя, чтобы скан стал возможен

Любой из вариантов:

- **Вариант 1 (предпочтительный) — вернуть SSH к роутеру.** Подключить устройство-инициатор к домашней сети `192.168.1.0/24` (Wi-Fi `RT-WIFI-47` или Ethernet) и обеспечить доступ по SSH к `192.168.1.1` (ключ `HOMELAB_SSH_KEY`). Тогда скан и проверки выполняются прямо на роутере — это самый точный источник (см. раздел B).
- **Вариант 2 — выполнить скан с ПК/телефона в домашней сети.** Подключить ПК с Linux к `RT-WIFI-47` и выполнить команды из раздела B (с ПК), затем передать вывод.
- **Вариант 3 — телефон в домашней сети + Android-приложение** для инвентаризации Wi-Fi (например, встроенный анализатор или приложение-сканер из локального источника). Результат — список SSID/BSSID/каналов/шифрования для **своей** сети.

Во всех вариантах: сканируется **только своя** сеть; чужие сети и подбор паролей исключены.

---

## B. Как получить настоящий Wi-Fi-скан

### B.1. На OpenWrt через SSH (источник истины)

Выполнять на роутере `192.168.1.1` (или через `homelab.py router exec "..."`).

```bash
# Список радио и интерфейсов
iwinfo                       # краткая сводка по всем радио
iw dev                       # интерфейсы и их режимы
uci show wireless            # вся конфигурация Wi-Fi (SSID, encryption, каналы)

# Активный скан эфира по каждому радио (только своя сеть — для оценки каналов/шума)
iwinfo radio0 scan
iwinfo radio1 scan
iwinfo radio2 scan

# Эквивалент через ubus (машинно-читаемо)
ubus call iwinfo scan '{"device":"radio0"}'
ubus call iwinfo scan '{"device":"radio1"}'
ubus call iwinfo scan '{"device":"radio2"}'

# Кто сейчас подключён к точке (ассоциации)
iwinfo <iface> assoclist          # напр. iwinfo phy0-ap0 assoclist
```

Примечание: активный `scan` на интерфейсе, который обслуживает клиентов, может на секунду «уронить» связь на этом радио. На роутере с 3 радио это допустимо, но лучше делать по одному радио.

### B.2. С ПК Linux (если роутер недоступен, но ПК в домашней сети)

```bash
# NetworkManager
nmcli device wifi list

# «Голый» wireless-tools/iw
iw dev                       # найти имя интерфейса, напр. wlan0
iw dev wlan0 scan            # активный скан
iw dev wlan0 link            # к чему подключён сам ПК
```

### B.3. Android-приложение (если есть только телефон)

Любое локальное приложение-анализатор Wi-Fi (без облака), установленное из доверенного источника. Смотреть для **своей** сети: SSID, BSSID, канал, ширина, тип шифрования (WPA2/WPA3), уровень сигнала. Приложение не должно требовать загрузки баз из интернета.

> Во всех случаях ищем в первую очередь ответы на вопросы: **какое шифрование реально в эфире** (WPA2/WPA3/SAE-mixed), **включён ли WPS**, **есть ли PMF/802.11w**, **какие каналы и ширина**, **нет ли посторонних/лишних SSID**.

---

## C. Уязвимости

Все строки — **по состоянию на 15.11.2026, требуют перепроверки**. Источники — раздел H.

| # | Риск | Где | Критичность | Доказательство / источник | Статус |
|---|------|-----|-------------|---------------------------|--------|
| C1 | ADB по TCP **без авторизации** → root-консоль любому в LAN | `192.168.1.139:5555` (Google ADT-3, Android TV 14) | 🔴 Критично | `adb connect` вернул `uid=0(root)`, без подтверждения на экране; `CNXN` без запроса авторизации | ✅ **Исправлено** — `service.adb.tcp.port=-1`, `persist.adb.tcp.port=-1`, перезапуск `adbd`; порт `5555` закрыт (по данным 15.11) |
| C2 | 5 устройств видеонаблюдения: **веб-интерфейс по HTTP без TLS** | `.10`, `.93`, `.135`, `.190`, `.206` (XM/XMEye, JF, NVR Topsvision) | 🟠 Высоко | HTTP-баннеры: `Web Viewer`, `Server: APPWebs/`, редирект `doc/page/login.html` | ⏳ **Открыто** — нужен логин/пароль админа |
| C3 | **Порт `34567`** (проприетарный XM-протокол) открыт на камерах/NVR — поверхность атаки, Mirai-риск | `.10`, `.93`, `.135`, `.190`, `.206` | 🟠 Высоко | TCP `34567` открыт; семейство Xiongmai массово используется ботнетами из-за старых прошивок/дефолтных учёток | ⏳ **Открыто** |
| C4 | RTSP `:554` без TLS, но **требует авторизацию** (не «голый») | камеры/NVR | 🟡 Средне | `DESCRIBE` → `401 Unauthorized`; баннеры `H264DVR 1.0` / `Topsvision Server v2.1` | ✅ **Проверено** — доступ без пароля закрыт; TLS у RTSP нет |
| C5 | Wavlink WN570HA1B: **дефолтный тестовый сертификат**, истёк **16.10.2021**; веб-вход по HTTP; пароль хешируется **MD5 на клиенте** | `192.168.1.223` | 🟠 Высоко (по баннеру) / низко по конфигу | `CN=Test Server Cert`, `O=OpenSSL Group`, «FOR TESTING PURPOSES ONLY»; `jquery.md5.js` | ⚠️ **Частично** — remote mgmt/UPnP/DMZ **выкл**, пробросов **0**, DHCP не раздаёт, облако **выкл**; сертификат прошивочный, из UI не меняется → **реальный риск низкий** |
| C6 | Роутер: **SSH пускает `root` по паролю** (dropbear) | `192.168.1.1:22` | 🟠 Высоко | Отчёт 15.11 §4.1: «SSH пускает по паролю для `root`» | ⚠️ **Противоречие данных** — `homelab.json`/`INVENTORY.md` утверждают «SSH только по ключу». **[ПРОВЕРИТЬ]** при возврате доступа |
| C7 | **Пароль Wi-Fi = пароль админки репитера** (один пароль на всё) | роутер + `192.168.1.223` | 🟠 Высоко | Отчёт 15.11 §4.1 | ⏳ **Открыто** |
| C8 | **LuCI (`:80`/`:443`) и SSH доступны всей LAN** без ограничения по адресам | `192.168.1.1` | 🟡 Средне | Порты `22, 53, 80, 443` открыты; зона `lan` — `input ACCEPT` | ⏳ **Открыто** |
| C9 | **Нет сегментации IoT**: камеры/NVR/умный дом/ТВ/ПК — в одной зоне с роутером | вся сеть | 🟡 Средне | Зона `lan` одна, `input ACCEPT`, `forward ACCEPT`; 37 DHCP-аренд, 48 соседей | ⏳ **Открыто** |
| C10 | **Нет WPA3-only / статус PMF (802.11w) и WPS не подтверждён** | Wi-Fi `RT-WIFI-47`, 3 радио | 🟡 Средне | Шифрование — `sae-mixed` (WPA2/WPA3). WPS/PMF в данных **не отражены** | ❓ **[ПРОВЕРИТЬ]** — обязательная проверка (`uci show wireless`, `iwinfo`) |
| C11 | Самоподписанный сертификат LuCI | `192.168.1.1:443` | 🟡 Средне | Отчёт 15.11 §1 | ⏳ **Открыто** |
| C12 | Устаревшие/необновлённые прошивки XM-камер (нет подтверждённой версии) | камеры | 🟡 Средне | Косвенно: семейство XM, `version_web="2.0.0.0"` | ❓ **[ПРОВЕРИТЬ]** — точные версии неизвестны |
| C13 | Один DHCP-диапазон, нет статических lease/журнала появления новых устройств | роутер | 🟢 Низко | 37 аренд, из них часть — IoT/телефоны | ⏳ **Открыто** |
| C14 | Нестабильный узел `192.168.1.132` (периодически `5000`, потом «No route to host») | `192.168.1.132` | ⚪ Инфо | Отчёт 15.11 §4.7 | ❓ **[ПРОВЕРИТЬ]** — спящее устройство? |

**Что закрыто / что уже проверено (не открытые риски):**

- **DNAT с WAN нет.** По данным 15.11 удалены мёртвый проброс `HA-External-Access` (`8123` → `192.168.1.156`, хост мёртв) и дубль правила WireGuard. В бэкапе `firewall-backup.json` они ещё присутствуют — это **состояние до правок**. [ФАКТ]
- **WAN корректно закрыт:** зона `wan` — `input REJECT`, `forward DROP`, `masq 1`; `miniupnpd` не установлен → **UPnP на WAN нет**. [ФАКТ]
- **WAN за CGNAT:** WAN-адрес `172.25.213.7` — частный; входящие из интернета до роутера не доходят. [ФАКТ]
- **Ретранслятор `192.168.1.223`:** remote management / UPnP / DMZ выключены, правил проброса 0, облако Wavlink выключено. [ФАКТ]

---

## D. Как исправить

Порядок: сначала бэкап, потом по одному изменению с проверкой.

```bash
H=/root/workspace/homelab/homelab.py
python3 $H router backup          # ОБЯЗАТЕЛЬНО перед правками firewall/сети
python3 $H router exec "uci show wireless"
python3 $H router exec "uci show firewall"
```

> **Правило безопасности:** не отрезать себе SSH/LAN. Правки firewall применять только имея рабочий канал (SSH-ключ уже на роутере, либо физический доступ). После каждого `uci commit` + reload — проверять доступность.

### D.1. Wi-Fi: WPA3-only или `sae-mixed` + обязательный PMF, отключить WPS

`RT-WIFI-47` уже `sae-mixed` [ФАКТ]. Минимально — **включить обязательный PMF** и **выключить WPS**.

```bash
# посмотреть интерфейсы: wireless.@wifi-iface[N]
uci show wireless | grep -E "wifi-iface|encryption|ieee80211w|wps|ssid"

# для КАЖДОГО wifi-iface (пример с индексом 0, повторить для остальных):
uci set wireless.@wifi-iface[0].encryption='sae-mixed'   # WPA2+WPA3 (совместимо)
# либо строго WPA3, если все клиенты умеют SAE:
# uci set wireless.@wifi-iface[0].encryption='sae'

uci set wireless.@wifi-iface[0].ieee80211w='2'   # PMF: 2 = обязательный
uci set wireless.@wifi-iface[0].wps_pushbutton='0'
uci set wireless.@wifi-iface[0].wps_label='0'

uci commit wireless
wifi reload
```

Проверка: `iwinfo` (см. F). Если после `ieee80211w=2` старый клиент не подключается — временно `ieee80211w=1` (опциональный PMF), но это компромисс.

### D.2. SSH только по ключу (dropbear)

**Сначала убедиться, что ключ уже лежит в `/etc/dropbear/authorized_keys`**, иначе можно потерять доступ.

```bash
# проверить наличие ключа
ls -l /etc/dropbear/authorized_keys

# если ключа нет — добавить свой публичный (HOMELAB_SSH_KEY), затем:
uci show dropbear
uci set dropbear.@dropbear[0].PasswordAuth='off'
uci set dropbear.@dropbear[0].RootPasswordAuth='off'
uci commit dropbear
/etc/init.d/dropbear restart
```

Проверка (с доверенного хоста): вход по ключу работает; вход по паролю — отклонён. Не закрывать текущую сессию, пока не подтверждён вход новой.

### D.3. Ограничить LuCI/SSH доверенными адресами

uhttpd слушает `:80`/`:443`. Ограничить доступ можно правилом firewall на зоне `lan`.

```bash
# оставить uhttpd только на LAN-адресе
uci set uhttpd.main.listen_http='192.168.1.1:80'
uci set uhttpd.main.listen_https='192.168.1.1:443'
uci commit uhttpd
/etc/init.d/uhttpd restart

# разрешить LuCI (80/443) и SSH (22) только доверенным IP, остальным в lan — REJECT
# (пример: разрешаем 192.168.1.239 — ПК)
uci add firewall rule
uci set firewall.@rule[-1].name='Allow-LuCI-Trusted'
uci set firewall.@rule[-1].src='lan'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].dest_port='80 443'
uci set firewall.@rule[-1].src_ip='192.168.1.239'
uci set firewall.@rule[-1].target='ACCEPT'

uci add firewall rule
uci set firewall.@rule[-1].name='Deny-LuCI-Other'
uci set firewall.@rule[-1].src='lan'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].dest_port='80 443'
uci set firewall.@rule[-1].target='REJECT'

uci commit firewall
fw4 reload
```

> Внимание: правило `Deny-LuCI-Other` **не должно** задеть SSH (порт `22`) и **не должно** задеть зону `wan`. Проверять `fw4 print` до перезагрузки. При риске блокировки — сначала добавить правило для своего текущего IP.

### D.4. Отключить DNAT / port forward

На 15.11 DNAT уже нет [ФАКТ]. Подтвердить и не возвращать:

```bash
uci show firewall | grep -i redirect     # не должно быть записей с src='wan' и target='DNAT'
fw4 print | sed -n '/chain dstnat/,/^}/p'
```

Если появятся — удалить: `uci delete firewall.<name>` → `uci commit firewall` → `fw4 reload`.

### D.5. Обновление пакетов

Офлайн `opkg update` не работает. Обновление прошивки/пакетов — **только вручную пользователем из доверенного источника**, не из этой среды. Фиксировать версию до/после (`ubus call system board`).

### D.6. Гостевой SSID + VLAN для IoT-камер и NVR

Цель: камеры/NVR в отдельной зоне без доступа к ПК/телефонам/роутеру; NVR видит камеры, HA (при необходимости) видит NVR; камеры **не имеют выхода в интернет**.

```bash
# 1) отдельный интерфейс/бридж для IoT
uci set network.iot=interface
uci set network.iot.proto='static'
uci set network.iot.device='br-iot'
uci set network.iot.ipaddr='192.168.30.1'
uci set network.iot.netmask='255.255.255.0'
uci set network.iot.delegate='0'

uci set network.iotdev=device
uci set network.iotdev.name='br-iot'
uci set network.iotdev.type='bridge'

uci commit network
/etc/init.d/network reload

# 2) отдельный SSID, привязанный к IoT-сети
uci set wireless.iotwifi=wifi-iface
uci set wireless.iotwifi.device='radio0'      # при необходимости добавить и на radio1/radio2
uci set wireless.iotwifi.mode='ap'
uci set wireless.iotwifi.network='iot'
uci set wireless.iotwifi.ssid='RT-IOT'
uci set wireless.iotwifi.encryption='sae-mixed'
uci set wireless.iotwifi.ieee80211w='2'
uci set wireless.iotwifi.isolate='1'          # клиенты не видят друг друга
uci set wireless.iotwifi.key='<СИЛЬНЫЙ_УНИКАЛЬНЫЙ_ПАРОЛЬ>'
uci commit wireless
wifi reload

# 3) зона firewall для IoT: без forward наружу по умолчанию
uci add firewall zone
uci set firewall.@zone[-1].name='iot'
uci set firewall.@zone[-1].input='REJECT'
uci set firewall.@zone[-1].output='ACCEPT'
uci set firewall.@zone[-1].forward='REJECT'
uci add_list firewall.@zone[-1].network='iot'

# IoT -> LAN запрещено (нет forwarding iot->lan). Доступ к NVR — только если NVR тоже в iot,
# либо точечно разрешить HA(lan)->NVR по RTSP:
uci add firewall rule
uci set firewall.@rule[-1].name='Allow-HA-to-NVR-RTSP'
uci set firewall.@rule[-1].src='lan'
uci set firewall.@rule[-1].dest='iot'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].dest_port='554'
uci set firewall.@rule[-1].target='ACCEPT'

uci commit firewall
fw4 reload
```

> Если камерам нужен только локальный просмотр (без облака/P2P) — **не** добавлять forwarding `iot → wan`. Это автоматически блокирует камерам выход в интернет.
> Внимание: перенос камер/NVR в новую подсеть меняет их IP — **сначала** перенастроить NVR/HA на новые адреса, чтобы не сломать запись. Делать по одному устройству.

### D.7. Камеры/NVR: сменить пароли, отключить P2P/UPnP/Telnet

Через веб-интерфейс каждого устройства (нужен логин/пароль админа — сейчас **нет доступа**, статус C2/C3 открыт):

- сменить пароль на длинный уникальный (не `admin`, не пустой, **не тот же**, что Wi-Fi/роутер);
- отключить **P2P/облако** (XMEye/JFTech-облако, «Cloud», «P2P», серийный-номер-доступ);
- отключить **UPnP** и **Telnet** в настройках сети;
- закрыть/сменить порт `34567`, если он не нужен;
- включить HTTPS на веб-интерфейсе, если прошивка умеет;
- отключить ONVIF-обнаружение, если не используется;
- создать отдельную учётку «только просмотр», где возможно.

Пароли не подбираем и в отчёт не выводим.

---

## E. Блокировка

Здесь два разных смысла — разбираю оба.

### E.1. Что и как блокировать на роутере (по нашей инициативе)

| Что блокируем | Как | Команда |
|---|---|---|
| Чужие/неизвестные устройства (по MAC) | не выдавать DHCP + при желании отсечь правилом | см. ниже |
| WPS | выключить на всех wifi-iface | `wps_pushbutton=0`, `wps_label=0` (D.1) |
| IoT → LAN | зона IoT с `forward REJECT`, без forwarding `iot→lan` | D.6 |
| Камеры/NVR → WAN (интернет) | не создавать forwarding `iot→wan`; при необходимости явный REJECT | см. ниже |
| Порты `34567/5555/554/80` из WAN | уже закрыто (`wan input REJECT`, DNAT нет); добавить явный drop для глубины | см. ниже |
| UPnP / DMZ | `miniupnpd` не установлен; DMZ не настроен — не включать | — |

**Блокировка устройства по MAC (мягкая мера — не выдавать адрес):**

```bash
uci add dhcp host
uci set dhcp.@host[-1].name='blocked-<метка>'
uci set dhcp.@host[-1].mac='AA:BB:CC:DD:EE:FF'
uci set dhcp.@host[-1].ignore='1'      # не выдавать lease
uci commit dhcp
/etc/init.d/dnsmasq restart
```

**Явный запрет IoT → интернет (defense-in-depth):**

```bash
uci add firewall rule
uci set firewall.@rule[-1].name='Block-IoT-To-WAN'
uci set firewall.@rule[-1].src='iot'
uci set firewall.@rule[-1].dest='wan'
uci set firewall.@rule[-1].target='REJECT'
uci commit firewall
fw4 reload
```

**Явный drop «опасных» портов с WAN (страховка, если когда-нибудь появится DNAT):**

```bash
for P in 34567 5555 554 80 443 22; do
  uci add firewall rule
  uci set firewall.@rule[-1].name="Drop-WAN-$P"
  uci set firewall.@rule[-1].src='wan'
  uci set firewall.@rule[-1].proto='tcp'
  uci set firewall.@rule[-1].dest_port="$P"
  uci set firewall.@rule[-1].target='DROP'
done
uci commit firewall
fw4 reload
```

> MAC-фильтрация — **слабая** мера (MAC подделывается). Основная защита — WPA3/PMF, сильный уникальный пароль Wi-Fi и сегментация.

### E.2. Если пользователь имел в виду «что-то блокирует доступ/устройство»

Тогда это **диагностика блокировки**, а не наша настройка. Порядок:

```bash
# 1) живые логи роутера
logread | tail -100
logread -e firewall | tail -50
logread -e dnsmasq | tail -50

# 2) состояние firewall
fw4 print
uci show firewall
nft list ruleset | head -120

# 3) Wi-Fi: подключён ли клиент, не отсечён ли
iwinfo
iwinfo <iface> assoclist        # список ассоциаций

# 4) DHCP: выдан ли адрес
cat /tmp/dhcp.leases
ubus call dhcp.leases

# 5) сеть на самом устройстве (если есть доступ)
ip -br a; ip r
```

Чем проверить, что именно блокирует:

- **Клиент не получает IP** → смотреть `logread -e dnsmasq` (нет аренды), проверять `dhcp.@host[].ignore`, пул, MAC-фильтр.
- **Клиент получает IP, но нет доступа к LAN** → `fw4 print` (правило REJECT/зона), `nft list ruleset`.
- **Устройство не видно в ассоциациях** → `iwinfo <iface> assoclist`; возможно, неверный PSK или PMF-несовместимость после D.1.
- **Есть интернет-адрес, но нет наружу** → зона/forwarding, `masq`, маршрут по умолчанию (`ip r`).
- **Пропал сам SSH/LuCI** → правило firewall отсекло управление; откат через физический доступ/`failsafe` (только по инструкции пользователю).

---

## F. Проверка после правок

Выполнять после каждого блока изменений.

```bash
H=/root/workspace/homelab/homelab.py

# Wi-Fi: шифрование/PMF/WPS
python3 $H router exec "uci show wireless"
python3 $H router exec "iwinfo"
python3 $H router exec "iwinfo <iface> assoclist"

# Firewall: зоны, правила, отсутствие DNAT
python3 $H router exec "fw4 print"
python3 $H router exec "uci show firewall"
python3 $H router exec "fw4 print | sed -n '/chain dstnat/,/^}/p'"

# Слушающие сервисы на роутере
python3 $H router exec "netstat -lntp 2>/dev/null || ss -lntp 2>/dev/null"

# SSH: по ключу работает, по паролю — нет (с доверенного хоста)
ssh -o PreferredAuthentications=password root@192.168.1.1   # ожидается отказ

# Камеры/NVR: порты и HTTP
python3 $H cam 192.168.1.10
python3 $H cam 192.168.1.190

# DHCP-аренды: не появилось ли новых устройств
python3 $H router exec "cat /tmp/dhcp.leases"

# ADB на приставке (не должен отвечать)
python3 $H tv shell "getprop service.adb.tcp.port"   # ожидается -1 / пусто
```

Критерии «исправлено»: `fw4 print` без DNAT с `wan`; `wan input REJECT`; PMF обязателен; WPS `0`; SSH-пароль отключён; IoT-зона изолирована; камеры не имеют forwarding в `wan`.

---

## G. Что нужно от пользователя

- [ ] Подключить устройство-инициатор к домашней сети `192.168.1.0/24` (Wi-Fi `RT-WIFI-47` или Ethernet).
- [ ] Вернуть SSH к роутеру `192.168.1.1` (ключ `HOMELAB_SSH_KEY`) **или** выполнить скан с ПК из раздела B и прислать вывод.
- [ ] Выполнить `iwinfo` / `uci show wireless` и подтвердить: реальное шифрование, **статус WPS**, **статус PMF (802.11w)** — сейчас [ПРОВЕРИТЬ].
- [ ] Уточнить статус SSH на роутере: **по ключу или по паролю** (в данных противоречие C6).
- [ ] Дать доступ (логин/пароль админа) к камерам/NVR **или** самостоятельно сменить пароли и отключить P2P/облако/UPnP/Telnet.
- [ ] Подтвердить готовность к правкам firewall/сети (нужен рабочий канал, чтобы не потерять доступ).
- [ ] Разделить пароли: Wi-Fi ≠ админка репитера ≠ камеры/NVR.
- [ ] Разрешить отдельный VLAN/SSID для IoT-камер (с перенастройкой NVR/HA, чтобы не сломать запись).
- [ ] Перед изменениями — согласовать бэкап (`homelab.py router backup`).

---

## H. Ссылки на использованные файлы-источники

Все данные — **по состоянию на 15.11.2026**:

- `/root/workspace/network-report.md` — основной отчёт сканирования (карта сети, детали устройств, статус исправлений).
- `/root/workspace/firewall-backup.json` — снимок firewall OpenWrt **до правок** (содержит удалённые `HA-External-Access` DNAT `8123→.156` и дубль `Allow-WG`).
- `/root/workspace/homelab/homelab.json` — инвентарь устройств (IP, роли, заметки; без секретов).
- `/root/workspace/homelab/INVENTORY.md` — человекочитаемый инвентарь (ключевые узлы, камеры/NVR, умный дом).
- `/root/workspace/network-report.html` — HTML-версия отчёта сканирования.

Локальная проверка среды (16.11.2026, для раздела A): отсутствуют `iw`, `iwinfo`, `airodump-ng`, `nmcli`, `nmap`, `arp`; `ip` не установлен; `/sys/class/net` — `Permission denied`.

**Свежее сканирование в этой сессии не выполнялось.** Раздел C требует перепроверки после восстановления доступа.

---

## Приложение: статус исправлений (по состоянию на 15.11.2026)

| Проблема | Действие | Статус |
|---|---|---|
| ADB `:5555` без авторизации на `192.168.1.139` | `service.adb.tcp.port=-1`, `persist.adb.tcp.port=-1`, рестарт `adbd` | ✅ Исправлено (порт закрыт) |
| Камеры XM / NVR: HTTP без TLS | нужен логин/пароль админа | ⏳ Ожидает доступа |
| Wavlink WN570HA1B: дефолтный сертификат | remote mgmt/UPnP/DMZ выкл, пробросов 0 | ✅ Проверено (риск низкий) |
| OpenWrt: пробросы, SSH/LuCI, VLAN для IoT | удалён мёртвый DNAT, убран дубль WireGuard | ⏳ Частично (DNAT закрыт, VLAN — нет) |
