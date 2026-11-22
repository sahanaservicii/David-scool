from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IntentResult:
    intent: str
    confidence: float = 1.0
    entities: Dict[str, Any] = field(default_factory=dict)
    skill: Optional[str] = None
    raw: str = ""


@dataclass
class SkillResponse:
    text: str
    speak: Optional[str] = None
    end_session: bool = False
    data: Dict[str, Any] = field(default_factory=dict)
    ask: Optional[str] = None  # follow-up question key
