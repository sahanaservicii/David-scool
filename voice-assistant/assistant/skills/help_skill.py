from __future__ import annotations
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext

HELP_TEXT = """Я умею (локально, без подписок; часть функций зависит от настройки):
• Диалог «как в чате»: свободные вопросы и помощь — при подключённой локальной LLM (Ollama/llama.cpp, OpenAI-compatible) на сервере.
• Умный дом / Home Assistant: «статус HA», «какая температура в спальне», «включи/выключи свет в кухне», «что включено».
• Мультирум-медиа (через HA media_player): «включи музыку в этой комнате», «пауза/продолжи», «громче/тише», «следующий трек» (нужны настроенные комнаты и плееры в config).
• Время и дата: «который час», «какая сегодня дата».
• Таймеры: «таймер на 5 минут», «мои таймеры», «отмени таймер».
• Заметки: «запиши купить хлеб», «мои заметки», «найди заметку хлеб».
• Калькулятор: «посчитай (2+3)*4».
• Поиск: «найди в интернете ...» (без ключей, если есть сеть) или локальный fallback.
• Погода: «погода в Москве» (онлайн-источник при доступе).
• Система: «статус системы».
• Homelab: «статус homelab», «роутер», «инвентарь» (через homelab.py, если доступно).

Советы: выберите комнату в веб-интерфейсе для команд «в этой комнате». Для продакшена настройте config/config.local.json (HA, LLM, rooms, STT/TTS, allow_lan)."""


class HelpSkill(Skill):
    name = "help"
    description = "Справка о возможностях"
    intents = ["help"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        return SkillResponse(text=HELP_TEXT)
