from __future__ import annotations
import logging
import os
import uuid
from typing import Any, Dict, Optional

from .config import load_config, data_path
from .context import DialogContext
from .storage import Storage
from .rooms import normalize_rooms, resolve_room as resolve_room_config, room_summary
from ..nlu.router import IntentRouter
from ..skills.base import SkillRegistry
from ..skills.smalltalk import SmalltalkSkill
from ..skills.time_skill import TimeSkill
from ..skills.calc_skill import CalcSkill
from ..skills.notes_skill import NotesSkill
from ..skills.timer_skill import TimerSkill
from ..skills.help_skill import HelpSkill
from ..skills.system_skill import SystemSkill
from ..skills.search_skill import SearchSkill
from ..skills.weather_skill import WeatherSkill
from ..skills.homelab_skill import HomelabSkill
from ..skills.ha_skill import HomeAssistantSkill
from ..skills.web_skill import WebSkill
from ..skills.app_skill import AppControlSkill
from ..skills.fallback_skill import FallbackSkill
from ..tts.base import get_tts_provider
from ..stt.base import get_stt_provider
from ..integrations.homeassistant import ha_client_from_config

log = logging.getLogger("assistant")


def setup_logging(cfg: Dict[str, Any]):
    level_name = str(cfg.get('app', {}).get('log_level', 'INFO')).upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    else:
        root.setLevel(level)
    logging.getLogger("assistant").setLevel(level)


class AssistantEngine:
    VERSION = "0.3.0"

    def __init__(self, config_path: Optional[str] = None):
        self.cfg = load_config(config_path)
        setup_logging(self.cfg)
        self.storage = Storage(data_path(self.cfg, 'assistant.db'))
        self.router = IntentRouter()
        self.registry = SkillRegistry()
        self.tts = get_tts_provider(self.cfg)
        self.stt = get_stt_provider(self.cfg)
        self.ha = ha_client_from_config(self.cfg)
        self._sessions: Dict[str, DialogContext] = {}
        self._register_skills()

    def _register_skills(self):
        cfg, st = self.cfg, self.storage
        enabled = set(self.cfg.get('skills', {}).get('enabled', []))
        def want(name):
            return not enabled or name in enabled or name in ('smalltalk', 'help', 'fallback')
        # inject HA client into skills via cfg reference convenience
        for skill in [
            SmalltalkSkill(cfg, st), TimeSkill(cfg, st), CalcSkill(cfg, st),
            NotesSkill(cfg, st), TimerSkill(cfg, st), HelpSkill(cfg, st),
            SystemSkill(cfg, st), SearchSkill(cfg, st), WeatherSkill(cfg, st),
            HomeAssistantSkill(cfg, st), HomelabSkill(cfg, st),
            WebSkill(cfg, st), AppControlSkill(cfg, st), FallbackSkill(cfg, st),
        ]:
            if hasattr(skill, 'ha'):
                try:
                    skill.ha = self.ha  # type: ignore[attr-defined]
                except Exception:
                    pass
            if want(skill.name):
                self.registry.register(skill)

    def get_context(self, session_id: str = "default") -> DialogContext:
        if session_id not in self._sessions:
            lang = self.cfg.get('app', {}).get('language', 'ru')
            self._sessions[session_id] = DialogContext(session_id=session_id, language=lang)
        return self._sessions[session_id]

    def rooms(self):
        return normalize_rooms(self.cfg.get('rooms') or [])

    def resolve_room(self, room_hint: Optional[str], ctx: DialogContext, text: str = "", satellite_id: str = "") -> Dict[str, Any]:
        return resolve_room_config(
            self.rooms(),
            hint=room_hint or ctx.slots.get('room') or ctx.slots.get('room_id'),
            text=text,
            context_room_id=ctx.slots.get('room'),
            satellite_id=satellite_id or ctx.slots.get('satellite_id'),
        )

    def process(self, text: str, session_id: str = "default", meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        meta = dict(meta or {})
        ctx = self.get_context(session_id)
        text = (text or '').strip()
        sat_id = str(meta.get('satellite_id') or meta.get('satellite') or '')
        room = self.resolve_room(meta.get('room') or meta.get('room_id'), ctx, text=text, satellite_id=sat_id)
        if room and room.get('id'):
            ctx.slots['room'] = room.get('id')
            ctx.slots['room_name'] = room.get('name')
            ctx.slots['room_media_player'] = room.get('media_player') or ''
            ctx.slots['room_tts_player'] = room.get('tts_player') or room.get('announce_player') or ''
            if sat_id or room.get('satellite_id'):
                ctx.slots['satellite_id'] = sat_id or room.get('satellite_id')
            meta['room'] = room.get('id')
            meta['room_name'] = room.get('name')
            if room.get('media_player'):
                meta['room_media_player'] = room.get('media_player')

        ctx.add('user', text, **meta)
        if self.cfg.get('security', {}).get('log_conversations'):
            self.storage.add_history('user', text, meta)

        fired = self.storage.fire_due_timers()
        notices = []
        for t in fired:
            notices.append(f"⏰ Сработал таймер: {t.get('label') or t.get('id')}")

        intent = self.router.route(text)
        # enrich intent with room/satellite hints from entities/meta/context
        if meta.get('room'):
            intent.entities.setdefault('room', meta.get('room'))
            intent.entities.setdefault('room_id', meta.get('room'))
            intent.entities.setdefault('room_name', meta.get('room_name'))
        if meta.get('room_media_player'):
            intent.entities.setdefault('room_media_player', meta.get('room_media_player'))
        sat = sat_id or (room.get('satellite_id') if room else '') or ctx.slots.get('satellite_id') or ''
        if sat:
            intent.entities.setdefault('satellite_id', sat)
        intent.entities.setdefault('session_id', session_id)
        # pass room config snapshot for skills
        if room:
            intent.entities.setdefault('room_config', room_summary(room))

        resp = self.registry.dispatch(intent, ctx)
        if resp is None:
            resp = self.registry.get('fallback').handle(intent, ctx) if self.registry.get('fallback') else None
        if resp is None:
            from ..nlu.intents import SkillResponse
            resp = SkillResponse(text="Не удалось обработать запрос.")

        if notices:
            resp.text = "\n".join(notices) + "\n\n" + resp.text

        speak_text = resp.speak or resp.text
        ctx.add('assistant', resp.text, intent=intent.intent, skill=getattr(intent, 'skill', None))
        ctx.last_intent = intent.intent
        if self.cfg.get('security', {}).get('log_conversations'):
            self.storage.add_history('assistant', resp.text, {"intent": intent.intent, "room": meta.get('room')})

        return {
            "text": resp.text,
            "speak": speak_text,
            "intent": intent.intent,
            "skill": intent.skill,
            "confidence": intent.confidence,
            "entities": intent.entities,
            "data": resp.data,
            "session_id": session_id,
            "room": room_summary(room) if room else None,
            "satellite": {"id": sat} if sat else None,
        }


    # --- Music / multi-room control helpers (HA-backed, graceful) ---
    def music_config(self) -> Dict[str, Any]:
        music = self.cfg.get('music') or {}
        def norm(items):
            out = []
            if not isinstance(items, list):
                return out
            for i, it in enumerate(items):
                if not isinstance(it, dict):
                    continue
                out.append({
                    'id': str(it.get('id') or f'item_{i+1}'),
                    'name': str(it.get('name') or it.get('title') or it.get('id') or f'Item {i+1}'),
                    'media_content_id': str(it.get('media_content_id') or it.get('url') or it.get('uri') or ''),
                    'media_content_type': str(it.get('media_content_type') or it.get('type') or 'music'),
                    'source': str(it.get('source') or ''),
                    'image': str(it.get('image') or it.get('thumbnail') or ''),
                })
            return out
        return {
            'prefer': music.get('prefer', 'home_assistant'),
            'music_assistant': music.get('music_assistant') or {},
            'radio_presets': norm(music.get('radio_presets') or []),
            'archive_presets': norm(music.get('archive_presets') or music.get('library_presets') or []),
            'notes': music.get('notes', ''),
        }

    def music_status(self, room_id: str = '') -> Dict[str, Any]:
        cfg = self.music_config()
        rooms_out = []
        ha_reachable = False
        ha_error = ''
        try:
            ha_st = self.ha.safe_status(quick=True)
            ha_reachable = bool(ha_st.get('reachable'))
            ha_error = str(ha_st.get('error') or '')
        except Exception as e:
            ha_error = str(e)
        for r in self.rooms():
            if room_id and str(r.get('id')) != str(room_id):
                continue
            mp = str(r.get('media_player') or '').strip()
            tts = str(r.get('tts_player') or r.get('announce_player') or '').strip()
            item = {
                'room': room_summary(r),
                'media_player': mp,
                'tts_player': tts,
                'player_state': None,
                'available': bool(mp),
            }
            if mp and ha_reachable:
                try:
                    st = self.ha.get_state(mp)
                    if st.ok and isinstance(st.data, dict):
                        attrs = st.data.get('attributes') or {}
                        item['player_state'] = {
                            'entity_id': mp,
                            'state': st.data.get('state'),
                            'friendly_name': attrs.get('friendly_name') or mp,
                            'volume_level': attrs.get('volume_level'),
                            'is_volume_muted': attrs.get('is_volume_muted'),
                            'media_title': attrs.get('media_title'),
                            'media_artist': attrs.get('media_artist'),
                            'media_content_id': attrs.get('media_content_id'),
                            'source': attrs.get('source'),
                            'app_name': attrs.get('app_name'),
                        }
                    elif not st.ok:
                        item['error'] = st.error
                except Exception as e:
                    item['error'] = str(e)
            elif mp and not ha_reachable:
                item['error'] = ha_error or 'Home Assistant недоступен'
            rooms_out.append(item)
        return {
            'ok': True,
            'ha': {'reachable': ha_reachable, 'error': ha_error or None, 'url': self.ha.base_url or None},
            'rooms': rooms_out,
            'config': cfg,
        }

    def music_control(self, action: str, room_id: str = '', payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        action = str(action or '').strip().lower()
        # resolve room
        rooms = self.rooms()
        ctx_room = resolve_room_config(rooms, hint=room_id)
        room = ctx_room
        mp = str(room.get('media_player') or '').strip()
        if not mp:
            return {'ok': False, 'error': 'media_player_not_configured', 'message': f'Для комнаты «{room.get("name") or room.get("id")}» не настроен media_player.', 'room': room_summary(room)}
        # require HA
        try:
            ha_st = self.ha.safe_status(quick=True)
            if not ha_st.get('reachable') and ha_st.get('status_code') not in (401, 403):
                return {'ok': False, 'error': 'ha_unreachable', 'message': str(ha_st.get('error') or 'Home Assistant недоступен'), 'room': room_summary(room), 'entity_id': mp}
            if ha_st.get('status_code') in (401, 403) and not self.ha.token:
                return {'ok': False, 'error': 'ha_auth_required', 'message': 'Требуется токен Home Assistant.', 'room': room_summary(room), 'entity_id': mp}
        except Exception as e:
            return {'ok': False, 'error': 'ha_error', 'message': str(e), 'room': room_summary(room), 'entity_id': mp}

        res = None
        if action in ('play', 'resume', 'media_play'):
            res = self.ha.call_service('media_player', 'media_play', {'entity_id': mp})
        elif action in ('pause', 'media_pause'):
            res = self.ha.call_service('media_player', 'media_pause', {'entity_id': mp})
        elif action in ('toggle', 'play_pause', 'media_play_pause'):
            res = self.ha.call_service('media_player', 'media_play_pause', {'entity_id': mp})
        elif action in ('stop', 'media_stop'):
            res = self.ha.call_service('media_player', 'media_stop', {'entity_id': mp})
            if res and not res.ok:
                res = self.ha.call_service('media_player', 'turn_off', {'entity_id': mp})
        elif action in ('next', 'media_next', 'media_next_track'):
            res = self.ha.call_service('media_player', 'media_next_track', {'entity_id': mp})
        elif action in ('previous', 'prev', 'media_previous', 'media_previous_track'):
            res = self.ha.call_service('media_player', 'media_previous_track', {'entity_id': mp})
        elif action in ('volume_up',):
            res = self.ha.call_service('media_player', 'volume_up', {'entity_id': mp})
        elif action in ('volume_down',):
            res = self.ha.call_service('media_player', 'volume_down', {'entity_id': mp})
        elif action in ('volume_set', 'set_volume'):
            try:
                vol = float(payload.get('volume'))
            except Exception:
                vol = None
            if vol is None:
                return {'ok': False, 'error': 'bad_volume', 'message': 'volume должен быть числом 0..1 (или 0..100).', 'room': room_summary(room), 'entity_id': mp}
            if vol > 1.0:
                vol = vol / 100.0
            vol = max(0.0, min(1.0, vol))
            res = self.ha.call_service('media_player', 'volume_set', {'entity_id': mp, 'volume_level': vol})
        elif action in ('play_media', 'start', 'radio', 'archive'):
            mcid = str(payload.get('media_content_id') or payload.get('url') or payload.get('query') or '').strip()
            mct = str(payload.get('media_content_type') or payload.get('content_type') or 'music').strip() or 'music'
            if not mcid:
                return {'ok': False, 'error': 'missing_media_content_id', 'message': 'Укажите media_content_id/url или выберите пресет.', 'room': room_summary(room), 'entity_id': mp}
            attempts = []
            ma_cfg = (self.cfg.get('music') or {}).get('music_assistant') or {}
            prefer_ma = bool(ma_cfg.get('enabled')) or bool(room.get('music_assistant'))
            if prefer_ma:
                for dom in ('music_assistant', 'mass'):
                    attempts.append((dom, 'play_media', {'entity_id': mp, 'media_id': mcid, 'media_type': mct, 'enqueue': 'play'}))
            attempts.extend([
                ('media_player', 'play_media', {'entity_id': mp, 'media_content_id': mcid, 'media_content_type': mct}),
                ('media_player', 'play_media', {'entity_id': mp, 'media_content_id': mcid, 'media_content_type': 'music'}),
                ('media_player', 'play_media', {'entity_id': mp, 'media_content_id': mcid, 'media_content_type': 'channel'}),
            ])
            if not prefer_ma:
                for dom in ('music_assistant', 'mass'):
                    attempts.append((dom, 'play_media', {'entity_id': mp, 'media_id': mcid, 'media_type': mct, 'enqueue': 'play'}))
            last = None
            for dom, svc, data in attempts:
                last = self.ha.call_service(dom, svc, data)
                if last.ok:
                    return {'ok': True, 'action': action, 'service': f'{dom}.{svc}', 'room': room_summary(room), 'entity_id': mp, 'media_content_id': mcid, 'media_content_type': mct}
            err = (last.error if last else 'unknown error')
            return {'ok': False, 'error': 'play_failed', 'message': str(err), 'room': room_summary(room), 'entity_id': mp, 'media_content_id': mcid}
        else:
            return {'ok': False, 'error': 'unknown_action', 'message': f'Неизвестное действие: {action}', 'room': room_summary(room), 'entity_id': mp}

        if res and res.ok:
            return {'ok': True, 'action': action, 'room': room_summary(room), 'entity_id': mp, 'result': res.data}
        err = res.error if res else 'no result'
        return {'ok': False, 'error': 'service_failed', 'message': str(err), 'room': room_summary(room), 'entity_id': mp}


    def status(self, quick: bool = True) -> Dict[str, Any]:
        ha_status = None
        try:
            ha_status = self.ha.safe_status(quick=quick)
        except Exception:
            ha_status = {"configured": False, "reachable": False}
        return {
            "name": self.cfg.get('app', {}).get('name'),
            "version": self.VERSION,
            "language": self.cfg.get('app', {}).get('language'),
            "tts": self.tts.name,
            "stt": self.stt.name,
            "llm_provider": self.cfg.get('llm', {}).get('provider'),
            "llm_configured": bool((self.cfg.get('llm', {}).get('openai_compat') or {}).get('base_url')),
            "skills": sorted(self.registry.by_name.keys()),
            "home_assistant": ha_status,
            "rooms": [room_summary(r) for r in self.rooms()],
            "music": self.cfg.get('music', {}),
        }
