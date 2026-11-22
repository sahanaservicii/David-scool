<#
.SYNOPSIS
  Единый (single-file) PowerShell-инструмент диагностики доступности конечного адреса для подготовки заявки сетевикам/СБ.

.DESCRIPTION
  Самодостаточный .ps1 для сценария: новое устройство/сервис в сегменте с жёсткой фильтрацией не работает из-за закрытых портов
  → нужно точно определить требуемые потоки и сформировать обоснование для согласования/разблокировки.

  Включает диагностику (DNS, ICMP, трассировка, TCP/UDP-спецификация портов, HTTP(S), локальный firewall, мониторинг
  фактических соединений) и встроенные материалы комплекта (инструкция, чек-лист, шаблоны портов, .cmd-обёртка), которые
  можно показать или экспортировать в файлы.

  Запускать на Windows-машине в том же сетевом сегменте/с теми же ограничениями, что и проблемное устройство
  (или на самом устройстве, если это Windows).

.PARAMETER Target
  Конечный адрес: FQDN, IP, URL (http/https) или host:port. Обязателен для режима диагностики.

.PARAMETER Ports
  Список TCP-портов для активной проверки (например 443,8443,554).

.PARAMETER UdpPorts
  Список UDP-портов, требуемых устройству/сервису (активно не probing'уются; фиксируются как требуемые и наблюдаются в мониторинге).

.PARAMETER Profiles
  Готовые наборы портов: Web, RDP, SMB, DNS, LDAP, SSH, WinRM, SQL, Mail, Printer, Camera, NTP, MQTT, DB, AD, SIP, SNMP.

.PARAMETER PortsFile
  Файл со спецификацией портов (точность под устройство): CSV с заголовками Proto,Port,Direction,Description
  или строки вида "TCP 443 outbound HTTPS API", "123/udp".

.PARAMETER MonitorSeconds
  Наблюдать активные TCP/UDP-соединения к целевому адресу N секунд (запустите устройство/приложение параллельно).

.PARAMETER ProcessName
  Ограничить мониторинг процессом (имя без .exe).

.PARAMETER DeviceName
  Название/модель устройства или сервиса (для черновика заявки).

.PARAMETER Purpose
  Назначение доступа/бизнес-обоснование (для черновика заявки).

.PARAMETER OutDir
  Каталог для отчётов диагностики (создаётся автоматически).

.PARAMETER TimeoutMs
  Таймаут TCP-подключения в миллисекундах (по умолчанию 3000).

.PARAMETER NoTrace
  Не выполнять трассировку маршрута.

.PARAMETER ExportBundle
  Экспортировать встроенный комплект файлов (README, чек-лист, CSV-шаблоны, .cmd) в каталог -ExportDir.

.PARAMETER ExportDir
  Каталог для экспорта комплекта (по умолчанию текущий).

.PARAMETER ShowGuide
  Показать встроенную инструкцию (README).

.PARAMETER ShowChecklist
  Показать встроенный чек-лист точности.

.PARAMETER ShowPortsTemplate
  Показать шаблон CSV портов.

.PARAMETER ShowPortsExample
  Показать пример CSV портов.

.PARAMETER ShowHelp
  Показать краткую справку по использованию одного файла.

.EXAMPLE
  .\Check-EndpointAccess.ps1 -ExportBundle -ExportDir .\bundle

.EXAMPLE
  .\Check-EndpointAccess.ps1 -Target 10.20.30.40 -PortsFile .\device-ports.csv -MonitorSeconds 300 -DeviceName "Камера" -Purpose "Видеонаблюдение"

.NOTES
  Ограничения: UDP активно не probing'уется (подтверждать мониторингом/захватом); правила сетевого оборудования с клиента не видны.
  Использовать только для согласованных проверок в рамках политик организации.
#>

[CmdletBinding()]
param(
    [string]$Target,

    [int[]]$Ports = @(),

    [int[]]$UdpPorts = @(),

    [string[]]$Profiles = @(),

    [string]$PortsFile,

    [int]$MonitorSeconds = 0,

    [string]$ProcessName,

    [string]$DeviceName,

    [string]$Purpose,

    [string]$OutDir = (Join-Path (Get-Location) ("endpoint-report-{0:yyyyMMdd-HHmmss}" -f (Get-Date))),

    [int]$TimeoutMs = 3000,

    [switch]$NoTrace,

    [switch]$ExportBundle,

    [string]$ExportDir = (Get-Location).Path,

    [switch]$ShowGuide,

    [switch]$ShowChecklist,

    [switch]$ShowPortsTemplate,

    [switch]$ShowPortsExample,

    [switch]$ShowHelp
)

$script:EmbeddedReadme = @'
# Check-EndpointAccess.ps1

PowerShell-инструмент для диагностики доступности конечного адреса (устройства/сервиса) из текущего сетевого сегмента и подготовки точного, доказательного обоснования для сетевиков/службы безопасности.

Ориентирован на сценарий: новое устройство/сервис в сегменте с жёсткой фильтрацией не работает из-за закрытых портов → нужно определить требуемые потоки и сформировать заявку на согласование/разблокировку.

## Что проверяет

1. **Локальная конфигурация** — интерфейсы, IP, шлюз, DNS, прокси.
2. **DNS** — разрешение имени в IP (A/AAAA).
3. **ICMP** — ping (если разрешён).
4. **Маршрут/трассировка** — вероятная точка обрыва (`Test-NetConnection -TraceRoute` / `tracert`).
5. **Порты по спецификации** (точность под устройство/сервис): активная проверка TCP (`OPEN` / `CLOSED/REFUSED` / `TIMEOUT/FILTERED` / `UNREACHABLE`) и учёт UDP как требуемых потоков (активный UDP-probe с клиента ненадёжен, фиксируется для заявки/мониторинга).
6. **HTTP/HTTPS** — пробный запрос при указании URL.
7. **Локальный firewall** — состояние профилей (best effort).
8. **Мониторинг фактических соединений** (ключевой режим) — реальные TCP/UDP-попытки к целевому IP за период (`Get-NetTCPConnection`/`Get-NetUDPEndpoint`), порты/состояния/процесс/PID/счётчики (`SynSent` — признак фильтрации/drop; `Established` — доступно).

## Режим «один файл» (передача одним .ps1)

`Check-EndpointAccess.ps1` — самодостаточный скрипт: содержит встроенную инструкцию, чек-лист, шаблоны портов и обёртку запуска. Можно передать только его.

- Показать инструкцию/материалы: `-ShowGuide`, `-ShowChecklist`, `-ShowPortsTemplate`, `-ShowPortsExample`
- Развернуть полный комплект файлов рядом: `-ExportBundle -ExportDir .\tools`

**Состав комплекта (при экспорте/в полном наборе):** `Check-EndpointAccess.ps1`, `Run-CheckEndpointAccess.cmd`, `README-Check-EndpointAccess.md`, `ACCURACY-CHECKLIST.md`, `device-ports.template.csv`, `device-ports.example.csv`.

## Требования

- Windows PowerShell 5.1+ или PowerShell 7+.
- Модуль `NetTCPIP` (обычно есть в Windows 8/Server 2012+).
- Базовые проверки работают без админ-прав; трассировка/часть сведений/захват трафика могут требовать повышенных прав.
- Запускать на хосте **в том же сетевом сегменте/с теми же ограничениями**, что и проблемное устройство (или на самом устройстве, если это Windows).

## Параметры (основные)

- `-Target` (обяз.) — FQDN, IP, URL (`http/https`) или `host:port`.
- `-Ports <int[]>` — TCP-порты для активной проверки.
- `-UdpPorts <int[]>` — UDP-порты, требуемые устройству (учитываются в спецификации/заявке, подтверждаются мониторингом).
- `-Profiles <string[]>` — профили: `Web, RDP, SMB, DNS, LDAP, SSH, WinRM, SQL, Mail, Printer, Camera, NTP, MQTT, DB, AD, SIP, SNMP`.
- `-PortsFile <path>` — файл спецификации портов производителя/устройства (CSV с `Proto,Port,Direction,Description` или строки вида `TCP 443 ...`, `123/udp`). **Рекомендуется для точности.**
- `-MonitorSeconds <int>` — наблюдать фактические соединения N секунд (запустите устройство/приложение параллельно).
- `-ProcessName <string>` — фильтр мониторинга по процессу (без `.exe`).
- `-DeviceName <string>`, `-Purpose <string>` — подставляются в черновик заявки.
- `-OutDir <path>`, `-TimeoutMs <int>` (по умолчанию 3000), `-NoTrace`.

## Рекомендуемый сценарий (точность под конкретное устройство)

1. **Возьмите спецификацию вендора** (официальные порты/протоколы) и заполните `device-ports.csv` по шаблону.
2. **Базовая проверка по спецификации + метаданные заявки:**
   ```powershell
   .\Run-CheckEndpointAccess.cmd -Target 10.20.30.40 -PortsFile .\device-ports.csv -DeviceName "Камера/модель" -Purpose "Видеонаблюдение/доступ к сервису"
   ```
3. **Зафиксируйте реальные потоки** во время воспроизведения проблемы (ключевой шаг):
   ```powershell
   .\Run-CheckEndpointAccess.cmd -Target 10.20.30.40 -PortsFile .\device-ports.csv -MonitorSeconds 300 -ProcessName "ИмяПроцесса" -DeviceName "..." -Purpose "..."
   ```
4. Сверьте `requested-ports.csv` (спецификация) и `observed.csv` (факт), проверьте `TIMEOUT/FILTERED` и `SynSent`, приложите отчёт к заявке (см. `ACCURACY-CHECKLIST.md`).

## Другие примеры

Веб/URL:
```powershell
.\Check-EndpointAccess.ps1 -Target "https://app.example.local" -Profiles Web
```
Конкретные порты (TCP) + UDP:
```powershell
.\Check-EndpointAccess.ps1 -Target 10.20.30.40 -Ports 443,8443,554 -UdpPorts 123,3702
```
Без трассировки, в заданный каталог:
```powershell
.\Check-EndpointAccess.ps1 -Target host.local -Profiles SSH -NoTrace -OutDir .\report-host
```

> При блокировке запуском скриптов используйте `Run-CheckEndpointAccess.cmd` или: `powershell -NoProfile -ExecutionPolicy Bypass -File .\Check-EndpointAccess.ps1 ...`

## Формат `-PortsFile`

CSV (рекомендуется), заголовки: `Proto,Port,Direction,Description`
```csv
Proto,Port,Direction,Description
TCP,443,outbound,HTTPS API
UDP,123,outbound,NTP
```
Также поддерживаются строки: `TCP 443 описание`, `UDP 123`, `443/tcp`.

## Выходные артефакты (каталог отчёта)

- `summary.txt` — сводка по всем уровням, спецификация, факты, черновик заявки.
- `request-for-network.txt` — черновик запроса для сетевиков/СБ (заполните поля источника/контакта/обоснования).
- `details.json` — структурированные данные (цель, IP, спецификация, результаты, наблюдения, findings).
- `requested-ports.csv` — итоговая спецификация требуемых портов (профили/файл/параметры).
- `port-tests.csv` — результаты проверок по портам.
- `observed.csv` — фактически наблюдавшиеся соединения (в т.ч. `SynSent`, счётчики, время).
- `run.log` — лог выполнения.

## Интерпретация

- **OPEN** — TCP-соединение установлено, порт доступен.
- **CLOSED/REFUSED** — хост достижим по сети, но соединение отклонено (RST): обычно сервис/хост, не сетевой фильтр.
- **TIMEOUT/FILTERED** — нет ответа за таймаут: вероятна фильтрация/drop на коммутаторе/фаерволе/ACL (сопоставляйте с трассировкой).
- **UNREACHABLE** — нет маршрута/сеть недостижима.
- **SKIPPED/UDP** — UDP не проверяется активно; требование подтверждается мониторингом/захватом.
- В мониторинге: **SynSent** — признак блокировки; **Established** — поток работает; **UDP endpoint** — факт обмена/привязки.

## Ограничения

- Скрипт **не видит** реальные правила на сетевом оборудовании/СЗИ — вывод о точке блокировки вероятностный (по timeout/SynSent/трассировке).
- **UDP** без серверного ответа достоверно не подтверждается активной проверкой; для точности используйте `-MonitorSeconds` и при необходимости `pktmon`/`netsh trace` (админ-права, отдельное согласование).
- Часть проверок зависит от прав и политики ОС (трассировка, доступ к состояниям/журналам).
- Приложение может обращаться к разным FQDN/IP; для полноты проверяйте все релевантные назначения и сверяйтесь со спецификацией производителя.

## Безопасность

Только диагностика (DNS, ping, трассировка, попытки TCP-connect, чтение состояния соединений). Скрипт не изменяет настройки сети/фаервола и не выполняет эксплуатацию уязвимостей. Используйте исключительно для согласованных проверок в рамках политик вашей организации.
'@
$script:EmbeddedChecklist = @'
# Чек-лист: точное определение портов/потоков для конкретного устройства или сервиса

Цель: собрать достоверный перечень сетевых потоков (источник → назначение, протокол, порт, направление, назначение) и доказательства для согласования/разблокировки у сетевиков и службы безопасности.

> Проверки выполняйте только в рамках политик вашей организации и на согласованных системах. Скрипт фиксирует факты с клиента и не меняет настройки сети/оборудования.

## 1. Подготовка (до запуска)
- [ ] Определите цель: устройство/сервис, модель/версия ПО, инв. номер, владелец, назначение.
- [ ] Определите источник: хост, с которого выполняется проверка (тот же сегмент/VLAN/зона, что и проблемное устройство), его IP/подсеть.
- [ ] Определите назначение: FQDN/IP/URL, известные роли (сервер управления, обновления, NTP, облако недоступно и т.п.).
- [ ] Соберите **спецификацию производителя/вендора**: официальный список портов/протоколов/направлений. Сохраните ссылку/документ (для приложения к заявке).
- [ ] Заполните файл портов на основе спецификации (см. `device-ports.template.csv` / `device-ports.example.csv`), колонки: `Proto,Port,Direction,Description`.
- [ ] Уточните окно проверки: когда устройство реально выполняет проблемную операцию (загрузка, регистрация, поток, синхронизация).

## 2. Базовая диагностика (уровни L3–L7 с клиента)
Запустите на Windows-машине в том же сетевом контексте:
```powershell
.\Run-CheckEndpointAccess.cmd -Target <IP|FQDN|URL> -PortsFile .\device-ports.csv -DeviceName "<модель/система>" -Purpose "<зачем нужен доступ>"
```
- [ ] Убедитесь, что DNS разрешается в ожидаемые IP (п.2 отчёта `summary.txt`).
- [ ] Проверьте маршрут/трассировку: где обрывается путь (п.4) — это вероятная зона фильтрации.
- [ ] Зафиксируйте результаты по TCP-портам из спецификации (п.5, `port-tests.csv`):
  - `OPEN` — порт доступен.
  - `CLOSED/REFUSED` — достижимо по сети, но сервис не принимает (не сетевой фильтр).
  - `TIMEOUT/FILTERED`/`UNREACHABLE` — вероятная блокировка/проблема маршрутизации.
- [ ] Для URL проверьте HTTP(S) пробу (п.6).

## 3. Фиксация фактических потоков (ключевой шаг для точности)
Запустите мониторинг **во время воспроизведения** работы устройства/приложения (достаточная длительность, обычно 2–10 минут; при необходимости фильтр по процессу):
```powershell
.\Run-CheckEndpointAccess.cmd -Target <IP|FQDN> -PortsFile .\device-ports.csv -MonitorSeconds 300 -ProcessName "<имя_процесса_если_есть>" -DeviceName "<...>" -Purpose "<...>"
```
- [ ] Воспроизведите проблемный сценарий в окне мониторинга (подключение, логин, передача данных, обновление).
- [ ] Проанализируйте `observed.csv` и п.8 `summary.txt`:
  - TCP `Established` — фактически работающий поток.
  - TCP `SynSent` — попытка без ответа (сильный признак фильтрации/drop).
  - UDP `endpoint` — факт обмена/привязки (доставка требует подтверждения ответом/захватом).
- [ ] Сверьте наблюдаемые порты со спецификацией: отметьте недостающие/лишние/заблокированные.

## 4. UDP и спорные случаи
- [ ] Помните: активная проверка UDP с клиента ненадёжна. Требуемые UDP-порты фиксируйте в `-PortsFile`/`-UdpPorts` и подтверждайте мониторингом.
- [ ] При необходимости и наличии прав/согласования используйте захват (`pktmon`, `netsh trace`) для подтверждения отправки/ответа UDP и точных потоков — приложите вывод как доп. доказательство.
- [ ] Если адресов назначения несколько (балансировка/DNS round-robin), повторите проверку и убедитесь, что все IP покрыты политикой.

## 5. Подготовка заявки для сетевиков / СБ
- [ ] Возьмите за основу `request-for-network.txt` из каталога отчёта и заполните поля: инициатор/контакт, источник (IP/сегмент/VLAN), точное назначение доступа, бизнес-обоснование.
- [ ] Укажите потоки в формате: `<SRC IP/сегмент> → <DST IP/FQDN> : Proto/Port, направление, назначение` (объедините `requested-ports.csv` и `observed.csv`, отметьте источник: вендор/факт).
- [ ] Приложите доказательства: `summary.txt`, `details.json`, `port-tests.csv`, `observed.csv`, спецификацию производителя, при наличии — трассировку/захват.
- [ ] Для каждого проблемного потока укажите признак: `TIMEOUT/FILTERED`/`SynSent`, время проверки, хост-источник, последняя достижимая точка трассировки.

## 6. Критерий готовности
- [ ] Перечень портов опирается на спецификацию производителя **и** подтверждён фактическим мониторингом там, где это возможно.
- [ ] Для заблокированных потоков есть воспроизводимые факты (статус/состояние, время, трассировка).
- [ ] Заявка содержит все поля, нужные для реализации правила (источник, назначение, proto/port, направление, обоснование) и приложенные артефакты.
'@
$script:EmbeddedPortsTemplate = @'
Proto,Port,Direction,Description
TCP,443,outbound,Описание назначения
UDP,123,outbound,Описание назначения
'@
$script:EmbeddedPortsExample = @'
Proto,Port,Direction,Description
TCP,443,outbound,HTTPS API / веб-интерфейс / обновления
TCP,80,outbound,HTTP (редирект/служебные запросы)
TCP,554,outbound,RTSP видеопоток
TCP,8000,outbound,Сервисный/управляющий порт устройства (пример)
UDP,123,outbound,NTP синхронизация времени
UDP,3702,outbound,WS-Discovery (если используется)
TCP,8883,outbound,MQTT over TLS (если используется)
'@
$script:EmbeddedCmd = @'
@echo off
setlocal
REM Запуск диагностики доступности конечного адреса (обход ExecutionPolicy для текущего процесса).
REM Примеры:
REM   Run-CheckEndpointAccess.cmd -Target 10.20.30.40 -PortsFile "%~dp0device-ports.example.csv" -MonitorSeconds 120
REM   Run-CheckEndpointAccess.cmd -Target "https://app.example.local" -Profiles Web

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Check-EndpointAccess.ps1" %*
set "RC=%ERRORLEVEL%"
echo.
echo Exit code: %RC%
if /I "%~1"=="" pause
exit /b %RC%
'@

function Show-QuickHelp {
    Write-Host "Check-EndpointAccess.ps1 — единый файл диагностики доступности адреса (Windows/PowerShell)." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Экспорт встроенного комплекта (README, чек-лист, CSV, .cmd):" 
    Write-Host "  .\Check-EndpointAccess.ps1 -ExportBundle -ExportDir .\bundle"
    Write-Host ""
    Write-Host "Показать встроенные материалы:" 
    Write-Host "  -ShowGuide | -ShowChecklist | -ShowPortsTemplate | -ShowPortsExample"
    Write-Host ""
    Write-Host "Диагностика (точность под устройство: спецификация + мониторинг фактов):" 
    Write-Host '  .\Check-EndpointAccess.ps1 -Target 10.20.30.40 -PortsFile .\device-ports.csv -MonitorSeconds 300 -DeviceName "Устройство" -Purpose "Назначение"'
    Write-Host '  .\Check-EndpointAccess.ps1 -Target "https://app.example.local" -Profiles Web'
    Write-Host ""
    Write-Host "При блокировке ExecutionPolicy: powershell -NoProfile -ExecutionPolicy Bypass -File .\Check-EndpointAccess.ps1 ..." 
    Write-Host "Подробности: -ShowGuide или -ExportBundle."
}

function Export-BundleFiles {
    param([string]$Dir)
    if (-not (Test-Path -LiteralPath $Dir)) { New-Item -ItemType Directory -Path $Dir -Force | Out-Null }
    $items = @(
        @{ Name = 'README-Check-EndpointAccess.md'; Content = $script:EmbeddedReadme },
        @{ Name = 'ACCURACY-CHECKLIST.md';        Content = $script:EmbeddedChecklist },
        @{ Name = 'device-ports.template.csv';    Content = $script:EmbeddedPortsTemplate },
        @{ Name = 'device-ports.example.csv';     Content = $script:EmbeddedPortsExample },
        @{ Name = 'Run-CheckEndpointAccess.cmd';  Content = $script:EmbeddedCmd }
    )
    foreach ($it in $items) {
        $path = Join-Path $Dir $it.Name
        $it.Content | Out-File -FilePath $path -Encoding UTF8
        Write-Host "Экспортировано: $path"
    }
    # also copy self if running from a file path
    try {
        $self = $MyInvocation.PSCommandPath
        if (-not $self -and $PSCommandPath) { $self = $PSCommandPath }
        if ($self -and (Test-Path -LiteralPath $self)) {
            $dest = Join-Path $Dir 'Check-EndpointAccess.ps1'
            $srcFull = [IO.Path]::GetFullPath($self)
            $dstFull = [IO.Path]::GetFullPath($dest)
            if ($srcFull -ne $dstFull) { Copy-Item -LiteralPath $self -Destination $dest -Force; Write-Host "Экспортировано: $dest" }
        }
    } catch { }
    Write-Host "Готово. Для диагностики используйте Check-EndpointAccess.ps1 или Run-CheckEndpointAccess.cmd из каталога экспорта."
}

# Handle help/export modes before diagnostics
$didAction = $false
if ($ShowHelp) { Show-QuickHelp; $didAction = $true }
if ($ShowGuide) { Write-Output $script:EmbeddedReadme; $didAction = $true }
if ($ShowChecklist) { Write-Output $script:EmbeddedChecklist; $didAction = $true }
if ($ShowPortsTemplate) { Write-Output $script:EmbeddedPortsTemplate; $didAction = $true }
if ($ShowPortsExample) { Write-Output $script:EmbeddedPortsExample; $didAction = $true }
if ($ExportBundle) { Export-BundleFiles -Dir $ExportDir; $didAction = $true }
if ($didAction -and -not $Target) { return }
if (-not $Target) { Show-QuickHelp; Write-Host ""; Write-Host "Ошибка: для диагностики укажите -Target <FQDN|IP|URL|host:port>" -ForegroundColor Yellow; return }

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

function New-ReportDir {
    if (-not (Test-Path -LiteralPath $OutDir)) {
        New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
    }
}

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    $script:LogLines.Add($line) | Out-Null
    Write-Host $line
}

function Add-Section {
    param([string]$Title)
    $script:ReportLines.Add("") | Out-Null
    $script:ReportLines.Add(("=" * 78)) | Out-Null
    $script:ReportLines.Add($Title) | Out-Null
    $script:ReportLines.Add(("=" * 78)) | Out-Null
}

function Add-Line {
    param([string]$Text = "")
    $script:ReportLines.Add($Text) | Out-Null
}

function Parse-Target {
    param([string]$InputTarget)
    $result = [ordered]@{
        Original    = $InputTarget
        Host        = $InputTarget
        Url         = $null
        PortFromUrl = $null
        Scheme      = $null
    }
    $t = $InputTarget.Trim()
    if ($t -match '^[a-zA-Z][a-zA-Z0-9+\-.]*://') {
        try {
            $u = [Uri]$t
            $result.Url = $u.AbsoluteUri
            $result.Host = $u.Host
            $result.Scheme = $u.Scheme
            if (-not $u.IsDefaultPort) { $result.PortFromUrl = $u.Port }
            elseif ($u.Scheme -eq 'https') { $result.PortFromUrl = 443 }
            elseif ($u.Scheme -eq 'http') { $result.PortFromUrl = 80 }
        } catch { }
        return [pscustomobject]$result
    }
    # host:port (simple, not IPv6 bracket form)
    if ($t -match '^([^:\[\]]+):(\d{1,5})$') {
        $result.Host = $Matches[1]
        $result.PortFromUrl = [int]$Matches[2]
    }
    return [pscustomobject]$result
}

function New-PortSpec {
    param([string]$Proto, [int]$Port, [string]$Source = 'manual', [string]$Description = '', [string]$Direction = 'outbound')
    return [pscustomobject]@{
        Proto       = $Proto.ToUpperInvariant()
        Port        = $Port
        Source      = $Source
        Description = $Description
        Direction   = $Direction
    }
}

function Add-PortSpec {
    param($Map, $Spec)
    if ($null -eq $Spec -or $null -eq $Spec.Port) { return }
    $p = [int]$Spec.Port
    if ($p -lt 1 -or $p -gt 65535) { return }
    $proto = ($Spec.Proto | ForEach-Object { "$_".ToUpperInvariant() })
    if ($proto -ne 'TCP' -and $proto -ne 'UDP') { $proto = 'TCP' }
    $key = "$proto|$p"
    if (-not $Map.ContainsKey($key)) {
        $Map[$key] = [pscustomobject]@{
            Proto       = $proto
            Port        = $p
            Sources     = New-Object System.Collections.Generic.List[string]
            Description = $Spec.Description
            Direction   = $Spec.Direction
        }
        [void]$Map[$key].Sources.Add($Spec.Source)
    } else {
        if ($Spec.Source -and -not $Map[$key].Sources.Contains($Spec.Source)) { [void]$Map[$key].Sources.Add($Spec.Source) }
        if (-not $Map[$key].Description -and $Spec.Description) { $Map[$key].Description = $Spec.Description }
        if ($Map[$key].Direction -eq 'outbound' -and $Spec.Direction) { $Map[$key].Direction = $Spec.Direction }
    }
}

function Parse-PortsFile {
    param([string]$Path, $Map)
    if (-not $Path) { return }
    if (-not (Test-Path -LiteralPath $Path)) { Write-Log "Файл портов не найден: $Path" 'WARN'; return }
    try {
        $raw = Get-Content -LiteralPath $Path -ErrorAction Stop
    } catch { Write-Log "Не удалось прочитать файл портов '$Path': $($_.Exception.Message)" 'WARN'; return }
    $nonEmpty = @($raw | Where-Object { $_ -and $_.Trim() -and -not $_.Trim().StartsWith('#') })
    if ($nonEmpty.Count -eq 0) { return }
    $first = $nonEmpty[0]
    $isCsv = ($first -match '(?i)(^|,|\t|;)\s*proto\s*(,|\t|;)' -and $first -match '(?i)port')
    if ($isCsv) {
        try {
            $rows = Import-Csv -LiteralPath $Path -ErrorAction Stop
            foreach ($row in $rows) {
                $proto = if ($row.PSObject.Properties['Proto']) { "$($row.Proto)" } elseif ($row.PSObject.Properties['Protocol']) { "$($row.Protocol)" } else { 'TCP' }
                $portVal = if ($row.PSObject.Properties['Port']) { "$($row.Port)" } else { '' }
                $desc = if ($row.PSObject.Properties['Description']) { "$($row.Description)" } elseif ($row.PSObject.Properties['Comment']) { "$($row.Comment)" } else { '' }
                $dir = if ($row.PSObject.Properties['Direction']) { "$($row.Direction)" } else { 'outbound' }
                if ($portVal -match '(\d{1,5})') {
                    Add-PortSpec -Map $Map -Spec (New-PortSpec -Proto $proto -Port ([int]$Matches[1]) -Source "file:$([IO.Path]::GetFileName($Path))" -Description $desc -Direction $dir)
                }
            }
            return
        } catch { Write-Log "Не удалось разобрать CSV портов '$Path': $($_.Exception.Message). Пробую построчно." 'WARN' }
    }
    foreach ($line in $nonEmpty) {
        $l = $line.Trim()
        $proto = 'TCP'; $port = $null; $desc = ''
        if ($l -match '^(?i)(TCP|UDP)\s*[/\s,:-]\s*(\d{1,5})(?:\s+(.+))?$') {
            $proto = $Matches[1]; $port = [int]$Matches[2]; $desc = if ($Matches[3]) { $Matches[3].Trim() } else { '' }
        } elseif ($l -match '^(\d{1,5})\s*/\s*(?i)(TCP|UDP)(?:\s+(.+))?$') {
            $port = [int]$Matches[1]; $proto = $Matches[2]; $desc = if ($Matches[3]) { $Matches[3].Trim() } else { '' }
        } elseif ($l -match '^(\d{1,5})(?:\s+(.+))?$') {
            $port = [int]$Matches[1]; $desc = if ($Matches[2]) { $Matches[2].Trim() } else { '' }
            if ($desc -match '^(?i)udp\b') { $proto = 'UDP' }
        }
        if ($port) {
            Add-PortSpec -Map $Map -Spec (New-PortSpec -Proto $proto -Port $port -Source "file:$([IO.Path]::GetFileName($Path))" -Description $desc -Direction 'outbound')
        }
    }
}

function Get-RequestedPorts {
    $map = @{}
    $profilesDef = @{
        'Web'     = @(@{P=80;T='TCP'}, @{P=443;T='TCP'})
        'RDP'     = @(@{P=3389;T='TCP'}, @{P=3389;T='UDP'})
        'SMB'     = @(@{P=445;T='TCP'}, @{P=139;T='TCP'})
        'DNS'     = @(@{P=53;T='TCP'}, @{P=53;T='UDP'})
        'LDAP'    = @(@{P=389;T='TCP'}, @{P=636;T='TCP'}, @{P=3268;T='TCP'}, @{P=3269;T='TCP'}, @{P=389;T='UDP'})
        'SSH'     = @(@{P=22;T='TCP'})
        'WinRM'   = @(@{P=5985;T='TCP'}, @{P=5986;T='TCP'})
        'SQL'     = @(@{P=1433;T='TCP'}, @{P=1434;T='UDP'})
        'Mail'    = @(@{P=25;T='TCP'}, @{P=110;T='TCP'}, @{P=143;T='TCP'}, @{P=465;T='TCP'}, @{P=587;T='TCP'}, @{P=993;T='TCP'}, @{P=995;T='TCP'})
        'Printer' = @(@{P=9100;T='TCP'}, @{P=515;T='TCP'}, @{P=631;T='TCP'}, @{P=631;T='UDP'})
        'Camera'  = @(@{P=80;T='TCP'}, @{P=443;T='TCP'}, @{P=554;T='TCP'}, @{P=8000;T='TCP'}, @{P=8554;T='TCP'}, @{P=37777;T='TCP'}, @{P=37778;T='TCP'})
        'NTP'     = @(@{P=123;T='UDP'})
        'Time'    = @(@{P=123;T='UDP'})
        'MQTT'    = @(@{P=1883;T='TCP'}, @{P=8883;T='TCP'})
        'DB'      = @(@{P=1433;T='TCP'}, @{P=3306;T='TCP'}, @{P=5432;T='TCP'}, @{P=1521;T='TCP'}, @{P=27017;T='TCP'})
        'AD'      = @(@{P=53;T='TCP'}, @{P=53;T='UDP'}, @{P=88;T='TCP'}, @{P=88;T='UDP'}, @{P=135;T='TCP'}, @{P=389;T='TCP'}, @{P=389;T='UDP'}, @{P=445;T='TCP'}, @{P=464;T='TCP'}, @{P=464;T='UDP'}, @{P=636;T='TCP'}, @{P=3268;T='TCP'}, @{P=3269;T='TCP'})
        'SIP'     = @(@{P=5060;T='TCP'}, @{P=5060;T='UDP'}, @{P=5061;T='TCP'})
        'SNMP'    = @(@{P=161;T='UDP'}, @{P=162;T='UDP'})
    }
    foreach ($p in $Profiles) {
        $keyName = $p
        foreach ($k in $profilesDef.Keys) { if ($k -ieq $p) { $keyName = $k; break } }
        if ($profilesDef.ContainsKey($keyName)) {
            foreach ($x in $profilesDef[$keyName]) {
                Add-PortSpec -Map $map -Spec (New-PortSpec -Proto $x.T -Port $x.P -Source "profile:$keyName")
            }
        } else {
            Write-Log "Неизвестный профиль: $p" 'WARN'
        }
    }
    foreach ($x in $Ports) { Add-PortSpec -Map $map -Spec (New-PortSpec -Proto 'TCP' -Port $x -Source 'param:Ports') }
    foreach ($x in $UdpPorts) { Add-PortSpec -Map $map -Spec (New-PortSpec -Proto 'UDP' -Port $x -Source 'param:UdpPorts') }
    if ($script:ParsedTarget.PortFromUrl) { Add-PortSpec -Map $map -Spec (New-PortSpec -Proto 'TCP' -Port $script:ParsedTarget.PortFromUrl -Source 'target') }
    Parse-PortsFile -Path $PortsFile -Map $map
    return @($map.Values | Sort-Object Proto, Port)
}

function Resolve-TargetHost {
    param([string]$HostName)
    $ips = @()
    $errors = @()
    try {
        if (Get-Command Resolve-DnsName -ErrorAction SilentlyContinue) {
            $a = Resolve-DnsName -Name $HostName -ErrorAction Stop | Where-Object { $_.Type -in 'A','AAAA' -and ($_.IPAddress -or $_.IP4Address -or $_.IP6Address) }
            foreach ($r in $a) {
                if ($r.IPAddress) { $ips += $r.IPAddress }
                elseif ($r.IP4Address) { $ips += $r.IP4Address }
                elseif ($r.IP6Address) { $ips += $r.IP6Address }
            }
        } else {
            $he = [System.Net.Dns]::GetHostAddresses($HostName)
            foreach ($i in $he) { $ips += $i.IPAddressToString }
        }
    } catch { $errors += $_.Exception.Message }
    # if input already IP
    try { [void][System.Net.IPAddress]::Parse($HostName); if (-not $ips) { $ips += $HostName } } catch { }
    return [pscustomobject]@{ IPs = @($ips | Sort-Object -Unique); Errors = $errors }
}

function Get-LocalNetworkInfo {
    Add-Section "1. Локальная конфигурация хоста"
    Add-Line "Компьютер: $env:COMPUTERNAME"
    Add-Line "Пользователь: $env:USERNAME"
    Add-Line "Дата: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
    Add-Line "ОС: $([System.Environment]::OSVersion.VersionString)"
    try {
        $cfg = Get-NetIPConfiguration -ErrorAction SilentlyContinue | Where-Object { $_.NetAdapter.Status -eq 'Up' }
        foreach ($c in $cfg) {
            Add-Line ("Интерфейс: {0} | IPv4: {1} | Шлюз: {2} | DNS: {3}" -f $c.InterfaceAlias, ($c.IPv4Address.IPv4Address -join ','), ($c.IPv4DefaultGateway.NextHop -join ','), ($c.DnsServer.ServerAddresses -join ','))
        }
    } catch {
        try { Add-Line (ipconfig /all | Out-String).TrimEnd() } catch { Add-Line "Не удалось получить сетевую конфигурацию: $($_.Exception.Message)" }
    }
    try {
        $proxy = Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
        if ($proxy) {
            Add-Line "Прокси включён: $($proxy.ProxyEnable) | ProxyServer: $($proxy.ProxyServer) | AutoConfigURL: $($proxy.AutoConfigURL)"
        }
    } catch { }
}

function Test-Icmp {
    param([string]$HostName)
    Add-Section "3. ICMP (ping)"
    try {
        $r = Test-Connection -ComputerName $HostName -Count 4 -ErrorAction Stop
        $avg = ($r | Measure-Object -Property ResponseTime -Average).Average
        Add-Line ("Ping: УСПЕХ, ответов {0}/4, средняя задержка {1} мс" -f $r.Count, [math]::Round($avg,2))
        $script:Findings['icmp'] = 'ok'
    } catch {
        Add-Line "Ping: НЕТ ОТВЕТА/ОШИБКА ($($_.Exception.Message))"
        Add-Line "Примечание: ICMP может быть запрещён политикой, при этом TCP/UDP-доступ возможен."
        $script:Findings['icmp'] = 'fail'
    }
}

function Get-TraceRoute {
    param([string]$HostName)
    if ($NoTrace) { return }
    Add-Section "4. Маршрут / трассировка"
    $done = $false
    try {
        if (Get-Command Test-NetConnection -ErrorAction SilentlyContinue) {
            $r = Test-NetConnection -ComputerName $HostName -TraceRoute -InformationLevel Detailed -WarningAction SilentlyContinue -ErrorAction Stop
            if ($r.TraceRoute) {
                $i = 0
                foreach ($hop in $r.TraceRoute) { $i++; Add-Line ("  {0,2}. {1}" -f $i, $hop) }
                $done = $true
                $script:Findings['trace_last'] = ($r.TraceRoute | Select-Object -Last 1)
                $script:Findings['trace_hops'] = @($r.TraceRoute)
            }
        }
    } catch { Add-Line "Test-NetConnection -TraceRoute: $($_.Exception.Message)" }
    if (-not $done) {
        try {
            Add-Line "Результат tracert (первые 30 переходов):"
            $out = & tracert -d -h 30 $HostName 2>&1
            foreach ($l in $out) { Add-Line ("  " + $l) }
            $script:Findings['trace_raw'] = ($out -join "`n")
            $done = $true
        } catch { Add-Line "tracert недоступен: $($_.Exception.Message)" }
    }
    if (-not $done) { Add-Line "Трассировка не выполнена." }
}

function Test-TcpPortOne {
    param([string]$HostName, [int]$Port, [int]$TmoMs)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne($TmoMs, $false)
        if (-not $ok) {
            try { $client.Close() } catch { }
            $sw.Stop()
            return [pscustomobject]@{ Host=$HostName; Port=$Port; Proto='TCP'; Status='TIMEOUT/FILTERED'; Detail='Нет ответа за таймаут (возможна фильтрация/drop)'; Ms=$sw.ElapsedMilliseconds }
        }
        $client.EndConnect($iar)
        $sw.Stop()
        try { $client.Close() } catch { }
        return [pscustomobject]@{ Host=$HostName; Port=$Port; Proto='TCP'; Status='OPEN'; Detail='Соединение установлено'; Ms=$sw.ElapsedMilliseconds }
    } catch [System.Net.Sockets.SocketException] {
        $sw.Stop()
        $code = $_.Exception.SocketErrorCode
        $detail = $_.Exception.Message
        $status = 'ERROR'
        if ($code -eq 'ConnectionRefused') { $status = 'CLOSED/REFUSED'; $detail = 'Порт достижим, но соединение отклонено (RST) — скорее сервис/хост, не сетевой фильтр' }
        elseif ($code -eq 'HostUnreachable' -or $code -eq 'NetworkUnreachable') { $status = 'UNREACHABLE'; $detail = 'Сеть/хост недостижимы (маршрутизация/ACL)' }
        elseif ($code -eq 'TimedOut') { $status = 'TIMEOUT/FILTERED'; $detail = 'Таймаут (возможна фильтрация/drop)' }
        else { $status = "ERROR($code)"; $detail = $_.Exception.Message }
        try { $client.Close() } catch { }
        return [pscustomobject]@{ Host=$HostName; Port=$Port; Proto='TCP'; Status=$status; Detail=$detail; Ms=$sw.ElapsedMilliseconds }
    } catch {
        $sw.Stop()
        try { $client.Close() } catch { }
        return [pscustomobject]@{ Host=$HostName; Port=$Port; Proto='TCP'; Status='ERROR'; Detail=$_.Exception.Message; Ms=$sw.ElapsedMilliseconds }
    }
}

function Test-Ports {
    param([string[]]$TargetIPs, [object[]]$PortSpecs)
    Add-Section "5. Проверка портов (по спецификации)"
    if (-not $PortSpecs -or $PortSpecs.Count -eq 0) {
        Add-Line "Порты не заданы. Укажите -Ports/-UdpPorts, -Profiles и/или -PortsFile, либо запустите с -MonitorSeconds для наблюдения фактических попыток."
        return @()
    }
    Add-Line "Спецификация (для точности под устройство/сервис):"
    foreach ($s in $PortSpecs) {
        $src = ($s.Sources -join ',')
        $extra = @()
        if ($s.Direction) { $extra += "dir=$($s.Direction)" }
        if ($s.Description) { $extra += "desc=$($s.Description)" }
        if ($src) { $extra += "source=$src" }
        Add-Line ("  - {0}/{1} ({2})" -f $s.Proto, $s.Port, ($extra -join '; '))
    }
    $results = @()
    foreach ($ip in $TargetIPs) {
        foreach ($s in $PortSpecs) {
            if ($s.Proto -eq 'TCP') {
                $r = Test-TcpPortOne -HostName $ip -Port ([int]$s.Port) -TmoMs $TimeoutMs
            } else {
                $r = [pscustomobject]@{ Host=$ip; Port=[int]$s.Port; Proto='UDP'; Status='SKIPPED/UDP'; Detail='Активная проверка UDP с клиента ненадёжна; подтвердите обмен через -MonitorSeconds и/или захват (pktmon/netsh trace).'; Ms=0 }
            }
            # attach spec metadata
            $r | Add-Member -NotePropertyName 'Direction' -NotePropertyValue $s.Direction -Force
            $r | Add-Member -NotePropertyName 'Description' -NotePropertyValue $s.Description -Force
            $r | Add-Member -NotePropertyName 'Sources' -NotePropertyValue @($s.Sources) -Force
            $results += $r
            Add-Line ("[{0}] {1}:{2}/{3} -> {4} ({5} мс) — {6}" -f $ip, $ip, $s.Port, $s.Proto, $r.Status, $r.Ms, $r.Detail)
        }
    }
    return $results
}

function Test-HttpProbe {
    param([string]$Url)
    Add-Section "6. HTTP/HTTPS проба"
    if (-not $Url) { Add-Line "URL не задан (укажите http/https в -Target для этой проверки)."; return }
    try {
        $resp = Invoke-WebRequest -Uri $Url -Method Get -MaximumRedirection 5 -TimeoutSec ([math]::Ceiling($TimeoutMs/1000.0)) -UseBasicParsing -ErrorAction Stop
        Add-Line "HTTP(S): УСПЕХ, код $($resp.StatusCode) $($resp.StatusDescription)"
        $script:Findings['http'] = "ok:$($resp.StatusCode)"
    } catch {
        $msg = $_.Exception.Message
        Add-Line "HTTP(S): ОШИБКА — $msg"
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            try { Add-Line "  Код ответа: $([int]$_.Exception.Response.StatusCode)" } catch { }
        }
        $script:Findings['http'] = "fail:$msg"
    }
}

function Get-FirewallHints {
    Add-Section "7. Локальный firewall / фильтрация (best effort)"
    try {
        $profiles = Get-NetFirewallProfile -ErrorAction Stop
        foreach ($p in $profiles) { Add-Line ("Профиль {0}: Enabled={1}, DefaultOutbound={2}, DefaultInbound={3}" -f $p.Name, $p.Enabled, $p.DefaultOutboundAction, $p.DefaultInboundAction) }
    } catch {
        Add-Line "Не удалось прочитать профили firewall (возможны ограниченные права): $($_.Exception.Message)"
    }
    Add-Line "Примечание: исходящий трафик обычно разрешён по умолчанию; точные блокирующие правила требуют анализа администратором (Get-NetFirewallRule/журналы/СЗИ)."
}

function Watch-Connections {
    param([string[]]$TargetIPs, [int]$Seconds, [string]$ProcName)
    Add-Section "8. Наблюдение попыток подключений (фактические потоки)"
    if ($Seconds -le 0) { Add-Line "Мониторинг не запрошен (-MonitorSeconds 0). Для точного профиля трафика устройства запустите мониторинг во время его работы."; return @() }
    $ownerIds = $null
    if ($ProcName) {
        try { $ownerIds = @(Get-Process -Name $ProcName -ErrorAction Stop | Select-Object -ExpandProperty Id) } catch { Add-Line "Процесс '$ProcName' не найден: $($_.Exception.Message)" }
    }
    Add-Line "Наблюдение $Seconds сек. Целевые IP: $($TargetIPs -join ', ')"
    if ($ownerIds) { Add-Line "Фильтр PID процесса '$ProcName': $($ownerIds -join ', ')" }
    Add-Line "Запустите/активируйте проверяемое устройство или приложение сейчас, чтобы зафиксировать нужные порты и протоколы."
    $seen = @{}
    $end = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $end) {
        try {
            $tcp = Get-NetTCPConnection -ErrorAction SilentlyContinue | Where-Object { $TargetIPs -contains $_.RemoteAddress }
            if ($ownerIds) { $tcp = $tcp | Where-Object { $ownerIds -contains $_.OwningProcess } }
            foreach ($c in $tcp) {
                $key = "TCP|$($c.RemoteAddress)|$($c.RemotePort)|$($c.State)|$($c.OwningProcess)"
                $pname = ''
                try { $pname = (Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue).ProcessName } catch { }
                if (-not $seen.ContainsKey($key)) {
                    $seen[$key] = [pscustomobject]@{ FirstSeen=(Get-Date); LastSeen=(Get-Date); Count=1; Proto='TCP'; RemoteAddress=$c.RemoteAddress; RemotePort=$c.RemotePort; State=$c.State; LocalPort=$c.LocalPort; PID=$c.OwningProcess; Process=$pname }
                } else {
                    $seen[$key].LastSeen = (Get-Date)
                    $seen[$key].Count = [int]$seen[$key].Count + 1
                    if (-not $seen[$key].Process -and $pname) { $seen[$key].Process = $pname }
                }
            }
            $udp = Get-NetUDPEndpoint -ErrorAction SilentlyContinue | Where-Object { $_.RemoteAddress -and ($TargetIPs -contains $_.RemoteAddress) }
            if ($ownerIds) { $udp = $udp | Where-Object { $ownerIds -contains $_.OwningProcess } }
            foreach ($u in $udp) {
                $key = "UDP|$($u.RemoteAddress)|$($u.RemotePort)|*|$($u.OwningProcess)"
                $pname = ''
                try { $pname = (Get-Process -Id $u.OwningProcess -ErrorAction SilentlyContinue).ProcessName } catch { }
                if (-not $seen.ContainsKey($key)) {
                    $seen[$key] = [pscustomobject]@{ FirstSeen=(Get-Date); LastSeen=(Get-Date); Count=1; Proto='UDP'; RemoteAddress=$u.RemoteAddress; RemotePort=$u.RemotePort; State='endpoint'; LocalPort=$u.LocalPort; PID=$u.OwningProcess; Process=$pname }
                } else {
                    $seen[$key].LastSeen = (Get-Date)
                    $seen[$key].Count = [int]$seen[$key].Count + 1
                    if (-not $seen[$key].Process -and $pname) { $seen[$key].Process = $pname }
                }
            }
        } catch { }
        Start-Sleep -Milliseconds 1000
    }
    $rows = @($seen.Values | Sort-Object Proto, RemotePort, State, PID)
    if ($rows.Count -eq 0) {
        Add-Line "За период наблюдения соединений к целевому адресу не зафиксировано."
        Add-Line "Проверьте, что устройство/приложение реально обращалось к адресу, увеличьте -MonitorSeconds, укажите -ProcessName или проверьте, совпадают ли IP назначения."
    } else {
        foreach ($r in $rows) {
            Add-Line ("{0} {1}:{2} state={3} local={4} pid={5} proc={6} count={7} first={8} last={9}" -f $r.Proto, $r.RemoteAddress, $r.RemotePort, $r.State, $r.LocalPort, $r.PID, $r.Process, $r.Count, $r.FirstSeen.ToString('HH:mm:ss'), $r.LastSeen.ToString('HH:mm:ss'))
        }
        Add-Line "Подсказка: TCP SynSent — вероятная фильтрация/drop; Established — соединение установлено; UDP endpoint — факт обмена/привязки (доставка не гарантируется без ответа)."
    }
    return $rows
}

function Build-NetworkRequest {
    param([string[]]$TargetIPs, [object[]]$PortResults, [object[]]$Observed, [object[]]$RequestedSpecs)
    Add-Section "9. Черновик запроса для сетевиков / СБ"
    $flows = New-Object System.Collections.Generic.List[string]
    foreach ($s in $RequestedSpecs) {
        $desc = if ($s.Description) { " — $($s.Description)" } else { '' }
        $dir = if ($s.Direction) { $s.Direction } else { 'outbound' }
        $srcs = if ($s.Sources) { ($s.Sources -join ',') } else { '' }
        $flows.Add("$($s.Proto)/$($s.Port) ($dir)$desc [spec:$srcs]") | Out-Null
    }
    foreach ($o in $Observed) {
        $state = if ($o.State) { $o.State } else { 'endpoint' }
        $flows.Add("$($o.Proto)/$($o.RemotePort) (наблюдалось, state=$state, proc=$($o.Process))") | Out-Null
    }
    $flows = @($flows | Sort-Object -Unique)

    $blocked = @()
    foreach ($r in $PortResults) { if ($r.Status -like 'TIMEOUT*' -or $r.Status -eq 'UNREACHABLE' -or $r.Status -like 'ERROR*') { $blocked += $r } }
    foreach ($o in $Observed) { if ($o.State -eq 'SynSent') { $blocked += $o } }

    $dev = if ($DeviceName) { $DeviceName } else { '<модель, инв. номер, ОС, назначение>' }
    $pur = if ($Purpose) { $Purpose } else { '<заполнить: зачем нужен доступ>' }

    $req = New-Object System.Collections.Generic.List[string]
    $req.Add("Тема: Запрос на согласование/разблокировку сетевого доступа для устройства/сервиса") | Out-Null
    $req.Add("") | Out-Null
    $req.Add("1. Инициатор/подразделение/контакт: <заполнить>") | Out-Null
    $req.Add("2. Устройство/система: $dev") | Out-Null
    $req.Add("3. Источник (IP/сегмент/VLAN/зона): <заполнить, см. отчёт п.1>") | Out-Null
    $req.Add("4. Назначение (FQDN/IP/URL): $($script:ParsedTarget.Original)") | Out-Null
    $req.Add("5. Разрешённые/наблюдаемые IP назначения: $($TargetIPs -join ', ')") | Out-Null
    $req.Add("6. Назначение доступа (обоснование): $pur") | Out-Null
    $req.Add("7. Требуемые потоки (уточнить по данным производителя и фактам мониторинга):") | Out-Null
    if ($flows.Count -gt 0) {
        foreach ($f in $flows) { $req.Add("   - <SRC_IP/сегмент> -> <DST_IP/FQDN> : $f") | Out-Null }
    } else {
        $req.Add("   - <не определено автоматически: приложите спецификацию портов производителя (-PortsFile) и/или выполните -MonitorSeconds во время работы устройства>") | Out-Null
    }
    $req.Add("8. Наблюдаемые проблемы (факты диагностики):") | Out-Null
    if ($blocked.Count -gt 0) {
        $req.Add("   - Выявлены таймауты/недостижимость/SynSent (вероятная сетевая фильтрация/маршрутизация). См. сводку и трассировку в summary.txt.") | Out-Null
    } else {
        $req.Add("   - Явных таймаутов/блокировок по проверенным точкам не выявлено; для полноты требуется мониторинг реальной работы устройства и сверка со спецификацией производителя.") | Out-Null
    }
    $req.Add("9. Время проверки и хост-источник: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'), $env:COMPUTERNAME") | Out-Null
    $req.Add("10. Вложения: summary.txt, details.json, port-tests.csv, observed.csv, request-for-network.txt") | Out-Null
    $req.Add("") | Out-Null
    $req.Add("Примечание: выводы о блокировке на сетевом оборудовании вероятностны (по признакам с клиента: timeout/SynSent/трассировка). UDP-требования требуют подтверждения мониторингом/захватом.") | Out-Null

    foreach ($l in $req) { Add-Line $l }
    return ($req -join "`r`n")
}

# --- main ---
$script:ReportLines = New-Object System.Collections.Generic.List[string]
$script:LogLines = New-Object System.Collections.Generic.List[string]
$script:Findings = @{}
New-ReportDir
Write-Log "Старт диагностики для '$Target'"

$script:ParsedTarget = Parse-Target -InputTarget $Target
Get-LocalNetworkInfo

Add-Section "2. DNS / разрешение имени"
Add-Line "Цель: $($script:ParsedTarget.Original)"
Add-Line "Хост: $($script:ParsedTarget.Host)"
if ($script:ParsedTarget.Url) { Add-Line "URL: $($script:ParsedTarget.Url)" }
if ($DeviceName) { Add-Line "Устройство/сервис: $DeviceName" }
if ($Purpose) { Add-Line "Назначение: $Purpose" }
$res = Resolve-TargetHost -HostName $script:ParsedTarget.Host
$targetIPs = @($res.IPs)
if ($targetIPs.Count -gt 0) {
    Add-Line "Разрешённые адреса: $($targetIPs -join ', ')"
    $script:Findings['dns'] = 'ok'
} else {
    Add-Line "Не удалось разрешить имя."
    foreach ($e in $res.Errors) { Add-Line "  Ошибка: $e" }
    $script:Findings['dns'] = 'fail'
}

$probeHost = $script:ParsedTarget.Host
if ($targetIPs.Count -gt 0) { $probeHost = $targetIPs[0] }

if ($targetIPs.Count -gt 0) { Test-Icmp -HostName $probeHost } else { Add-Section "3. ICMP (ping)"; Add-Line "Пропущено: нет IP." }
if ($targetIPs.Count -gt 0) { Get-TraceRoute -HostName $probeHost } else { if (-not $NoTrace) { Add-Section "4. Маршрут / трассировка"; Add-Line "Пропущено: нет IP." } }

$requestedSpecs = @(Get-RequestedPorts)
$portResults = @()
if ($targetIPs.Count -gt 0) { $portResults = @(Test-Ports -TargetIPs $targetIPs -PortSpecs $requestedSpecs) } else { Add-Section "5. Проверка портов (по спецификации)"; Add-Line "Пропущено: нет IP." }

if ($script:ParsedTarget.Url) { Test-HttpProbe -Url $script:ParsedTarget.Url } else { Add-Section "6. HTTP/HTTPS проба"; Add-Line "URL не задан." }

Get-FirewallHints

$observed = @()
if ($targetIPs.Count -gt 0) { $observed = @(Watch-Connections -TargetIPs $targetIPs -Seconds $MonitorSeconds -ProcName $ProcessName) } else { Add-Section "8. Наблюдение попыток подключений (фактические потоки)"; Add-Line "Пропущено: нет IP." }

$requestText = Build-NetworkRequest -TargetIPs $targetIPs -PortResults $portResults -Observed $observed -RequestedSpecs $requestedSpecs

# Write outputs
$summaryPath = Join-Path $OutDir 'summary.txt'
$detailsPath = Join-Path $OutDir 'details.json'
$requestPath = Join-Path $OutDir 'request-for-network.txt'
$portCsvPath = Join-Path $OutDir 'port-tests.csv'
$obsCsvPath  = Join-Path $OutDir 'observed.csv'
$logPath     = Join-Path $OutDir 'run.log'
$specCsvPath = Join-Path $OutDir 'requested-ports.csv'

try { $script:ReportLines | Out-File -FilePath $summaryPath -Encoding UTF8 } catch { Write-Log "Не удалось записать summary: $($_.Exception.Message)" 'WARN' }
try { $requestText | Out-File -FilePath $requestPath -Encoding UTF8 } catch { Write-Log "Не удалось записать request: $($_.Exception.Message)" 'WARN' }
try { $script:LogLines | Out-File -FilePath $logPath -Encoding UTF8 } catch { }

$details = [ordered]@{
    target         = $script:ParsedTarget
    deviceName     = $DeviceName
    purpose        = $Purpose
    resolvedIPs    = $targetIPs
    requestedPorts = $requestedSpecs
    portResults    = $portResults
    observed       = $observed
    findings       = $script:Findings
    host           = $env:COMPUTERNAME
    timestamp      = (Get-Date).ToString('o')
}
try { $details | ConvertTo-Json -Depth 8 | Out-File -FilePath $detailsPath -Encoding UTF8 } catch { Write-Log "Не удалось записать details.json: $($_.Exception.Message)" 'WARN' }
try { if ($requestedSpecs.Count -gt 0) { $requestedSpecs | Select-Object Proto,Port,Direction,Description,@{N='Sources';E={($_.Sources -join ',')}} | Export-Csv -Path $specCsvPath -NoTypeInformation -Encoding UTF8 } } catch { }
try { if ($portResults.Count -gt 0) { $portResults | Select-Object Host,Proto,Port,Status,Ms,Direction,Description,Detail,@{N='Sources';E={($_.Sources -join ',')}} | Export-Csv -Path $portCsvPath -NoTypeInformation -Encoding UTF8 } } catch { }
try { if ($observed.Count -gt 0) { $observed | Export-Csv -Path $obsCsvPath -NoTypeInformation -Encoding UTF8 } } catch { }

Write-Log "Готово. Отчёт: $OutDir"
Write-Host ""
Write-Host "Файлы:" -ForegroundColor Cyan
Write-Host " - $summaryPath"
Write-Host " - $requestPath"
Write-Host " - $detailsPath"
if (Test-Path $specCsvPath) { Write-Host " - $specCsvPath" }
if (Test-Path $portCsvPath) { Write-Host " - $portCsvPath" }
if (Test-Path $obsCsvPath)  { Write-Host " - $obsCsvPath" }

# Console hint
$bad = @($portResults | Where-Object { $_.Status -like 'TIMEOUT*' -or $_.Status -eq 'UNREACHABLE' })
$syn = @($observed | Where-Object { $_.State -eq 'SynSent' })
if ($bad.Count -gt 0 -or $syn.Count -gt 0) {
    Write-Host ""
    Write-Host "Обнаружены признаки сетевой фильтрации/недостижимости. Используйте request-for-network.txt и CSV/JSON как основу заявки." -ForegroundColor Yellow
} elseif ($MonitorSeconds -le 0) {
    Write-Host ""
    Write-Host "Для точного профиля конкретного устройства/сервиса запустите с -PortsFile (спецификация производителя) и -MonitorSeconds во время реальной работы." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Мониторинг выполнен. Сверьте observed.csv/requested-ports.csv со спецификацией производителя и приложите отчёт к заявке." -ForegroundColor Green
}
