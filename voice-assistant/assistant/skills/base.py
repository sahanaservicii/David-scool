from __future__ import annotations
from typing import Any, Dict, List, Optional
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext
from ..core.storage import Storage


class Skill:
    name: str = "base"
    description: str = ""
    intents: List[str] = []

    def __init__(self, cfg: Dict[str, Any], storage: Storage):
        self.cfg = cfg
        self.storage = storage

    def can_handle(self, intent: IntentResult) -> bool:
        return intent.intent in self.intents or intent.skill == self.name

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        return SkillResponse(text="Навык не реализован.")


class SkillRegistry:
    def __init__(self):
        self.skills: List[Skill] = []
        self.by_name: Dict[str, Skill] = {}

    def register(self, skill: Skill):
        self.skills.append(skill)
        self.by_name[skill.name] = skill

    def get(self, name: str) -> Optional[Skill]:
        return self.by_name.get(name)

    def dispatch(self, intent: IntentResult, ctx: DialogContext) -> Optional[SkillResponse]:
        # prefer explicit skill
        if intent.skill and intent.skill in self.by_name:
            return self.by_name[intent.skill].handle(intent, ctx)
        for s in self.skills:
            if s.can_handle(intent):
                return s.handle(intent, ctx)
        return None
