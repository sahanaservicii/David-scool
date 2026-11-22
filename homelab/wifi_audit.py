#!/usr/bin/env python3
"""Еженедельный ночной read-only аудит Wi-Fi Домового.

Проверяет SSID `RT-WIFI-47` (фактическое имя из UCI) и фиксирует, что
`sahanovschi` в инвентаре — хост, а не SSID. Ничего не меняет на роутере:
никаких uci set/commit, wifi reload, reboot, firewall.

Авто-фиксы допустимы только локально (каталоги, повтор команд, атомарная
перезапись отчёта/состояния). Правки конфига роутера попадают в раздел
`fix_proposals` отчёта и требуют отдельного подтверждения пользователя.

Использование: python3 homelab/wifi_audit.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/root/workspace")
HOMELAB = WORKSPACE / "homelab"
HL = HOMELAB / "homelab.py"
REPORT_DIR = WORKSPACE / "reports"
STATE_DIR = HOMELAB / "state"
STATE_FILE = STATE_DIR / "wifi_audit.json"

TARGET_SSIDS = ("RT-WIFI-47", "sahanovschi")
SECRET_LINE_RE = re.compile(r"(?i)(\.|\"|')(key|password|passwd|secret|token|psk)(\"|')?\s*[=:]|[\"']key[\"']\s*:")
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
REDACTED_MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){3}xx:xx:xx\b")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize(text: str) -> str:
    out = []
    for line in text.splitlines():
        if SECRET_LINE_RE.search(line):
            continue  # PSK/пароли/токены никогда не попадают в отчёт
        line = MAC_RE.sub(lambda m: ":".join(m.group(0).split(":")[:3]) + ":xx:xx:xx", line)
        line = "".join(ch if ch.isprintable() or ch == "\t" else " " for ch in line)
        out.append(line)
    return "\n".join(out)


def hcmd(args: list[str], timeout: int = 30) -> tuple[bool, str]:
    """Выполнить read-only команду homelab.py; при сбое повторить один раз."""
    for attempt in range(2):
        try:
            p = subprocess.run(
                [sys.executable, str(HL), *args],
                cwd=str(HOMELAB), capture_output=True, text=True, timeout=timeout,
            )
            text = sanitize(p.stdout + ("\n" + p.stderr if p.stderr else ""))
            if p.returncode == 0:
                return True, text
            last = text.strip()[-200:]
        except (subprocess.TimeoutExpired, OSError) as exc:
            last = type(exc).__name__
    return False, last


def parse_uci(text: str) -> dict[str, dict[str, str]]:
    props: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"^wireless\.([^.]+)\.([^=]+)=('?)([^'\n]*)\3\s*$", text, re.M):
        section, key, _quote, value = m.groups()
        props.setdefault(section, {})[key] = value
    return {s: v for s, v in props.items() if "ssid" in v}


def parse_iwinfo(text: str) -> list[dict]:
    result = []
    for block in re.split(r"\n\s*\n", text):
        m = re.match(r"\s*(\S+)\s+ESSID:\s*\"([^\"]*)\"", block)
        if not m:
            continue
        iface, ssid = m.groups()
        def grab(pattern: str, cast=int):
            found = re.search(pattern, block)
            return cast(found.group(1)) if found else None
        result.append({
            "iface": iface,
            "ssid": ssid,
            "channel": grab(r"Channel:\s*(\d+)"),
            "htmode": (re.search(r"HT Mode:\s*(\S+)", block) or [None, None])[1],
            "txpower": grab(r"Tx-Power:\s*(\d+)"),
            "signal": grab(r"Signal:\s*(-?\d+)"),
            "noise": grab(r"Noise:\s*(-?\d+)"),
        })
    return result


def count_clients(iface: str) -> int | None:
    ok, text = hcmd(["router", "exec", f"iwinfo {iface} assoclist"], timeout=25)
    if not ok:
        return None
    return sum(1 for line in text.splitlines() if REDACTED_MAC_RE.match(line.strip()))


def main() -> int:
    fixes: list[str] = []
    errors: list[str] = []

    for d in (REPORT_DIR, STATE_DIR):
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            fixes.append(f"создан каталог {d.relative_to(WORKSPACE)}")

    old_invalid = False
    if STATE_FILE.exists():
        try:
            json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            old_invalid = True
    if old_invalid:
        fixes.append("перезаписан повреждённый state/wifi_audit.json")

    cmds = {
        "uci": ["router", "uci", "wireless"],
        "iwinfo": ["router", "exec", "iwinfo"],
        "status": ["router", "status"],
        "logread": ["router", "exec", "logread"],
    }
    out: dict[str, str] = {}
    for name, args in cmds.items():
        ok, text = hcmd(args)
        if ok:
            out[name] = text
        else:
            errors.append(f"команда {name} недоступна: {text[:120]}")

    uci_ifaces = parse_uci(out.get("uci", ""))
    radios = parse_iwinfo(out.get("iwinfo", ""))
    for r in radios:
        r["clients"] = count_clients(r["iface"])

    logs = out.get("logread", "")
    log_counts = {
        "auth_noack": len(re.findall(r"did not acknowledge authentication response", logs, re.I)),
        "deauth": len(re.findall(r"deauthenticated", logs, re.I)),
        "dhcp_discover": len(re.findall(r"DHCPDISCOVER", logs, re.I)),
        "ssh_bad_password": len(re.findall(r"Bad password attempt", logs, re.I)),
        "ssh_preauth_exit": len(re.findall(r"Exit before auth", logs, re.I)),
    }
    suspicious_macs = []
    for line in logs.splitlines():
        if "did not acknowledge authentication response" in line.lower():
            m = REDACTED_MAC_RE.search(line)
            if m:
                suspicious_macs.append(m.group(0))
    suspicious_macs = sorted(set(suspicious_macs))[:5]

    findings = []
    proposals = []
    present = {r["ssid"] for r in radios}
    for ssid in TARGET_SSIDS:
        if ssid not in present:
            if ssid == "sahanovschi":
                findings.append({"severity": "info", "text": "sahanovschi в homelab.json — хост (sahanovschi.v6.rocks), не SSID; по вашему выбору проверяется только Wi-Fi."})
            else:
                findings.append({"severity": "warn", "text": f"SSID {ssid} не вещается ни на одном радио."})

    for r in radios:
        if r["clients"] is None:
            findings.append({"severity": "warn", "text": f"{r['iface']} ({r['ssid']}): не удалось прочитать список клиентов."})
        if r["signal"] is not None and -30 < r["signal"] < 0:
            findings.append({"severity": "info", "text": f"{r['iface']}: сигнал {r['signal']} dBm — очень сильный, возможен избыток мощности."})

    cfg_disabled = [s for s, v in uci_ifaces.items() if str(v.get("disabled", "0")) == "1"]
    if cfg_disabled:
        findings.append({"severity": "warn", "text": "Отключённые wifi-iface в UCI: " + ", ".join(cfg_disabled)})

    ch35 = [r["channel"] for r in radios if r["ssid"] == "RT-WIFI-47" and r["channel"] and r["channel"] >= 36]
    if len(set(ch35)) == 1 and len(ch35) > 1:
        findings.append({"severity": "info", "text": f"Два 5 ГГц радио RT-WIFI-47 работают на одном канале {ch35[0]} — возможна интерференция."})
        proposals.append("Развести radio0 и radio1 по разным 5 ГГц-каналам (например 36/149) — только после вашего подтверждения и бэкапа.")

    if log_counts["auth_noack"]:
        findings.append({"severity": "warn", "text": f"Wi-Fi: {log_counts['auth_noack']} ошибок «did not acknowledge authentication response»" + (f", OUI: {', '.join(suspicious_macs)}" if suspicious_macs else "") + "."})
        proposals.append("Проверить клиента с указанным OUI: он пытается ассоциироваться с основным SSID, хотя числится в allow-списке гостевой сети. Изменения macfilter — только после подтверждения.")
    if log_counts["ssh_bad_password"]:
        findings.append({"severity": "warn", "text": f"Безопасность (не Wi-Fi): {log_counts['ssh_bad_password']} неудачных попыток пароля к SSH и {log_counts['ssh_preauth_exit']} обрывов до аутентификации."})
        proposals.append("Ограничить SSH белым списком источников / WireGuard — требует изменения firewall, только после подтверждения.")

    if not findings:
        findings.append({"severity": "ok", "text": "Подозрительных событий не найдено."})
    if not proposals:
        proposals.append("Авто-фиксы роутера не потребовались.")

    ok = not errors
    state = {
        "generated_utc": utc_now(),
        "ok": ok,
        "target_ssids": list(TARGET_SSIDS),
        "radios": radios,
        "log_counts": log_counts,
        "findings": findings,
        "fixes_applied": fixes,
        "fix_proposals": proposals,
        "errors": errors,
    }

    lines = [
        f"# Ночной аудит Wi-Fi — {datetime.now():%Y-%m-%d %H:%M} (локальное время)",
        "",
        f"Статус: **{'OK' if ok else 'ОШИБКА'}**. Источник: `homelab.py router` (только чтение).",
        "PSK/ключи и MAC-адреса клиентов из отчёта удалены.",
        "",
        "## Состояние радио",
        "",
        "| Интерфейс | SSID | Канал | HT | Tx, dBm | Сигнал, dBm | Клиентов |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in radios:
        lines.append(f"| {r['iface']} | {r['ssid']} | {r['channel']} | {r['htmode']} | {r['txpower']} | {r['signal']} | {r['clients']} |")
    lines += ["", "## Находки", ""]
    for f in findings:
        lines.append(f"- **{f['severity'].upper()}:** {f['text']}")
    lines += ["", "## Что исправлено автоматически (только локально)", ""]
    for f in fixes or ["ничего не потребовалось"]:
        lines.append(f"- {f}")
    lines += ["", "## Предложения по роутеру (НЕ применены, нужно подтверждение)", ""]
    for p in proposals:
        lines.append(f"- {p}")
    if errors:
        lines += ["", "## Ошибки сбора", ""] + [f"- {e}" for e in errors]

    report = REPORT_DIR / f"wifi-audit-{datetime.now():%Y-%m-%d}.md"
    tmp = Path(str(report) + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(report)
    fixes.append(f"отчёт перезаписан атомарно: {report.relative_to(WORKSPACE)}")
    state["fixes_applied"] = fixes

    stmp = Path(str(STATE_FILE) + ".tmp")
    stmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    stmp.replace(STATE_FILE)

    print(json.dumps({"ok": ok, "report": str(report), "radios": len(radios), "findings": len(findings), "fixes": len(fixes)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
