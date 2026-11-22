from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext
from ..core.rooms import normalize_rooms, resolve_room as resolve_room_config, room_summary
from ..integrations.homeassistant import HomeAssistantClient, ha_client_from_config


ON_WORDS = ("включи", "вруби", "зажги", "активируй", "запусти", "turn on", "enable", "открой")
OFF_WORDS = ("выключи", "отключи", "погаси", "деактивируй", "останови", "turn off", "disable", "закрой")
TOGGLE_WORDS = ("переключи", "toggle",)

LIGHT_DOMAINS = ["light", "switch", "input_boolean"]
MEDIA_DOMAINS = ["media_player"]
CLIMATE_DOMAINS = ["climate"]
COVER_DOMAINS = ["cover"]
SCENE_SCRIPT_DOMAINS = ["scene", "script", "automation"]

GENERIC_ROOM_HINTS = ("здесь", "тут", "в этой комнате", "в комнате", "сюда")


def _contains_any(text: str, words) -> bool:
    t = (text or "").lower()
    return any(w in t for w in words)


def _strip_room_phrases(text: str) -> str:
    t = " " + (text or "") + " "
    pats = [
        r"\bв этой комнате\b", r"\bв комнате\b", r"\bздесь\b", r"\bтут\b", r"\bсюда\b",
    ]
    for p in pats:
        t = re.sub(p, " ", t, flags=re.I)
    # remove "в/во/на <room>" fragments generically at end/beginning chunks? keep conservative
    t = re.sub(r"\s+", " ", t).strip(" ,.-")
    return t


class HomeAssistantSkill(Skill):
    name = "ha"
    description = "Управление умным домом и мультирум-медиа через Home Assistant (локально)"
    intents = ["ha_status", "ha_query", "ha_control", "media_control"]

    def __init__(self, cfg: Dict[str, Any], storage):
        super().__init__(cfg, storage)
        self.ha: HomeAssistantClient = ha_client_from_config(cfg)

    def can_handle(self, intent: IntentResult) -> bool:
        return super().can_handle(intent)

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        if intent.intent == "ha_status":
            return self._handle_status()
        if intent.intent == "ha_query":
            return self._handle_query(intent, ctx)
        if intent.intent == "ha_control":
            return self._handle_control(intent, ctx)
        if intent.intent == "media_control":
            return self._handle_media(intent, ctx)
        return SkillResponse(text="Неизвестная команда Home Assistant.")

    def _require_ha(self) -> Optional[SkillResponse]:
        if not self.ha.enabled:
            return SkillResponse(
                text=(
                    "Home Assistant не настроен. Укажите URL и токен в config/config.local.json "
                    "(home_assistant.url/token) или переменные окружения HASS_URL/HASS_TOKEN, "
                    "либо укажите secrets_file с HASS_TOKEN."
                ),
                data={"configured": False},
            )
        status = self.ha.safe_status(quick=True)
        if not status.get("reachable") and status.get("status_code") not in (401, 403):
            return SkillResponse(
                text=(
                    f"Home Assistant недоступен по адресу {status.get('url') or self.ha.base_url}. "
                    f"Ошибка: {status.get('error') or 'нет ответа'}. "
                    "Проверьте, запущен ли HA, доступен ли он из локальной сети сервера и корректен ли URL."
                ),
                data={"configured": True, "reachable": False, "status": status},
            )
        if status.get("status_code") in (401, 403) and not self.ha.token:
            return SkillResponse(
                text=(
                    "Home Assistant отвечает, но требуется токен доступа (Long-Lived Access Token). "
                    "Добавьте HASS_TOKEN в secrets/homelab.env или home_assistant.token в config.local.json."
                ),
                data={"configured": True, "reachable": True, "auth_required": True, "status": status},
            )
        return None

    def _handle_status(self) -> SkillResponse:
        st = self.ha.safe_status(quick=False)
        if not st.get("configured"):
            return SkillResponse(text="Home Assistant не настроен (url/token отсутствуют).", data=st)
        if st.get("reachable") and st.get("status_code") == 200:
            name = st.get("location_name") or "Home Assistant"
            ver = st.get("version") or "?"
            return SkillResponse(
                text=f"Home Assistant доступен: {name} (версия {ver}) по адресу {st.get('url')}. Токен: {'задан' if st.get('has_token') else 'не задан'}.",
                data=st,
            )
        if st.get("status_code") in (401, 403):
            return SkillResponse(
                text=f"Home Assistant доступен по адресу {st.get('url')}, но доступ отклонён (HTTP {st.get('status_code')}). Проверьте токен.",
                data=st,
            )
        return SkillResponse(
            text=f"Home Assistant недоступен: {st.get('url') or 'URL не задан'}. {st.get('error') or ''}".strip(),
            data=st,
        )

    def _rooms(self) -> List[Dict[str, Any]]:
        return normalize_rooms(self.cfg.get("rooms") or [])

    def _current_room(self, intent: IntentResult, ctx: DialogContext) -> Dict[str, Any]:
        ent = intent.entities or {}
        # if router/engine passed explicit room_config use it
        rc = ent.get("room_config")
        if isinstance(rc, dict) and rc.get("id"):
            # enrich from config by id
            r = resolve_room_config(self._rooms(), hint=rc.get("id"), context_room_id=ctx.slots.get("room"), satellite_id=ent.get("satellite_id"))
            return r
        hint = ent.get("room") or ent.get("room_id") or ent.get("room_name") or ctx.slots.get("room")
        return resolve_room_config(
            self._rooms(),
            hint=hint,
            text=intent.raw,
            context_room_id=ctx.slots.get("room"),
            satellite_id=ent.get("satellite_id") or ctx.slots.get("satellite_id"),
        )

    def _entity_name_guess(self, text: str) -> str:
        t = text.lower()
        remove = [
            "включи", "выключи", "вруби", "отключи", "зажги", "погаси", "переключи",
            "пожалуйста", "свет", "лампу", "лампочка", "розетку", "устройство",
            "музыку", "трек", "песню", "плейлист", "радио", "альбом",
            "в этой комнате", "в комнате", "здесь", "тут", "в", "во", "на", "у",
            "сделай", "поставь", "запусти", "воспроизведи", "играй", "проиграй",
            "покажи", "скажи", "какая", "какой", "какие", "статус", "состояние",
        ]
        for w in remove:
            t = re.sub(rf"\b{re.escape(w)}\b", " ", t)
        # remove known room aliases from guess
        for r in self._rooms():
            for nm in [r.get("id"), r.get("name")] + list(r.get("aliases") or []):
                nm = str(nm or "").strip().lower()
                if nm and len(nm) >= 3:
                    t = re.sub(rf"\b{re.escape(nm)}\b", " ", t)
        t = re.sub(r"\s+", " ", t).strip(" ,.-")
        return t

    def _domain_guess(self, text: str) -> List[str]:
        t = text.lower()
        if any(w in t for w in ("свет", "ламп", "люстр", "подсвет")):
            return LIGHT_DOMAINS
        if any(w in t for w in ("музык", "трек", "песн", "плейлист", "радио", "колонк", "динамик", "медиаплеер", "spotify", "youtube")):
            return MEDIA_DOMAINS
        if any(w in t for w in ("температур", "кондиционер", "климат", "обогрев", "термостат")):
            return CLIMATE_DOMAINS
        if any(w in t for w in ("штор", "жалюзи", "ворот", "замок", "двер")):
            return COVER_DOMAINS
        if any(w in t for w in ("сцен", "скрипт", "automation")):
            return SCENE_SCRIPT_DOMAINS
        return LIGHT_DOMAINS + ["switch", "input_boolean", "media_player", "climate", "cover", "scene", "script"]

    def _resolve_room_media_player(self, room: Dict[str, Any], text: str = "") -> Optional[str]:
        if not room:
            return None
        # explicit config
        for key in ("media_player", "ma_player", "player", "speaker"):
            mp = str(room.get(key) or "").strip()
            if mp:
                return mp
        name = str(room.get("name") or room.get("id") or "")
        guess = self._entity_name_guess(text)
        # try prefer room
        ent = self.ha.resolve_entity(guess or name, domains=MEDIA_DOMAINS, prefer_room=name)
        if not ent and name:
            ent = self.ha.resolve_entity(name, domains=MEDIA_DOMAINS, prefer_room=name)
        if ent:
            return str(ent.get("entity_id"))
        return None

    def _extract_media_query(self, text: str, room: Dict[str, Any]) -> str:
        t = (text or "").strip()
        # remove command phrases
        t = re.sub(r"^(пожалуйста\s+)?(включи|запусти|поставь|воспроизведи|играй|проиграй|сыграй)\s+", "", t, flags=re.I)
        # remove leading "музыку/трек/..." but keep content after it
        t = re.sub(r"^(музык[уаеыюя]*|трек|песн[уаеыюя]*|плейлист|радио|альбом)\s+", "", t, flags=re.I)
        # strip explicit room mentions
        if room:
            for nm in [room.get("id"), room.get("name")] + list(room.get("aliases") or []):
                nm = str(nm or "").strip()
                if len(nm) >= 3:
                    t = re.sub(rf"\b(в|во|на)\s+{re.escape(nm)}\b", " ", t, flags=re.I)
                    t = re.sub(rf"\b{re.escape(nm)}\b", " ", t, flags=re.I)
        t = _strip_room_phrases(t)
        t = re.sub(r"\s+", " ", t).strip(" ,.-")
        # if only generic word left
        if t.lower() in ("музыка", "музыку", "что-нибудь", "что нибудь", "любую", ""):
            return ""
        return t

    def _handle_media(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        err = self._require_ha()
        if err:
            return err
        t = (intent.raw or "").lower()
        room = self._current_room(intent, ctx)
        room_name = str(room.get("name") or room.get("id") or "комната")
        player = self._resolve_room_media_player(room, intent.raw)

        # volume up/down
        if "громче" in t or "прибав" in t and "громк" in t:
            if not player:
                return self._no_player(room_name)
            res = self.ha.call_service("media_player", "volume_up", {"entity_id": player})
            if res.ok:
                return SkillResponse(text=f"Сделал громче в {room_name} ({player}).", data={"entity_id": player, "action": "volume_up", "room": room_summary(room)})
            return self._svc_err(res)
        if "тише" in t or ("убав" in t and "громк" in t) or ("уменьш" in t and "громк" in t):
            if not player:
                return self._no_player(room_name)
            res = self.ha.call_service("media_player", "volume_down", {"entity_id": player})
            if res.ok:
                return SkillResponse(text=f"Сделал тише в {room_name} ({player}).", data={"entity_id": player, "action": "volume_down", "room": room_summary(room)})
            return self._svc_err(res)

        # transport
        if re.search(r"\b(пауза|приостанов)\b", t):
            if not player:
                return self._no_player(room_name)
            res = self.ha.call_service("media_player", "media_pause", {"entity_id": player})
            if res.ok:
                return SkillResponse(text=f"Пауза в {room_name}.", data={"entity_id": player, "action": "pause", "room": room_summary(room)})
            return self._svc_err(res)
        if re.search(r"\b(продолжи|play|играй дальше)\b", t) and "включи" not in t:
            if not player:
                return self._no_player(room_name)
            res = self.ha.call_service("media_player", "media_play", {"entity_id": player})
            if res.ok:
                return SkillResponse(text=f"Продолжаю воспроизведение в {room_name}.", data={"entity_id": player, "action": "play", "room": room_summary(room)})
            return self._svc_err(res)
        if re.search(r"\b(следующ|next)\b", t):
            if not player:
                return self._no_player(room_name)
            res = self.ha.call_service("media_player", "media_next_track", {"entity_id": player})
            if res.ok:
                return SkillResponse(text=f"Следующий трек в {room_name}.", data={"entity_id": player, "action": "next", "room": room_summary(room)})
            return self._svc_err(res)
        if re.search(r"\b(предыдущ|назад|previous)\b", t):
            if not player:
                return self._no_player(room_name)
            res = self.ha.call_service("media_player", "media_previous_track", {"entity_id": player})
            if res.ok:
                return SkillResponse(text=f"Предыдущий трек в {room_name}.", data={"entity_id": player, "action": "previous", "room": room_summary(room)})
            return self._svc_err(res)
        if re.search(r"\b(выключи|останови|стоп|stop)\b", t) and any(w in t for w in ("музык", "трек", "песн", "плеер", "колонк", "воспроизвед", "радио", "медиа")):
            if not player:
                return self._no_player(room_name)
            # try stop then turn_off fallback
            res = self.ha.call_service("media_player", "media_stop", {"entity_id": player})
            if not res.ok:
                res = self.ha.call_service("media_player", "turn_off", {"entity_id": player})
            if res.ok:
                return SkillResponse(text=f"Остановил воспроизведение в {room_name}.", data={"entity_id": player, "action": "stop", "room": room_summary(room)})
            return self._svc_err(res)

        # play / start music
        if any(w in t for w in ("включи", "запусти", "поставь", "воспроизведи", "играй", "проиграй", "сыграй", "музык", "трек", "песн", "плейлист", "радио", "альбом")):
            if not player:
                return self._no_player(room_name)
            query = self._extract_media_query(intent.raw, room)
            if not query:
                # resume/play
                res = self.ha.call_service("media_player", "media_play", {"entity_id": player})
                if not res.ok:
                    res = self.ha.call_service("media_player", "turn_on", {"entity_id": player})
                if res.ok:
                    return SkillResponse(
                        text=f"Включаю воспроизведение в {room_name} ({player}).",
                        data={"entity_id": player, "action": "play", "room": room_summary(room), "target_player": player},
                    )
                return self._svc_err(res)

            # try best-effort playback services for HA / Music Assistant compatibility
            attempts = []
            ma_cfg = (self.cfg.get("music") or {}).get("music_assistant") or {}
            prefer_ma = bool(ma_cfg.get("enabled")) or bool(room.get("music_assistant"))
            # Music Assistant services (domain names vary by HA/MA version; try common ones)
            ma_domains = ["music_assistant", "mass"]
            if prefer_ma:
                for dom in ma_domains:
                    attempts.append((dom, "play_media", {"entity_id": player, "media_id": query, "media_type": "track", "enqueue": "play"}))
                    attempts.append((dom, "play_media", {"entity_id": player, "media_id": query, "media_type": "playlist", "enqueue": "play"}))
                    attempts.append((dom, "play_media", {"entity_id": player, "media_id": query, "media_type": "radio", "enqueue": "play"}))
            # standard HA media_player
            attempts.extend([
                ("media_player", "play_media", {"entity_id": player, "media_content_id": query, "media_content_type": "music"}),
                ("media_player", "play_media", {"entity_id": player, "media_content_id": query, "media_content_type": "playlist"}),
                ("media_player", "play_media", {"entity_id": player, "media_content_id": query, "media_content_type": "track"}),
                ("media_player", "play_media", {"entity_id": player, "media_content_id": query, "media_content_type": "channel"}),
            ])
            if not prefer_ma:
                for dom in ma_domains:
                    attempts.append((dom, "play_media", {"entity_id": player, "media_id": query, "media_type": "track", "enqueue": "play"}))
            last_err = None
            for dom, svc, payload in attempts:
                res = self.ha.call_service(dom, svc, payload)
                if res.ok:
                    return SkillResponse(
                        text=f"Запускаю «{query}» в {room_name} ({player}).",
                        data={
                            "entity_id": player, "action": "play_media", "query": query,
                            "service": f"{dom}.{svc}", "room": room_summary(room), "target_player": player,
                        },
                    )
                last_err = res
            # if all failed, report useful hint
            err_msg = (last_err.error if last_err else "неизвестная ошибка")
            return SkillResponse(
                text=(
                    f"Не удалось запустить «{query}» в {room_name} ({player}) через Home Assistant: {err_msg}. "
                    "Проверьте, что media_player поддерживает воспроизведение по имени/URL, или настройте Music Assistant "
                    "и укажите предпочтительный сервис/плеер в config (rooms[].media_player, music.music_assistant.enabled)."
                ),
                data={"entity_id": player, "query": query, "error": err_msg, "room": room_summary(room), "target_player": player},
            )

        return SkillResponse(text=f"Не распознал медиа-команду для {room_name}. Скажите: «включи музыку», «пауза», «громче/тише».", data={"room": room_summary(room)})

    def _no_player(self, room_name: str) -> SkillResponse:
        return SkillResponse(
            text=(
                f"Для комнаты «{room_name}» не найден media_player. "
                "Укажите entity_id в config/config.local.json (rooms[].media_player) "
                "и убедитесь, что устройство доступно в Home Assistant."
            ),
            data={"room": room_name, "missing": "media_player"},
        )

    def _svc_err(self, res) -> SkillResponse:
        return SkillResponse(text=f"Ошибка Home Assistant: {res.error or res.status}", data={"ok": False, "status": res.status, "error": res.error})

    def _handle_query(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        err = self._require_ha()
        if err:
            return err
        t = intent.raw.lower()
        # temperature/humidity quick template
        if "температур" in t or "влажност" in t:
            guess = self._entity_name_guess(intent.raw)
            ent = self.ha.resolve_entity(guess or "температур", domains=["sensor", "climate"], prefer_room=(ctx.slots.get("room_name") or ""))
            if ent:
                eid = ent.get("entity_id")
                st = self.ha.get_state(eid)
                if st.ok and isinstance(st.data, dict):
                    attrs = st.data.get("attributes") or {}
                    name = attrs.get("friendly_name") or eid
                    state = st.data.get("state")
                    unit = attrs.get("unit_of_measurement") or ""
                    return SkillResponse(text=f"{name}: {state} {unit}".strip(), data={"entity_id": eid, "state": st.data})
            # fallback: search sensors
            sensors = self.ha.find_entities(query=guess or "temperature", domain="sensor")[:5]
            if sensors:
                lines = []
                for s in sensors:
                    attrs = s.get("attributes") or {}
                    lines.append(f"• {attrs.get('friendly_name') or s.get('entity_id')}: {s.get('state')} {attrs.get('unit_of_measurement','')}".strip())
                return SkillResponse(text="Найденные датчики:\n" + "\n".join(lines), data={"entities": [s.get('entity_id') for s in sensors]})
            return SkillResponse(text="Не нашёл подходящий датчик температуры/влажности в Home Assistant. Уточните название или комнату.")

        # generic state query
        guess = self._entity_name_guess(intent.raw)
        ents = self.ha.find_entities(query=guess) if guess else self.ha.find_entities()[:10]
        if not ents:
            return SkillResponse(text="Не нашёл подходящих сущностей в Home Assistant. Уточните устройство/датчик.")
        lines = []
        for e in ents[:8]:
            attrs = e.get("attributes") or {}
            lines.append(f"• {attrs.get('friendly_name') or e.get('entity_id')} ({e.get('entity_id')}): {e.get('state')}")
        return SkillResponse(text="Состояния из Home Assistant:\n" + "\n".join(lines), data={"entities": [e.get("entity_id") for e in ents[:8]]})

    def _handle_control(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        err = self._require_ha()
        if err:
            return err
        text = intent.raw
        t = text.lower()
        # determine action
        if _contains_any(t, OFF_WORDS):
            action = "turn_off"
        elif _contains_any(t, TOGGLE_WORDS):
            action = "toggle"
        elif _contains_any(t, ON_WORDS):
            action = "turn_on"
        else:
            action = "turn_on"

        room = self._current_room(intent, ctx)
        room_name = str(room.get("name") or room.get("id") or "")
        guess = self._entity_name_guess(text)
        domains = self._domain_guess(text)
        # if "свет в этой комнате" and no specific guess - try by room in domain light
        ent = self.ha.resolve_entity(guess or room_name, domains=domains, prefer_room=room_name)
        if not ent and room_name:
            ent = self.ha.resolve_entity(room_name, domains=domains, prefer_room=room_name)
        if not ent:
            # provide helpful candidates
            cands = self.ha.find_entities(query=guess or room_name)[:5]
            if cands:
                opts = ", ".join([str(c.get("entity_id")) for c in cands])
                return SkillResponse(
                    text=f"Не удалось однозначно определить устройство в Home Assistant. Похожие сущности: {opts}. Уточните название/комнату.",
                    data={"candidates": [c.get("entity_id") for c in cands], "room": room_summary(room)},
                )
            return SkillResponse(text="Не нашёл устройство в Home Assistant для этой команды. Уточните название и комнату.", data={"room": room_summary(room)})

        entity_id = str(ent.get("entity_id"))
        domain = entity_id.split(".", 1)[0]
        # map action for some domains
        service = action
        payload = {"entity_id": entity_id}
        if domain in ("scene", "script"):
            service = "turn_on"
        if domain == "cover" and action in ("turn_on", "turn_off"):
            service = "open_cover" if action == "turn_on" else "close_cover"

        res = self.ha.call_service(domain, service, payload)
        attrs = ent.get("attributes") or {}
        fname = attrs.get("friendly_name") or entity_id
        if res.ok:
            act_ru = {"turn_on": "включил", "turn_off": "выключил", "toggle": "переключил", "open_cover": "открыл", "close_cover": "закрыл"}.get(service, service)
            return SkillResponse(
                text=f"Готово: {act_ru} {fname} ({entity_id})" + (f" в {room_name}." if room_name else "."),
                data={"entity_id": entity_id, "service": f"{domain}.{service}", "room": room_summary(room), "result": res.data},
            )
        return self._svc_err(res)
