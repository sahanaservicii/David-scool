from __future__ import annotations
import re
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext


class NotesSkill(Skill):
    name = "notes"
    description = "Заметки: добавить, список, поиск, удаление"
    intents = ["note_add", "note_list", "note_find"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        if intent.intent == "note_add":
            body = (intent.entities.get('text') or '').strip()
            if not body:
                return SkillResponse(text="Что записать? Скажите: «запиши ...»", ask="note_text")
            nid = self.storage.add_note(body)
            return SkillResponse(text=f"Записал заметку №{nid}: {body}")
        if intent.intent == "note_find":
            q = intent.entities.get('query', '').strip()
            notes = self.storage.list_notes(limit=10, query=q)
            if not notes:
                return SkillResponse(text=f"Заметок по запросу «{q}» не найдено." if q else "Заметок пока нет.")
            lines = [f"№{n['id']}: {n['text']}" for n in notes]
            return SkillResponse(text="Нашёл заметки:\n" + "\n".join(lines))
        # list
        notes = self.storage.list_notes(limit=10)
        if not notes:
            return SkillResponse(text="Заметок пока нет. Скажите: «запиши купить молоко».")
        lines = [f"№{n['id']}: {n['text']}" for n in notes]
        return SkillResponse(text="Последние заметки:\n" + "\n".join(lines))
