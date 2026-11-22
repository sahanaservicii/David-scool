"""llm.py — опциональный локальный LLM-бэкенд (OpenAI-совместимый).

Система полностью работоспособна без него: все 100 агентов детерминированы.
Если на 127.0.0.1:8080 (llama.cpp / llamafile) или :11434 (ollama) поднят
сервер — `ai.*`-агенты начинают отвечать свободным текстом.
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from .tools import is_local_host
from dataclasses import dataclass, field


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class LLMClient:
    cfg: dict
    _ready: bool | None = None
    _info: dict = field(default_factory=dict)

    @property
    def urls(self) -> list[str]:
        llm = self.cfg.get("llm", {})
        urls = [llm.get("url") or ""] + list(llm.get("fallback_urls") or [])
        return [u.rstrip("/") for u in urls if u]

    def _probe_one(self, base: str, timeout: float = 1.5) -> dict | None:
        host = urllib.parse.urlparse(base).hostname or ""
        if not is_local_host(host):
            return None
        try:
            req = urllib.request.Request(f"{base}/models",
                                         headers={"User-Agent": "agentos/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read(200_000).decode("utf-8", "replace"))
            models = [m.get("id") for m in data.get("data", []) if m.get("id")]
            return {"url": base, "models": models}
        except (urllib.error.URLError, socket.timeout, TimeoutError, ValueError,
                OSError):
            return None

    def probe(self) -> dict | None:
        if self._ready is not None:
            return self._info or None
        if not self.cfg.get("llm", {}).get("enabled", True):
            self._ready = False
            return None
        for base in self.urls:
            info = self._probe_one(base)
            if info:
                self._ready = True
                self._info = info
                return info
        self._ready = False
        return None

    @property
    def available(self) -> bool:
        return self.probe() is not None

    def complete(self, prompt: str, *, system: str | None = None,
                 max_tokens: int = 700, temperature: float = 0.2) -> str:
        info = self.probe()
        if not info:
            raise LLMUnavailable("локальный LLM не запущен")
        llm = self.cfg.get("llm", {})
        model = llm.get("model") or (info["models"][0] if info["models"] else "local")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({
            "model": model, "messages": messages, "temperature": temperature,
            "max_tokens": max_tokens, "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{info['url']}/chat/completions", data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "User-Agent": "agentos/1.0"},
        )
        timeout = int(llm.get("timeout", 90))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read(2_000_000).decode("utf-8", "replace"))
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
            raise LLMUnavailable(f"LLM не ответил: {exc}") from exc
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMUnavailable("непонятный ответ LLM") from exc


def describe(cfg: dict) -> dict:
    client = LLMClient(cfg)
    info = client.probe()
    if info:
        return {"available": True, "url": info["url"], "models": info["models"]}
    return {"available": False, "urls": client.urls,
            "hint": "подними llama.cpp/ollama на 127.0.0.1 — агенты ai.* включатся сами"}
