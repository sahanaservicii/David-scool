from __future__ import annotations
import json
import urllib.request
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext
from ..search.provider import SearchProvider


class FallbackSkill(Skill):
    name = "fallback"
    description = "Свободный диалог: локальная LLM (если настроена) или поиск/подсказка"
    intents = ["fallback", "chat"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        text = (intent.entities.get('text') or intent.raw or '').strip()
        if not text:
            return SkillResponse(text="Повторите, пожалуйста, запрос.")

        llm_cfg = self.cfg.get('llm', {}) or {}
        provider = str(llm_cfg.get('provider', 'rule_based')).lower()
        oc = llm_cfg.get('openai_compat') or {}
        base = str(oc.get('base_url') or '').strip()
        use_llm = provider == 'openai_compat' or (provider == 'auto' and bool(base))
        if use_llm and base:
            ans = self._ask_openai_compat(text, llm_cfg, ctx)
            if ans:
                return SkillResponse(text=ans, data={"source": "llm"})

        # try search as helpful fallback (if looks like info query)
        sp = SearchProvider(self.cfg)
        results = sp.search(text)
        if results:
            top = results[0]
            msg = f"По запросу нашёл: {top.title}\n{top.url}"
            if top.snippet:
                msg += f"\n{top.snippet}"
            return SkillResponse(text=msg, data={"source": "search", "results": [r.__dict__ for r in results[:3]]})

        if use_llm and base:
            return SkillResponse(text=(
                "Локальная языковая модель настроена, но сейчас недоступна. "
                "Проверьте, что LLM-сервер запущен (base_url в config/config.local.json) и отвечает."
            ), data={"source": "llm_unavailable"})
        return SkillResponse(text=(
            "Я могу выполнить локальные команды (время, таймеры, заметки, калькулятор, умный дом/Home Assistant при настройке), "
            "но для свободного диалога «как в чате» нужен локальный LLM-сервер (OpenAI-совместимый, например Ollama или llama.cpp). "
            "Укажите `llm.openai_compat.base_url` и модель в config/config.local.json, либо переформулируйте запрос. "
            "Скажите «помощь» для списка возможностей."
        ), data={"source": "none"})

    def _ask_openai_compat(self, text: str, llm_cfg: dict, ctx: DialogContext) -> str | None:
        oc = llm_cfg.get('openai_compat', {}) or {}
        base = (oc.get('base_url') or '').rstrip('/')
        if not base:
            return None
        url = base + '/chat/completions'
        system = llm_cfg.get('system_prompt', 'Ты полезный локальный ассистент.')
        # enrich with room context
        room_name = ctx.slots.get('room_name') or ctx.slots.get('room')
        if room_name:
            system += f"\nТекущая комната/контекст: {room_name}."
        ha_status = None
        try:
            ha = getattr(self, 'ha', None)
            if ha and getattr(ha, 'enabled', False):
                system += f"\nHome Assistant настроен ({ha.base_url}). Для точного состояния устройств используй результаты навыков/инструментов, не выдумывай."
        except Exception:
            pass

        messages = [{"role": "system", "content": system}]
        history = ctx.recent(12)
        # avoid duplicating current user message (already added to context)
        for i, m in enumerate(history):
            if m.role in ('user', 'assistant'):
                if i == len(history) - 1 and m.role == 'user' and (m.text or '').strip() == text.strip():
                    continue
                messages.append({"role": m.role, "content": m.text})
        messages.append({"role": "user", "content": text})
        payload = {
            "model": oc.get('model', 'local-model'),
            "messages": messages,
            "temperature": float(oc.get('temperature', 0.4)),
            "stream": False,
        }
        if oc.get('max_tokens'):
            try:
                payload['max_tokens'] = int(oc.get('max_tokens'))
            except Exception:
                pass
        data = json.dumps(payload).encode('utf-8')
        headers = {"Content-Type": "application/json"}
        if oc.get('api_key'):
            headers['Authorization'] = 'Bearer ' + oc['api_key']
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            timeout = int(oc.get('timeout', 90))
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode('utf-8', errors='replace'))
            choices = resp.get('choices') or []
            if choices:
                msg = choices[0].get('message') or {}
                content = msg.get('content') or ''
                if isinstance(content, list):
                    content = ''.join(p.get('text', '') for p in content if isinstance(p, dict))
                return str(content).strip() or None
        except Exception:
            return None
        return None
