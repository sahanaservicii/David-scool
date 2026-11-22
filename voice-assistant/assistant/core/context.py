from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class Message:
    role: str  # user/assistant/system
    text: str
    ts: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogContext:
    session_id: str = "default"
    language: str = "ru"
    messages: List[Message] = field(default_factory=list)
    slots: Dict[str, Any] = field(default_factory=dict)
    last_intent: Optional[str] = None
    pending: Optional[Dict[str, Any]] = None  # for confirmations/multi-turn

    def add(self, role: str, text: str, **meta):
        self.messages.append(Message(role=role, text=text, meta=meta))
        # keep bounded
        if len(self.messages) > 100:
            self.messages = self.messages[-100:]

    def recent(self, n: int = 10) -> List[Message]:
        return self.messages[-n:]
