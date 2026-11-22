from __future__ import annotations
import json
import mimetypes
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from ..core.engine import AssistantEngine

STATIC_DIR = Path(__file__).resolve().parent / 'static'


def _client_ip(headers) -> str:
    xff = headers.get('X-Forwarded-For', '')
    if xff:
        return xff.split(',')[0].strip()
    return ''


def make_handler(engine: AssistantEngine):
    srv_cfg = engine.cfg.get('server', {}) or {}
    cors_origin = str(srv_cfg.get('cors_allow_origin') or '*')
    api_token = str(srv_cfg.get('api_token') or '').strip()
    require_token_lan = bool((engine.cfg.get('security') or {}).get('require_api_token_for_lan'))

    class Handler(BaseHTTPRequestHandler):
        server_version = "FreeVoice/0.2"

        def _send(self, code, body: bytes, content_type='text/plain; charset=utf-8'):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', cors_origin)
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Api-Token')
            self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
            self._send(code, body, 'application/json; charset=utf-8')

        def _check_auth(self):
            if not api_token:
                return True
            # optional: require token only for LAN; but if token set and require_token_lan False, require always for API mutations?
            # Simple policy: if token configured, require for POST APIs.
            auth = self.headers.get('Authorization', '')
            hdr = self.headers.get('X-Api-Token', '')
            token = ''
            if auth.lower().startswith('bearer '):
                token = auth[7:].strip()
            elif hdr:
                token = hdr.strip()
            return token == api_token

        def do_OPTIONS(self):
            self._send(HTTPStatus.NO_CONTENT, b'')

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            qs = parse_qs(parsed.query or '', keep_blank_values=True)
            def q1(name, default=''):
                v = qs.get(name)
                if not v:
                    return default
                return v[0]
            if path == '/api/status':
                quick = True
                # allow full probe via ?quick=0 if explicitly requested
                if q1('quick', '1') in ('0', 'false', 'no') or q1('full', '0') in ('1', 'true', 'yes'):
                    quick = False
                return self._json(200, engine.status(quick=quick))
            if path == '/api/health':
                # lightweight: no network probes
                ha_cfg = (engine.cfg.get('home_assistant') or {})
                ha_url = ha_cfg.get('url') or engine.ha.base_url
                return self._json(200, {
                    'ok': True,
                    'version': engine.VERSION,
                    'name': engine.cfg.get('app', {}).get('name'),
                    'skills': len(engine.registry.by_name),
                    'llm_configured': bool((engine.cfg.get('llm', {}).get('openai_compat') or {}).get('base_url')),
                    'ha_configured': bool(ha_url),
                })
            if path == '/api/rooms':
                try:
                    from ..core.rooms import room_summary
                    rooms = [room_summary(r) for r in engine.rooms()]
                except Exception:
                    rooms = engine.rooms()
                return self._json(200, {'rooms': rooms})
            if path == '/api/music' or path == '/api/music/status':
                room_id = q1('room', '')
                try:
                    return self._json(200, engine.music_status(room_id=room_id))
                except Exception:
                    return self._json(500, {'error': 'internal error'})
            if path == '/api/music/config':
                try:
                    try:
                        from ..core.rooms import room_summary
                        rooms = [room_summary(r) for r in engine.rooms()]
                    except Exception:
                        rooms = engine.rooms()
                    return self._json(200, {'ok': True, 'config': engine.music_config(), 'rooms': rooms})
                except Exception:
                    return self._json(500, {'error': 'internal error'})
            if path == '/api/config':
                cfg = engine.cfg
                safe = {
                    'app': cfg.get('app', {}),
                    'stt': {'provider': cfg.get('stt', {}).get('provider'), 'language': cfg.get('stt', {}).get('language')},
                    'tts': {'provider': cfg.get('tts', {}).get('provider'), 'voice': cfg.get('tts', {}).get('voice')},
                    'llm': {'provider': cfg.get('llm', {}).get('provider')},
                    'rooms': [{'id': r.get('id'), 'name': r.get('name')} for r in engine.rooms()],
                    'home_assistant': {'configured': bool((cfg.get('home_assistant') or {}).get('url') or (cfg.get('home_assistant') or {}).get('secrets_file'))},
                }
                return self._json(200, safe)
            # friendly aliases
            if path == '/music':
                path = '/music.html'
            # static files
            if path == '/':
                path = '/index.html'
            fs_path = (STATIC_DIR / path.lstrip('/')).resolve()
            try:
                fs_path.relative_to(STATIC_DIR.resolve())
            except Exception:
                return self._send(403, b'Forbidden')
            if fs_path.is_dir():
                fs_path = fs_path / 'index.html'
            if not fs_path.exists():
                return self._send(404, b'Not found')
            ctype = mimetypes.guess_type(str(fs_path))[0] or 'application/octet-stream'
            try:
                data = fs_path.read_bytes()
            except Exception:
                return self._send(500, b'Read error')
            return self._send(200, data, ctype)

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path == '/api/chat':
                if not self._check_auth():
                    return self._json(401, {'error': 'unauthorized'})
                try:
                    n = int(self.headers.get('Content-Length', '0') or '0')
                except Exception:
                    n = 0
                if n < 0 or n > 65536:
                    return self._json(413, {'error': 'payload too large'})
                try:
                    raw = self.rfile.read(n) if n > 0 else b'{}'
                    payload = json.loads(raw.decode('utf-8', errors='replace') or '{}')
                except Exception:
                    return self._json(400, {'error': 'invalid json'})
                text = (payload.get('text') or payload.get('message') or '')
                if not isinstance(text, str):
                    text = str(text)
                text = text.strip()
                session = payload.get('session_id') or 'web'
                if not isinstance(session, str):
                    session = 'web'
                session = session[:64]
                room = payload.get('room') or payload.get('room_id') or ''
                if not isinstance(room, str):
                    room = str(room)
                room = room[:64]
                satellite_id = payload.get('satellite_id') or payload.get('satellite') or ''
                if not isinstance(satellite_id, str):
                    satellite_id = str(satellite_id)
                satellite_id = satellite_id[:64]
                if not text:
                    return self._json(400, {'error': 'text required'})
                if len(text) > 4000:
                    text = text[:4000]
                try:
                    meta = {'client': 'web'}
                    if room:
                        meta['room'] = room
                    if satellite_id:
                        meta['satellite_id'] = satellite_id
                        meta['client'] = 'satellite'
                    res = engine.process(text, session_id=session, meta=meta)
                    return self._json(200, res)
                except Exception:
                    return self._json(500, {'error': 'internal error'})
            if parsed.path == '/api/music':
                if not self._check_auth():
                    return self._json(401, {'error': 'unauthorized'})
                try:
                    n = int(self.headers.get('Content-Length', '0') or '0')
                except Exception:
                    n = 0
                if n < 0 or n > 65536:
                    return self._json(413, {'error': 'payload too large'})
                try:
                    raw = self.rfile.read(n) if n > 0 else b'{}'
                    payload = json.loads(raw.decode('utf-8', errors='replace') or '{}')
                except Exception:
                    return self._json(400, {'error': 'invalid json'})
                if not isinstance(payload, dict):
                    return self._json(400, {'error': 'invalid payload'})
                action = str(payload.get('action') or payload.get('command') or '').strip()
                room = payload.get('room') or payload.get('room_id') or ''
                if not isinstance(room, str):
                    room = str(room)
                room = room[:64]
                if not action:
                    return self._json(400, {'error': 'action required'})
                try:
                    res = engine.music_control(action, room_id=room, payload=payload)
                    code = 200 if res.get('ok') else 400
                    # map some errors to better codes
                    err = res.get('error')
                    if err in ('ha_unreachable', 'ha_error'):
                        code = 503
                    return self._json(code, res)
                except Exception:
                    return self._json(500, {'error': 'internal error'})
            if parsed.path == '/api/satellite':
                if not self._check_auth():
                    return self._json(401, {'error': 'unauthorized'})
                try:
                    n = int(self.headers.get('Content-Length', '0') or '0')
                except Exception:
                    n = 0
                if n < 0 or n > 65536:
                    return self._json(413, {'error': 'payload too large'})
                try:
                    raw = self.rfile.read(n) if n > 0 else b'{}'
                    payload = json.loads(raw.decode('utf-8', errors='replace') or '{}')
                except Exception:
                    return self._json(400, {'error': 'invalid json'})
                if not isinstance(payload, dict):
                    return self._json(400, {'error': 'invalid payload'})
                event_type = str(payload.get('type') or payload.get('event') or 'utterance').strip().lower()
                satellite_id = payload.get('satellite_id') or payload.get('satellite') or ''
                if not isinstance(satellite_id, str):
                    satellite_id = str(satellite_id)
                satellite_id = satellite_id[:64]
                room = payload.get('room') or payload.get('room_id') or ''
                if not isinstance(room, str):
                    room = str(room)
                room = room[:64]
                session = payload.get('session_id') or (f'sat-{satellite_id}' if satellite_id else 'satellite')
                if not isinstance(session, str):
                    session = str(session)
                session = session[:64]
                if event_type in ('ping', 'hello', 'status'):
                    try:
                        from ..core.rooms import resolve_room as resolve_room_config, room_summary, normalize_rooms
                        rooms = normalize_rooms(engine.rooms())
                        r = resolve_room_config(rooms, hint=room, satellite_id=satellite_id)
                        return self._json(200, {
                            'ok': True,
                            'type': event_type,
                            'version': engine.VERSION,
                            'satellite_id': satellite_id or None,
                            'room': room_summary(r) if r else None,
                            'tts': {'provider': engine.tts.name},
                            'stt': {'provider': engine.stt.name},
                        })
                    except Exception:
                        return self._json(500, {'error': 'internal error'})
                # default: utterance with text
                text = (payload.get('text') or payload.get('transcript') or payload.get('utterance') or '')
                if not isinstance(text, str):
                    text = str(text)
                text = text.strip()
                if not text:
                    return self._json(400, {'error': 'text required for utterance'})
                if len(text) > 4000:
                    text = text[:4000]
                try:
                    meta = {'client': 'satellite', 'event': event_type}
                    if room:
                        meta['room'] = room
                    if satellite_id:
                        meta['satellite_id'] = satellite_id
                    res = engine.process(text, session_id=session, meta=meta)
                    # add satellite-friendly hints
                    room_info = res.get('room') or {}
                    tts_target = room_info.get('tts_player') or room_info.get('media_player') or ''
                    res['satellite_hints'] = {
                        'speak': True,
                        'tts_target_player': tts_target,
                        'media_target_player': room_info.get('media_player') or '',
                        'room_id': room_info.get('id'),
                    }
                    return self._json(200, res)
                except Exception:
                    return self._json(500, {'error': 'internal error'})
            return self._json(404, {'error': 'not found'})

        def log_message(self, fmt, *args):
            if os.getenv('ASSISTANT_VERBOSE'):
                super().log_message(fmt, *args)

    return Handler


def run_server(host='127.0.0.1', port=8765, config_path=None):
    engine = AssistantEngine(config_path)
    handler = make_handler(engine)
    cfg_srv = engine.cfg.get('server', {}) or {}
    if cfg_srv.get('allow_lan') and host == '127.0.0.1':
        host = '0.0.0.0'
    httpd = ThreadingHTTPServer((host, int(port)), handler)
    print(f"FreeVoice v{engine.VERSION} web UI: http://{host}:{port}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == '__main__':
    run_server()
