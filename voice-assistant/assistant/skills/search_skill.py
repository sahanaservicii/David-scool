from __future__ import annotations
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext
from ..search.provider import SearchProvider


class SearchSkill(Skill):
    name = "search"
    description = "Поиск информации (онлайн без подписки / локальный fallback)"
    intents = ["search", "fallback"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        query = intent.entities.get('query') or intent.entities.get('text') or intent.raw
        # strip command words
        for prefix in ['найди', 'поиск', 'загугли', 'поищи в интернете', 'поищи', 'search for', 'search', 'google']:
            if query.lower().startswith(prefix):
                query = query[len(prefix):].strip(' :,-"\'' )
        query = (query or '').strip()
        if not query:
            return SkillResponse(text="Что нужно найти? Скажите: «найди ...»")

        provider = SearchProvider(self.cfg)
        results = provider.search(query)
        if results:
            lines = [f"Результаты по запросу «{query}»:"]
            for i, r in enumerate(results, 1):
                snip = f" — {r.snippet}" if r.snippet else ""
                lines.append(f"{i}. {r.title}\n   {r.url}{snip}")
            lines.append("\n(Поиск выполнен без подписки; источники открытые.)")
            return SkillResponse(text="\n".join(lines), data={"results": [r.__dict__ for r in results]})

        # offline/local fallback
        notes = self.storage.list_notes(limit=5, query=query)
        if notes:
            lines = [f"Онлайн-поиск недоступен, но нашёл в заметках по «{query}»:"]
            for n in notes:
                lines.append(f"• №{n['id']}: {n['text']}")
            return SkillResponse(text="\n".join(lines))

        return SkillResponse(
            text=(f"Не удалось выполнить онлайн-поиск по запросу «{query}». "
                  "Сеть недоступна или источник не ответил. "
                  "Подсказки: подключите интернет, укажите SearXNG в config (search.searxng_url), "
                  "или подключите локальную LLM для ответов без интернета."),
            data={"query": query, "online": False}
        )
