from __future__ import annotations
import datetime
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext

MONTHS_RU = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"]
DAYS_RU = ["понедельник","вторник","среда","четверг","пятница","суббота","воскресенье"]


class TimeSkill(Skill):
    name = "time"
    description = "Текущее время и дата"
    intents = ["time_now", "date_today"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        now = datetime.datetime.now().astimezone()
        if intent.intent == "time_now":
            text = f"Сейчас {now.strftime('%H:%M')}."
        else:
            text = f"Сегодня {DAYS_RU[now.weekday()]}, {now.day} {MONTHS_RU[now.month-1]} {now.year} года."
        return SkillResponse(text=text)
