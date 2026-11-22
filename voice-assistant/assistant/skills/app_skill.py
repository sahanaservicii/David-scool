from __future__ import annotations
import shutil
import subprocess
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext

# Safe allowlist concept - by default do nothing destructive, just report
SAFE_INFO = {
    'браузер': 'browser', 'browser': 'browser', 'firefox': 'firefox', 'chromium': 'chromium',
    'терминал': 'terminal', 'terminal': 'terminal', 'настройки': 'settings', 'settings': 'settings',
}


class AppControlSkill(Skill):
    name = "app_control"
    description = "Запуск приложений (безопасный режим, зависит от окружения)"
    intents = ["app_open"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        app = (intent.entities.get('app') or '').strip()
        if not app:
            return SkillResponse(text="Какое приложение запустить?")
        key = app.lower()
        mapped = SAFE_INFO.get(key)
        # We do not blindly execute arbitrary commands for safety.
        if not mapped:
            return SkillResponse(
                text=(f"Запрос на запуск «{app}» получен, но выполнение произвольных приложений "
                      "ограничено политикой безопасности. Добавьте приложение в allowlist в конфиге навыка."),
                data={"app": app, "executed": False})
        # try common binaries
        candidates = {
            'firefox': ['firefox'],
            'chromium': ['chromium', 'chromium-browser', 'google-chrome'],
            'terminal': ['x-terminal-emulator', 'gnome-terminal', 'konsole', 'xterm'],
        }.get(mapped, [])
        for c in candidates:
            if shutil.which(c):
                try:
                    subprocess.Popen([c], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return SkillResponse(text=f"Запускаю {app} ({c}).", data={"app": app, "cmd": c, "executed": True})
                except Exception as e:
                    return SkillResponse(text=f"Не удалось запустить {c}: {e}")
        return SkillResponse(text=f"Команда для «{app}» не найдена в этой системе.", data={"app": app, "executed": False})
