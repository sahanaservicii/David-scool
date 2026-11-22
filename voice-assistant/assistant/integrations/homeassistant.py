from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _parse_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        if not path.exists():
            return out
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k:
                out[k] = v
    except Exception:
        return out
    return out


def _normalize_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if url and not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    return url


@dataclass
class HAResult:
    ok: bool
    status: int = 0
    data: Any = None
    error: str = ""


class HomeAssistantClient:
    def __init__(self, base_url: str, token: str = "", timeout: int = 8, verify: bool = True):
        self.base_url = _normalize_url(base_url)
        self.token = (token or "").strip()
        self.timeout = timeout
        self.verify = verify
        self._states_cache: List[Dict[str, Any]] = []
        self._states_cache_ts: float = 0.0
        self._states_cache_ttl: float = 15.0

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            h["Authorization"] = "Bearer " + self.token
        return h

    def request(self, method: str, path: str, payload: Any = None) -> HAResult:
        if not self.base_url:
            return HAResult(False, 0, None, "Home Assistant URL не настроен")
        url = self.base_url + path
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read()
                ctype = (r.headers.get("Content-Type") or "").lower()
                if "application/json" in ctype or raw.strip().startswith((b"{", b"[")):
                    try:
                        body = json.loads(raw.decode("utf-8", errors="replace") or "null")
                    except Exception:
                        body = raw.decode("utf-8", errors="replace")
                else:
                    body = raw.decode("utf-8", errors="replace")
                return HAResult(True, getattr(r, "status", 200), body, "")
        except urllib.error.HTTPError as e:
            try:
                raw = e.read().decode("utf-8", errors="replace")
            except Exception:
                raw = str(e)
            msg = raw[:500]
            if e.code in (401, 403):
                msg = f"Нет доступа к Home Assistant ({e.code}). Проверьте HASS_TOKEN."
            return HAResult(False, e.code, None, msg)
        except Exception as e:
            return HAResult(False, 0, None, str(e))

    def ping(self) -> HAResult:
        # /api/ without auth sometimes returns 401 but indicates HA is up; with auth returns message
        res = self.request("GET", "/api/")
        if not res.ok and res.status in (401, 403) and self.base_url:
            return HAResult(True, res.status, {"message": "HA доступен, требуется токен"}, "")
        return res

    def get_config(self) -> HAResult:
        return self.request("GET", "/api/config")

    def get_states(self, force: bool = False) -> HAResult:
        now = time.time()
        if not force and self._states_cache and (now - self._states_cache_ts) < self._states_cache_ttl:
            return HAResult(True, 200, self._states_cache, "")
        res = self.request("GET", "/api/states")
        if res.ok and isinstance(res.data, list):
            self._states_cache = res.data
            self._states_cache_ts = now
        return res

    def get_state(self, entity_id: str) -> HAResult:
        eid = urllib.parse.quote(entity_id, safe="")
        return self.request("GET", f"/api/states/{eid}")

    def call_service(self, domain: str, service: str, data: Optional[Dict[str, Any]] = None) -> HAResult:
        res = self.request("POST", f"/api/services/{domain}/{service}", data or {})
        # invalidate cache on state-changing calls
        self._states_cache_ts = 0.0
        return res

    def render_template(self, template: str) -> HAResult:
        return self.request("POST", "/api/template", {"template": template})

    def check_config(self) -> HAResult:
        return self.request("POST", "/api/config/core/check_config", {})

    def safe_status(self, quick: bool = True) -> Dict[str, Any]:
        old_timeout = self.timeout
        try:
            if quick:
                self.timeout = min(self.timeout, 2)
            ping = self.ping()
            out = {
                "configured": bool(self.base_url),
                "url": self.base_url or None,
                "has_token": bool(self.token),
                "reachable": bool(ping.ok),
                "status_code": ping.status,
            }
            if ping.ok and ping.status == 200:
                # avoid extra request in quick mode? config gives nice info but costs time
                if not quick:
                    cfg = self.get_config()
                    if cfg.ok and isinstance(cfg.data, dict):
                        out["location_name"] = cfg.data.get("location_name")
                        out["version"] = cfg.data.get("version")
                else:
                    if isinstance(ping.data, dict):
                        out["message"] = ping.data.get("message")
            elif not ping.ok:
                out["error"] = ping.error
            return out
        finally:
            self.timeout = old_timeout

    # --- helpers for intent resolution ---
    def find_entities(self, query: str = "", domain: str = "", area: str = "") -> List[Dict[str, Any]]:
        st = self.get_states()
        items = st.data if st.ok and isinstance(st.data, list) else []
        q = (query or "").strip().lower()
        area_q = (area or "").strip().lower()
        out = []
        for e in items:
            eid = str(e.get("entity_id", ""))
            if domain and not eid.startswith(domain + "."):
                continue
            attrs = e.get("attributes") or {}
            fname = str(attrs.get("friendly_name") or "")
            hay = (eid + " " + fname).lower()
            if q and q not in hay:
                # token match
                tokens = [t for t in re.split(r"\s+", q) if t]
                if not tokens or not all(t in hay for t in tokens):
                    continue
            if area_q and area_q not in hay:
                # area can be matched via room mapping externally; keep simple contains
                pass
            score = 0
            if q and q in fname.lower():
                score += 3
            if q and q in eid.lower():
                score += 1
            e2 = dict(e)
            e2["_score"] = score
            out.append(e2)
        out.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return out

    def resolve_entity(self, query: str, domains: Optional[List[str]] = None, prefer_room: str = "") -> Optional[Dict[str, Any]]:
        domains = domains or []
        candidates: List[Dict[str, Any]] = []
        if domains:
            for d in domains:
                candidates.extend(self.find_entities(query=query, domain=d))
        else:
            candidates = self.find_entities(query=query)
        if not candidates and query:
            # fuzzy: try individual words
            words = [w for w in re.split(r"\s+", query.strip().lower()) if len(w) >= 3]
            for w in words:
                if domains:
                    for d in domains:
                        candidates.extend(self.find_entities(query=w, domain=d))
                else:
                    candidates.extend(self.find_entities(query=w))
        if prefer_room:
            room_l = prefer_room.lower()
            for c in candidates:
                eid = str(c.get("entity_id", "")).lower()
                fname = str((c.get("attributes") or {}).get("friendly_name", "")).lower()
                if room_l in eid or room_l in fname:
                    return c
        # dedupe by entity_id preserving order
        seen = set()
        uniq = []
        for c in candidates:
            eid = c.get("entity_id")
            if eid in seen:
                continue
            seen.add(eid)
            uniq.append(c)
        return uniq[0] if uniq else None


def _discover_ha_url_from_homelab() -> str:
    candidates = [
        Path(os.getenv("HOMELAB_JSON", "")) if os.getenv("HOMELAB_JSON") else None,
        Path(__file__).resolve().parents[3] / "homelab" / "homelab.json",
        Path("/root/workspace/homelab/homelab.json"),
    ]
    for p in candidates:
        try:
            if not p or not p.exists():
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            ha = data.get("home_assistant") or {}
            if ha.get("enabled") is False:
                continue
            url = ha.get("url") or ""
            if not url and ha.get("host"):
                host = str(ha.get("host"))
                port = ha.get("port") or 8123
                url = f"http://{host}:{port}"
            url = _normalize_url(str(url or ""))
            if url:
                return url
        except Exception:
            continue
    return ""


def ha_client_from_config(cfg: Dict[str, Any]) -> HomeAssistantClient:
    ha_cfg = (cfg.get("home_assistant") or {})
    # URL: env > config > homelab.json (fallback)
    url = os.getenv("HASS_URL") or os.getenv("HOME_ASSISTANT_URL") or ha_cfg.get("url") or ha_cfg.get("host") or ""
    if not url:
        url = _discover_ha_url_from_homelab()
    if url and not re.match(r"^https?://", str(url), re.I):
        # allow host:port
        if str(url).replace('.', '').replace(':', '').isdigit() or '.' in str(url):
            port = ha_cfg.get("port") or 8123
            if ":" in str(url):
                url = "http://" + str(url)
            else:
                url = f"http://{url}:{port}"
    # Token: env > config.token > secrets file
    token = os.getenv("HASS_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN") or ha_cfg.get("token") or ""
    if not token:
        secrets_path = ha_cfg.get("secrets_file") or os.getenv("HOMELAB_SECRETS_FILE") or "~/.config/opencode/secrets/homelab.env"
        try:
            envs = _parse_env_file(Path(os.path.expanduser(str(secrets_path))))
            token = envs.get("HASS_TOKEN") or envs.get("HOME_ASSISTANT_TOKEN") or ""
        except Exception:
            token = ""
    timeout = int(ha_cfg.get("timeout") or 8)
    return HomeAssistantClient(str(url or ""), str(token or ""), timeout=timeout)
