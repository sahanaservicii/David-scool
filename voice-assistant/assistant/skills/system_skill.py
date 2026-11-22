from __future__ import annotations
import os
import platform
import shutil
import time
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext


def _uptime():
    try:
        with open('/proc/uptime') as f:
            sec = float(f.read().split()[0])
        h = int(sec // 3600); m = int((sec % 3600) // 60)
        return f"{h} ч {m} мин"
    except Exception:
        return "н/д"


def _mem():
    try:
        info = {}
        with open('/proc/meminfo') as f:
            for line in f:
                k, v = line.split(':', 1)
                info[k.strip()] = int(v.strip().split()[0])  # kB
        total = info.get('MemTotal', 0) / 1024
        avail = info.get('MemAvailable', 0) / 1024
        used = total - avail
        return f"{used:.0f}/{total:.0f} МБ (свободно {avail:.0f} МБ)"
    except Exception:
        return "н/д"


class SystemSkill(Skill):
    name = "system"
    description = "Статус системы"
    intents = ["system_info"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        du = shutil.disk_usage('/')
        disk = f"{du.used//(1024**3)}/{du.total//(1024**3)} ГБ"
        load = "н/д"
        try:
            load = ", ".join(f"{x:.2f}" for x in os.getloadavg())
        except Exception:
            pass
        lines = [
            "Статус системы:",
            f"• Хост: {platform.node() or 'local'}",
            f"• ОС: {platform.system()} {platform.release()} ({platform.machine()})",
            f"• Python: {platform.python_version()}",
            f"• Uptime: {_uptime()}",
            f"• Память: {_mem()}",
            f"• Диск /: {disk}",
            f"• Load avg: {load}",
        ]
        return SkillResponse(text="\n".join(lines))
