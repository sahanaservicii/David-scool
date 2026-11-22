from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


GENERIC_ROOM_TOKENS = {
    "здесь", "тут", "в этой комнате", "в комнате", "сюда",
    "home", "here", "this room",
}


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _room_texts(room: Dict[str, Any]) -> List[str]:
    vals = [room.get("id"), room.get("name")]
    aliases = room.get("aliases") or []
    if isinstance(aliases, (list, tuple)):
        vals.extend(aliases)
    sat = room.get("satellite")
    if isinstance(sat, dict):
        vals.extend([sat.get("id"), sat.get("name")])
    elif sat:
        vals.append(sat)
    out = []
    for v in vals:
        n = _norm(v)
        if n and n not in out:
            out.append(n)
    return out


def normalize_room(room: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    r = dict(room or {})
    rid = str(r.get("id") or r.get("name") or f"room_{index+1}").strip()
    r["id"] = rid
    r["name"] = str(r.get("name") or rid).strip()
    aliases = r.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    r["aliases"] = [str(a).strip() for a in aliases if str(a).strip()]
    # satellite can be string id or object; also accept satellite_id field
    sat = r.get("satellite")
    sat_id = str(r.get("satellite_id") or "").strip()
    if isinstance(sat, str):
        sat_s = sat.strip()
        r["satellite"] = sat_s or ""
        r["satellite_id"] = sat_s or sat_id
    elif isinstance(sat, dict):
        sid = str(sat.get("id") or sat.get("name") or sat_id or "").strip()
        sat2 = dict(sat)
        if sid:
            sat2["id"] = sid
        r["satellite"] = sat2
        r["satellite_id"] = sid
    else:
        r["satellite"] = ""
        r["satellite_id"] = sat_id
    # media/tts targets
    for k in ("media_player", "tts_player", "announce_player", "speaker", "microphone"):
        if r.get(k) is None:
            r[k] = ""
        elif not isinstance(r[k], str):
            r[k] = str(r[k])
    return r


def normalize_rooms(rooms: Any) -> List[Dict[str, Any]]:
    if not isinstance(rooms, list):
        return []
    out = []
    for i, r in enumerate(rooms):
        if isinstance(r, dict):
            out.append(normalize_room(r, i))
    return out


def default_room(rooms: List[Dict[str, Any]]) -> Dict[str, Any]:
    if rooms:
        return rooms[0]
    return normalize_room({"id": "default", "name": "Дом", "aliases": ["здесь", "тут", "дом"]}, 0)


def find_room_by_id(rooms: List[Dict[str, Any]], room_id: Any) -> Optional[Dict[str, Any]]:
    rid = _norm(room_id)
    if not rid:
        return None
    for r in rooms:
        if _norm(r.get("id")) == rid:
            return r
    return None


def find_room_by_satellite(rooms: List[Dict[str, Any]], satellite_id: Any) -> Optional[Dict[str, Any]]:
    sid = _norm(satellite_id)
    if not sid:
        return None
    for r in rooms:
        if _norm(r.get("satellite_id")) == sid:
            return r
        sat = r.get("satellite")
        if isinstance(sat, dict):
            if _norm(sat.get("id")) == sid or _norm(sat.get("name")) == sid:
                return r
    return None


def _contains_token(hay: str, needle: str) -> bool:
    if not needle:
        return False
    # exact/substring match
    if needle in hay:
        return True
    # word-ish boundary match for short aliases
    if len(needle) <= 2:
        return re.search(rf"(^|\W){re.escape(needle)}(\W|$)", hay) is not None
    # fuzzy prefix match for inflected names/aliases (e.g. гостиная/гостиной)
    if len(needle) >= 5:
        pref = needle[: max(4, len(needle) - 2)]
        if pref and pref in hay:
            return True
    # token prefix overlap
    htokens = [t for t in re.split(r"[^\wа-яё]+", hay, flags=re.I) if t]
    for ht in htokens:
        if len(ht) >= 4 and len(needle) >= 4 and (ht.startswith(needle[:4]) or needle.startswith(ht[:4])):
            # require reasonable common prefix length
            common = 0
            for a, b in zip(ht, needle):
                if a != b:
                    break
                common += 1
            if common >= 4:
                return True
    return False


def resolve_room(
    rooms: List[Dict[str, Any]],
    hint: Any = None,
    text: Any = None,
    context_room_id: Any = None,
    satellite_id: Any = None,
) -> Dict[str, Any]:
    rooms = normalize_rooms(rooms)
    d = default_room(rooms)

    # explicit satellite binding
    sat_room = find_room_by_satellite(rooms, satellite_id)
    if sat_room:
        return sat_room

    # explicit/context id
    by_ctx = find_room_by_id(rooms, context_room_id)
    by_hint = find_room_by_id(rooms, hint)
    if by_hint:
        return by_hint
    if by_ctx and not hint and not text:
        return by_ctx

    hint_n = _norm(hint)
    text_n = _norm(text)
    combined = " ".join(x for x in [hint_n, text_n] if x).strip()

    # hint may be name/alias
    if hint_n:
        for r in rooms:
            for t in _room_texts(r):
                if hint_n == t or _contains_token(hint_n, t):
                    return r

    # text-based resolution (prefer longer/more specific names)
    if text_n:
        candidates: List[Tuple[int, Dict[str, Any]]] = []
        for r in rooms:
            for t in _room_texts(r):
                if not t or t in GENERIC_ROOM_TOKENS:
                    continue
                if _contains_token(text_n, t):
                    candidates.append((len(t), r))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]

    # "здесь/в этой комнате" -> context room
    if combined:
        for tok in GENERIC_ROOM_TOKENS:
            if tok in combined and by_ctx:
                return by_ctx

    if by_ctx:
        return by_ctx
    return d


def room_summary(room: Dict[str, Any]) -> Dict[str, Any]:
    r = normalize_room(room)
    sat = r.get("satellite")
    sat_id = r.get("satellite_id") or (sat.get("id") if isinstance(sat, dict) else sat) or ""
    return {
        "id": r.get("id"),
        "name": r.get("name"),
        "aliases": r.get("aliases") or [],
        "media_player": r.get("media_player") or "",
        "tts_player": r.get("tts_player") or r.get("announce_player") or "",
        "satellite_id": sat_id,
        "microphone": r.get("microphone") or "",
        "speaker": r.get("speaker") or "",
    }
