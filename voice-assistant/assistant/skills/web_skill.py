from __future__ import annotations
import webbrowser
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext


class WebSkill(Skill):
    name = "web"
    description = "Открытие ссылок (по запросу)"
    intents = ["open_url"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        url = (intent.entities.get('url') or '').strip()
        if not url:
            return SkillResponse(text="Какую ссылку открыть? Укажите URL.")
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        # In headless/server env opening browser may not be useful; return URL for client/UI to open
        try:
            # best effort; may fail in headless
            webbrowser.open(url)
        except Exception:
            pass
        return SkillResponse(text=f"Ссылка: {url}", data={"url": url, "action": "open_url"})
