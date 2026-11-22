"""AI-агенты: работают и без LLM — тогда отвечает профильный мини-агент."""
from __future__ import annotations

import json

from ..core import REGISTRY, Context, agent, run_agent
from ..llm import LLMClient, LLMUnavailable, describe
from ..utils import kv, truncate

SYSTEM = (
    "Ты Домовой — локальный домашний системный администратор. Отвечай по-русски, "
    "коротко и по делу. Работаешь только офлайн, без облаков. Не выдумывай IP, "
    "имена и возможности устройств. Если данных нет — так и скажи."
)


def _client(ctx: Context) -> LLMClient:
    if ctx.llm_client is None:
        ctx.llm_client = LLMClient(ctx.cfg)
    return ctx.llm_client


@agent("ai.ask", "Свободный вопрос", "ai",
       "Отвечает через локальную LLM; без неё — запускает профильного агента",
       keywords=("спроси", "объясни", "ask", "что делать", "помоги", "почему"),
       examples=("почему камеры лучше держать в отдельном vlan",), needs=("llm",))
def ask(ctx: Context, text: str):
    question = (text or "").strip()
    if not question:
        raise ValueError("задай вопрос")
    client = _client(ctx)
    if client.available:
        try:
            return client.complete(question, system=SYSTEM, max_tokens=700)
        except LLMUnavailable as exc:
            note = f"(LLM не ответила: {exc})\n"
    else:
        note = ("LLM недоступна — отвечает профильный мини-агент.\n"
                "Поднять локальную LLM: llama-server -m model.gguf --port 8080 "
                "или ollama serve (агенты ai.* включатся сами).\n\n")
    ranked = REGISTRY.route(question, 1)
    if not ranked:
        return note + "Не понял вопрос. Список умений: agentos list"
    target, score = ranked[0]
    res = run_agent(target, ctx, question)
    return note + f"[{target.id} · {target.name}]\n" + res.text()


@agent("ai.rewrite", "Переписать текст", "ai",
       "Улучшает формулировку: через LLM или детерминированной чисткой",
       keywords=("перепиши", "улучши текст", "rewrite", "сформулируй", "письмо"),
       examples=("нужно чтобы роутер был перезагружен завтра утром по возможности",), needs=("llm",))
def rewrite(ctx: Context, text: str):
    src = (text or "").strip()
    if not src:
        raise ValueError("дай текст")
    client = _client(ctx)
    if client.available:
        try:
            return client.complete(
                "Перепиши текст ясно и коротко, сохранив смысл. Только результат:\n\n"
                + src, system=SYSTEM, max_tokens=500, temperature=0.3)
        except LLMUnavailable:
            pass
    fixed = " ".join(src.split())
    fixed = fixed.replace(" ,", ",").replace(" .", ".").replace("  ", " ")
    if fixed and not fixed[0].isupper():
        fixed = fixed[0].upper() + fixed[1:]
    if fixed and fixed[-1] not in ".!?":
        fixed += "."
    return ("(LLM выключена, базовые правки)\n" + fixed)


@agent("ai.status", "Статус ИИ", "ai",
       "Показывает, доступна ли локальная LLM, и статистику системы",
       keywords=("статус ии", "llm", "модель", "нейросеть", "ai status"),
       examples=("",), needs=())
def status(ctx: Context, text: str):
    info = describe(ctx.cfg)
    st = ctx.memory.stats() if ctx.memory else {}
    lines = [
        f"агентов в реестре: {len(REGISTRY)}",
        f"LLM: {'доступна — ' + info['url'] if info['available'] else 'выключена'}",
    ]
    if info.get("available"):
        lines.append("модели: " + ", ".join(info.get("models") or ["?"]))
    else:
        lines.append("подсказка: " + info.get("hint", ""))
    if st:
        lines.append(f"прогонов: {st['runs']}, успешных: {st['ok']}, "
                     f"среднее время: {st['avg_ms']} мс")
    return "\n".join(lines)
