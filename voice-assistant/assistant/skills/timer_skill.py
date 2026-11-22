from __future__ import annotations
import time
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext


def fmt_duration(sec: int) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h: parts.append(f"{h} ч")
    if m: parts.append(f"{m} мин")
    if s or not parts: parts.append(f"{s} сек")
    return " ".join(parts)


class TimerSkill(Skill):
    name = "timer"
    description = "Таймеры и напоминания через время"
    intents = ["timer_set", "timer_list", "timer_cancel"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        if intent.intent == "timer_set":
            seconds = int(intent.entities.get('seconds') or 0)
            if seconds <= 0:
                return SkillResponse(text="На сколько поставить таймер? Пример: «таймер на 5 минут».")
            label = intent.entities.get('label') or 'Таймер'
            due = time.time() + seconds
            tid = self.storage.add_timer(label, due)
            return SkillResponse(text=f"Таймер №{tid} «{label}» установлен на {fmt_duration(seconds)}.",
                                 data={"timer_id": tid, "due_at": due})
        if intent.intent == "timer_cancel":
            # cancel last active
            timers = self.storage.list_timers(active_only=True)
            if not timers:
                return SkillResponse(text="Активных таймеров нет.")
            # simple: cancel most recent
            tid = timers[-1]['id']
            self.storage.cancel_timer(tid)
            return SkillResponse(text=f"Таймер №{tid} отменён.")
        timers = self.storage.list_timers(active_only=True)
        if not timers:
            return SkillResponse(text="Активных таймеров нет.")
        now = time.time()
        lines = []
        for t in timers:
            left = max(0, int(t['due_at'] - now))
            lines.append(f"№{t['id']} {t['label']}: осталось {fmt_duration(left)}")
        return SkillResponse(text="Активные таймеры:\n" + "\n".join(lines))
