from __future__ import annotations
import random
import datetime
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext


class SmalltalkSkill(Skill):
    name = "smalltalk"
    description = "Приветствия, вежливость, базовый диалог"
    intents = ["greeting", "how_are_you", "who_are_you", "thanks", "goodbye", "empty"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        lang = self.cfg.get("app", {}).get("language", "ru")
        if intent.intent == "greeting":
            text = random.choice([
                "Здравствуйте! Чем могу помочь?",
                "Привет! Я на связи.",
                "Слушаю вас. Что нужно сделать?",
            ])
        elif intent.intent == "how_are_you":
            text = random.choice([
                "Работаю стабильно. Готов помочь.",
                "Всё в порядке. Чем могу быть полезен?",
            ])
        elif intent.intent == "who_are_you":
            name = self.cfg.get("app", {}).get("name", "Свободный Голос")
            ha = (self.cfg.get("home_assistant") or {}).get("url")
            llm = (self.cfg.get("llm") or {}).get("openai_compat") or {}
            llm_on = bool(llm.get("base_url"))
            parts = [f"Я — {name}, локальный голосовой помощник для дома и сервера."]
            parts.append("Могу вести диалог, помогать с умным домом (Home Assistant), таймерами, заметками, поиском и системными задачами.")
            if llm_on:
                parts.append("Режим свободного диалога через локальную LLM настроен.")
            else:
                parts.append("Для свободного диалога «как в чате» можно подключить локальную LLM на сервере.")
            if ha:
                parts.append("Интеграция с Home Assistant сконфигурирована.")
            text = " ".join(parts)
        elif intent.intent == "thanks":
            text = random.choice(["Пожалуйста!", "Рад помочь.", "Всегда к услугам."])
        elif intent.intent == "goodbye":
            text = random.choice(["До связи!", "Хорошего дня.", "Пока!"])
        else:
            text = "Я вас не расслышал. Повторите, пожалуйста, или скажите «помощь»."
        return SkillResponse(text=text)
