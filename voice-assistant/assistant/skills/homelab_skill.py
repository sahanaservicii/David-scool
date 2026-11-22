from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext


class HomelabSkill(Skill):
    name = "homelab"
    description = "Интеграция с домашней лабораторией (homelab.py)"
    intents = ["homelab"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        root = Path(__file__).resolve().parents[2]
        # try ../homelab/homelab.py relative to workspace layout
        candidates = [
            root.parent / 'homelab' / 'homelab.py',
            Path('/root/workspace/homelab/homelab.py'),
        ]
        script = None
        for c in candidates:
            if c.exists():
                script = c
                break
        if not script:
            return SkillResponse(text="homelab.py не найден. Этот навык работает внутри экосистемы Домового.")
        text = intent.raw.lower()
        if 'инвентар' in text or 'устройств' in text:
            args = ['inventory']
        elif 'роутер' in text or 'router' in text or 'openwrt' in text:
            args = ['router', 'status']
        elif 'ha' in text or 'home assistant' in text or 'умн' in text:
            args = ['ha', 'states']
        else:
            args = ['doctor']
        try:
            p = subprocess.run(['python3', str(script)] + args, capture_output=True, text=True, timeout=30)
            out = (p.stdout or '').strip()
            err = (p.stderr or '').strip()
            if not out and err:
                out = err
            if len(out) > 3000:
                out = out[:3000] + '\n... (обрезано)'
            return SkillResponse(text=f"Homelab ({' '.join(args)}):\n{out or 'нет вывода'}",
                                 data={"rc": p.returncode})
        except Exception as e:
            return SkillResponse(text=f"Не удалось выполнить homelab.py: {e}")
