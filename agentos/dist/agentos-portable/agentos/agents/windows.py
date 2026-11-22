"""Администрирование Windows: cmd, PowerShell, службы, процессы, диски.

Правила безопасности:
  * по умолчанию dry-run — печатается точная команда, ничего не выполняется;
  * cmd — только фиксированный allowlist, аргументы без метасимволов;
  * PowerShell — allowlist командлетов Get-*/Test-*, запрещены конвейеры,
    точки с запятой, Invoke-Expression, Start-Process, Remove-*, Set-*;
  * изменяющие действия (старт/стоп службы, kill процесса) требуют --live
    и явного подтверждения `подтверждаю` / `confirm=да`;
  * вне Windows — честный отказ, без имитации.
"""
from __future__ import annotations

import os
import re

from ..core import REGISTRY, Context, agent
from ..tools import ToolError, is_windows, run_windows
from ..utils import parse_params, table

PS = ("powershell.exe", "-NoProfile", "-NonInteractive", "-Command")

# cmd-команды: фиксированные argv, без пользовательских аргументов
CMD = {
    "ver": ["ver"],
    "whoami": ["whoami"],
    "ipconfig": ["ipconfig", "/all"],
    "tasklist": ["tasklist"],
    "netstat": ["netstat", "-ano"],
    "route": ["route", "print"],
    "systeminfo": ["systeminfo"],
    "hostname": ["hostname"],
    "getmac": ["getmac", "/v"],
    "driverquery": ["driverquery"],
    "chcp": ["chcp"],
}

CMD_ALIASES = (
    ("ipconfig", "ipconfig"), ("netstat", "netstat"), ("tasklist", "tasklist"),
    ("systeminfo", "systeminfo"), ("driverquery", "driverquery"),
    ("whoami", "whoami"), ("getmac", "getmac"), ("hostname", "hostname"),
    ("маршрут", "route"), ("route", "route"),
    ("версия", "ver"), ("version", "ver"), ("кто я", "whoami"),
    ("процесс", "tasklist"), ("порт", "netstat"), ("соединен", "netstat"),
    ("система", "systeminfo"), ("имя пк", "hostname"),
    ("mac", "getmac"), ("драйвер", "driverquery"),
)

# PowerShell: только чтение
PS_ALLOW = {
    "get-service", "get-process", "get-volume", "get-psdrive", "get-disk",
    "get-partition", "get-ciminstance", "get-computerinfo", "get-host",
    "get-date", "get-hotfix", "get-winevent", "get-eventlog", "get-localuser",
    "get-localgroup", "get-scheduledtask", "get-netipconfiguration",
    "get-nettcpconnection", "get-netfirewallrule", "get-netadapter",
    "get-command", "get-itemproperty", "get-wmiobject", "test-connection",
    "resolve-dnsname", "get-childitem",
}

PS_BAN = (
    ";", "|", "&", ">", "<", "`", "$(", "${", "\n", "\r",
    "invoke-expression", "iex", "start-process", "stop-process", "remove-",
    "set-", "new-", "out-file", "set-content", "add-content", "clear-content",
    "invoke-webrequest", "invoke-restmethod", "downloadstring", "format-volume",
    "clear-disk", "initialize-disk", "shutdown", "restart-computer",
    "stop-computer", "reg add", "reg delete", "sc delete", "net user",
    "netsh", "bcdedit", "diskpart", "takeown", "icacls", "schtasks /create",
    "schtasks /delete", "enable-psremoting", "set-executionpolicy",
)

SAFE_NAME = re.compile(r"^[A-Za-z0-9 ._\-]+$")
SAFE_ARG = re.compile(r"^[A-Za-z0-9 _.,:\-/*\\'\"]+$")


# ---------------------------------------------------------------- помощники
def _clip(text: str, limit: int = 6000) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text or "(пусто)"
    return text[:limit].rstrip() + "\n… (вывод обрезан)"


def _fmt(res: dict) -> str:
    body = res.get("out") or res.get("err") or ""
    if not res.get("ok"):
        body = f"код {res.get('code')}: {res.get('err') or body}"
    return _clip(body)


def _ps(ctx: Context, script: str, *, timeout: int = 60) -> str:
    if ctx.dry_run:
        return f"dry-run: {_ps_line(script)}"
    full = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
            "$OutputEncoding=[Text.Encoding]::UTF8; " + script)
    return _fmt(run_windows([*PS, full], timeout=timeout))


def _ps_line(script: str) -> str:
    return f'powershell -NoProfile -NonInteractive -Command "{script}"'


def _cmd(ctx: Context, argv: list[str], *, timeout: int = 60) -> str:
    line = " ".join(argv)
    if ctx.dry_run:
        return f"dry-run: cmd /d /c {line}"
    return _fmt(run_windows(["cmd.exe", "/d", "/c", line], timeout=timeout))


def _need_confirm(params: dict, text: str) -> bool:
    val = (params.get("confirm") or params.get("подтверждение") or "").lower()
    return val in ("да", "yes", "1", "true") or "подтверждаю" in text.lower()


def _validate_ps(cmdline: str) -> str:
    low = cmdline.lower().strip()
    if not low:
        raise ToolError("пустая команда PowerShell")
    for bad in PS_BAN:
        if bad in low:
            raise ToolError(f"в PowerShell-команде запрещено {bad!r}")
    first = low.split()[0]
    if first not in PS_ALLOW:
        raise ToolError(
            f"командлет {first!r} не разрешён (только чтение: "
            "Get-*, Test-*, Resolve-DnsName)")
    if not SAFE_ARG.match(cmdline):
        raise ToolError("в аргументах есть недопустимые символы")
    return cmdline.strip()


def _pick(text: str, default: str) -> str:
    low = (text or "").lower()
    for word, key in CMD_ALIASES:
        if word in low:
            return key
    return default


# ---------------------------------------------------------------- агенты
@agent("win.info", "Windows: система", "windows",
       "Версия Windows, сборка, процессор, память, время работы (systeminfo)",
       keywords=("версия windows", "виндовс система", "systeminfo",
                 "какая windows", "сборка windows", "информация о системе windows"),
       examples=("",), needs=("windows",), tags=("slow",))
def info(ctx: Context, text: str):
    return _cmd(ctx, ["systeminfo"], timeout=120)


@agent("win.cmd", "Windows: cmd", "windows",
       "Разрешённые команды cmd.exe: ver, whoami, ipconfig, tasklist, netstat, "
       "route, systeminfo, hostname, getmac, driverquery",
       keywords=("cmd", "командная строка", "выполни команду cmd", "windows cmd",
                 "консоль windows", "команда cmd"),
       examples=("ipconfig",), needs=("windows",))
def cmd(ctx: Context, text: str):
    key = _pick(text, "")
    if not key:
        rows = [[k, " ".join(v)] for k, v in sorted(CMD.items())]
        return ("разрешённые команды cmd (аргументы не принимаются):\n"
                + table(rows, ["ключ", "команда"]))
    return _cmd(ctx, CMD[key], timeout=90)


@agent("win.ps", "Windows: PowerShell", "windows",
       "PowerShell только на чтение: Get-Service, Get-Process, Get-Volume, "
       "Get-WinEvent, Get-NetTCPConnection и другие Get-*/Test-*",
       keywords=("powershell", "powershell команда", "командлет", "ps команда",
                 "выполни powershell", "windows powershell"),
       examples=("Get-Service",), needs=("windows",))
def ps(ctx: Context, text: str):
    script = (text or "").strip()
    if not script:
        rows = [[c, ""] for c in sorted(PS_ALLOW)]
        return ("разрешённые командлеты (только чтение):\n"
                + table(rows, ["командлет", ""]))
    return _ps(ctx, _validate_ps(script), timeout=90)


@agent("win.net", "Windows: сеть", "windows",
       "Сеть Windows: ipconfig /all, netstat -ano, route print, кэш DNS",
       keywords=("сеть windows", "netstat windows", "ipconfig windows",
                 "windows ipconfig", "маршруты windows", "dns windows"),
       examples=("ipconfig",), needs=("windows",))
def net(ctx: Context, text: str):
    low = (text or "").lower()
    if "netstat" in low or "порт" in low or "соединен" in low:
        return _cmd(ctx, ["netstat", "-ano"])
    if "маршрут" in low or "route" in low:
        return _cmd(ctx, ["route", "print"])
    if "dns" in low or "днс" in low:
        return _cmd(ctx, ["ipconfig", "/displaydns"])
    return _cmd(ctx, ["ipconfig", "/all"])


@agent("win.disk", "Windows: диски", "windows",
       "Тома и свободное место: Get-Volume, размер и остаток в ГБ",
       keywords=("диски windows", "свободное место windows", "get-volume",
                 "тома windows", "место на диске windows"),
       examples=("",), needs=("windows",), tags=("slow",))
def disk(ctx: Context, text: str):
    script = ("Get-Volume | Where-Object DriveLetter | "
              "Select-Object DriveLetter,FileSystemLabel,FileSystem,HealthStatus,"
              "@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},"
              "@{n='FreeGB';e={[math]::Round($_.SizeRemaining/1GB,1)}} | "
              "Format-Table -AutoSize")
    return _ps(ctx, script, timeout=60)


@agent("win.services", "Windows: службы", "windows",
       "Службы Windows: список/статус, старт, стоп, перезапуск "
       "(изменения — только с подтверждением)",
       keywords=("службы windows", "служба windows", "service windows",
                 "запусти службу", "останови службу", "статус службы"),
       examples=("",), needs=("windows",))
def services(ctx: Context, text: str):
    params, rest = parse_params(text or "")
    low = (text or "").lower()
    action = (params.get("action") or params.get("действие") or "").strip().lower()
    if not action:
        if "перезапусти" in low:
            action = "restart"
        elif "останови" in low or "stop" in low:
            action = "stop"
        elif "запусти" in low or "start" in low:
            action = "start"
        else:
            action = "list"
    name = (params.get("name") or params.get("имя") or "").strip()
    if not name and action != "list":
        words = [w for w in rest.split() if re.fullmatch(r"[A-Za-z][A-Za-z0-9._\-]*", w)]
        words = [w for w in words if w.lower() not in
                 ("windows", "start", "stop", "restart", "status", "service")]
        if words:
            name = words[0]

    if action == "list":
        return _ps(ctx, "Get-Service | Sort-Object Status,DisplayName | "
                        "Select-Object Status,Name,DisplayName | Format-Table -AutoSize")

    if not name or not SAFE_NAME.match(name):
        raise ToolError("укажите имя службы: name=Spooler")
    if action not in ("start", "stop", "restart", "status"):
        raise ToolError("action: list | status | start | stop | restart")
    if action == "status":
        return _ps(ctx, f"Get-Service -Name '{name}' | "
                        "Format-Table Status,Name,DisplayName -AutoSize")
    if not _need_confirm(params, text or ""):
        raise ToolError(f"{action} службы {name}: нужно подтверждение "
                        "(добавьте «подтверждаю» или confirm=да)")
    verb = {"start": "Start-Service", "stop": "Stop-Service",
            "restart": "Restart-Service"}[action]
    return _ps(ctx, f"{verb} -Name '{name}' -ErrorAction Stop; "
                    f"Get-Service -Name '{name}' | Format-Table Status,Name -AutoSize")


@agent("win.process", "Windows: процессы", "windows",
       "Процессы: топ по памяти, поиск по имени; kill по PID — только с подтверждением",
       keywords=("процессы windows", "get-process", "убей процесс", "kill процесс",
                 "загрузка памяти windows", "диспетчер задач windows"),
       examples=("",), needs=("windows",))
def process(ctx: Context, text: str):
    params, _ = parse_params(text or "")
    top = params.get("top") or params.get("сколько") or "12"
    try:
        top = max(1, min(50, int(top)))
    except ValueError:
        top = 12

    pid = (params.get("kill") or params.get("pid") or "").strip()
    if pid:
        if not pid.isdigit():
            raise ToolError("PID должен быть числом: kill=1234")
        if not _need_confirm(params, text or ""):
            raise ToolError(f"kill PID {pid}: нужно подтверждение "
                            "(добавьте «подтверждаю» или confirm=да)")
        return _ps(ctx, f"Stop-Process -Id {pid} -Force -ErrorAction Stop; "
                        f"\"остановлен PID {pid}\"")

    return _ps(ctx, "Get-Process | Sort-Object WS -Descending | "
                    f"Select-Object -First {top} Id,ProcessName,"
                    "@{n='RAM_MB';e={[math]::Round($_.WS/1MB)}},CPU | "
                    "Format-Table -AutoSize")


@agent("win.eventlog", "Windows: журнал", "windows",
       "Последние события System: ошибки/предупреждения (Get-WinEvent)",
       keywords=("журнал событий windows", "eventlog windows", "get-winevent",
                 "ошибки windows", "события системы windows"),
       examples=("n=10",), needs=("windows",), tags=("slow",))
def eventlog(ctx: Context, text: str):
    params, _ = parse_params(text or "")
    try:
        n = max(1, min(50, int(params.get("n") or params.get("сколько") or 10)))
    except ValueError:
        n = 10
    level = (params.get("level") or params.get("уровень") or "error").lower()
    code = {"error": 2, "ошибка": 2, "warning": 3, "предупреждение": 3,
            "info": 4, "инфо": 4}.get(level, 2)
    script = (f"Get-WinEvent -FilterHashtable @{{LogName='System';Level={code}}} "
              f"-MaxEvents {n} | Select-Object TimeCreated,Id,ProviderName,"
              "@{n='Message';e={($_.Message -split \"`n\")[0]}} | Format-List")
    return _ps(ctx, script, timeout=90)


@agent("win.users", "Windows: пользователи", "windows",
       "Локальные пользователи и группы: Get-LocalUser / Get-LocalGroup",
       keywords=("пользователи windows", "get-localuser", "учетки windows",
                 "локальные пользователи", "группы windows"),
       examples=("",), needs=("windows",))
def users(ctx: Context, text: str):
    if "групп" in (text or "").lower():
        return _ps(ctx, "Get-LocalGroup | Select-Object Name,Description | "
                        "Format-Table -AutoSize")
    return _ps(ctx, "Get-LocalUser | Select-Object Name,Enabled,LastLogon,"
                    "Description | Format-Table -AutoSize")


@agent("win.tasks", "Windows: планировщик", "windows",
       "Задачи планировщика: имя, состояние, путь (Get-ScheduledTask)",
       keywords=("планировщик задач windows", "get-scheduledtask",
                 "задачи планировщика", "scheduled tasks windows"),
       examples=("",), needs=("windows",), tags=("slow",))
def tasks(ctx: Context, text: str):
    return _ps(ctx, "Get-ScheduledTask | Sort-Object State,TaskPath | "
                    "Select-Object State,TaskName,TaskPath | "
                    "Select-Object -First 60 | Format-Table -AutoSize", timeout=90)


@agent("win.firewall", "Windows: брандмауэр", "windows",
       "Правила брандмауэра: имя, направление, действие, профиль (только чтение)",
       keywords=("брандмауэр windows", "firewall windows", "get-netfirewallrule",
                 "правила firewall", "фаервол windows"),
       examples=("",), needs=("windows",), tags=("slow",))
def firewall(ctx: Context, text: str):
    return _ps(ctx, "Get-NetFirewallRule -Enabled True | "
                    "Select-Object DisplayName,Direction,Action,Profile | "
                    "Select-Object -First 40 | Format-Table -AutoSize", timeout=90)


@agent("win.updates", "Windows: обновления", "windows",
       "Установленные обновления Windows: Get-HotFix, последние 20",
       keywords=("обновления windows", "get-hotfix", "hotfix windows",
                 "заплатки windows", "патчи windows"),
       examples=("",), needs=("windows",), tags=("slow",))
def updates(ctx: Context, text: str):
    return _ps(ctx, "Get-HotFix | Sort-Object InstalledOn -Descending | "
                    "Select-Object -First 20 HotFixID,Description,InstalledOn | "
                    "Format-Table -AutoSize", timeout=90)


@agent("win.help", "Windows: справка", "windows",
       "Что умеют Windows-агенты и как включить реальное выполнение (--live)",
       keywords=("windows агенты", "что умеешь windows", "помощь windows",
                 "windows команды", "администрирование windows"),
       examples=("",))
def help_agent(ctx: Context, text: str):
    rows = [[a.id, a.description] for a in REGISTRY.all() if a.category == "windows"]
    head = ("Windows-агенты (реальное выполнение — только с --live; "
            f"сейчас: {'Windows' if is_windows() else 'не Windows, будет отказ'}):")
    return head + "\n" + table(rows, ["агент", "что делает"])
