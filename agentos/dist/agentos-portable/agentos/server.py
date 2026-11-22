"""Локальный HTTP API и браузерный интерфейс. Только stdlib.

По умолчанию слушает 127.0.0.1. Доступ по токену; страница `/` — лёгкий
мобильный интерфейс без внешних CDN. Для доступа с телефона в той же сети:
`serve --host 0.0.0.0` (токен обязателен, порт наружу не пробрасывать).
"""
from __future__ import annotations

import hmac
import json
import secrets
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .core import REGISTRY, VERSION, Context, answer, load_agents, save_config

UI = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>agentos</title>
<style>
  :root{--bg:#0f1216;--card:#171c22;--line:#26303a;--fg:#e6edf3;--dim:#8b98a5;
        --acc:#4da3ff;--ok:#3fb950;--warn:#d29922;--err:#f85149}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,
       -apple-system,"Segoe UI",Roboto,sans-serif}
  header{position:sticky;top:0;background:rgba(15,18,22,.95);border-bottom:1px solid var(--line);
         padding:10px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;backdrop-filter:blur(6px)}
  header b{font-size:16px}
  .badge{font-size:12px;padding:2px 8px;border-radius:999px;border:1px solid var(--line);color:var(--dim)}
  .badge.live{color:var(--warn);border-color:var(--warn)}
  main{max-width:860px;margin:0 auto;padding:14px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;margin-bottom:12px}
  label{display:block;font-size:12px;color:var(--dim);margin-bottom:4px}
  textarea,input,select{width:100%;background:#0d1117;color:var(--fg);border:1px solid var(--line);
        border-radius:8px;padding:10px;font:inherit}
  textarea{min-height:84px;resize:vertical}
  .row{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
  button{background:var(--acc);color:#06121f;border:0;border-radius:8px;padding:10px 16px;
         font:inherit;font-weight:600;cursor:pointer}
  button.ghost{background:transparent;color:var(--dim);border:1px solid var(--line);font-weight:400}
  button:disabled{opacity:.5;cursor:default}
  pre{white-space:pre-wrap;word-break:break-word;background:#0d1117;border:1px solid var(--line);
      border-radius:8px;padding:10px;margin:8px 0 0;font:13px/1.45 ui-monospace,Consolas,monospace;min-height:44px}
  .chip{display:inline-block;margin:4px 6px 0 0;padding:4px 10px;border:1px solid var(--line);
        border-radius:999px;font-size:12px;color:var(--dim);cursor:pointer}
  .chip:hover{color:var(--fg);border-color:var(--acc)}
  .muted{color:var(--dim);font-size:12px}
  .err{color:var(--err)} .ok{color:var(--ok)}
  ul.hist{list-style:none;margin:0;padding:0}
  ul.hist li{padding:6px 0;border-bottom:1px solid var(--line);font-size:13px;cursor:pointer}
  ul.hist li:last-child{border:0}
</style>
</head>
<body>
<header>
  <b>agentos</b><span class="badge" id="agents">…</span>
  <span class="badge" id="mode">…</span>
  <span class="badge" id="llm">LLM: …</span>
</header>
<main>
  <div class="card" id="authCard" hidden>
    <label for="token">Токен (напечатан в консоли при запуске)</label>
    <div class="row" style="margin-top:0">
      <input id="token" type="password" placeholder="вставьте токен" autocomplete="off" style="flex:1;min-width:200px">
      <button id="saveToken">Сохранить</button>
    </div>
  </div>

  <div class="card">
    <label for="q">Запрос</label>
    <textarea id="q" placeholder="например: покажи arp таблицу · посчитай 2+2*10 · план дня"></textarea>
    <div class="row">
      <select id="agent" style="flex:1;min-width:200px">
        <option value="">— авто (маршрутизация по смыслу) —</option>
      </select>
      <button id="run">Выполнить</button>
    </div>
    <div class="muted" style="margin-top:6px">Ctrl+Enter — отправить</div>
  </div>

  <div class="card">
    <div class="muted" id="meta">готов</div>
    <pre id="out">Здесь появится ответ.</pre>
    <div id="alts"></div>
  </div>

  <div class="card">
    <div class="muted">Последние запросы (это браузер)</div>
    <ul class="hist" id="hist"></ul>
  </div>
</main>
<script>
const $ = id => document.getElementById(id);
const store = {
  get token(){ return localStorage.getItem("agentos-token") || ""; },
  set token(v){ v ? localStorage.setItem("agentos-token", v) : localStorage.removeItem("agentos-token"); },
  get hist(){ try { return JSON.parse(localStorage.getItem("agentos-hist")||"[]"); } catch(e){ return []; } },
  set hist(v){ localStorage.setItem("agentos-hist", JSON.stringify(v.slice(0,12))); }
};

// токен можно передать ссылкой: /?token=... — сохраняем и убираем из адреса
const url = new URL(location.href);
if (url.searchParams.get("token")) {
  store.token = url.searchParams.get("token");
  url.searchParams.delete("token");
  history.replaceState(null, "", url.pathname + url.hash);
}

async function api(path, opts = {}) {
  const headers = Object.assign({"Content-Type":"application/json"}, opts.headers || {});
  if (store.token) headers["Authorization"] = "Bearer " + store.token;
  const r = await fetch(path, Object.assign({}, opts, {headers}));
  if (r.status === 401) { $("authCard").hidden = false; throw new Error("нужен токен"); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
  return data;
}

async function loadHealth() {
  try {
    const h = await api("/health");
    $("agents").textContent = h.agents + " агентов";
    $("mode").textContent = h.dry_run ? "dry-run" : "live";
    $("mode").className = "badge" + (h.dry_run ? "" : " live");
    $("llm").textContent = "LLM: " + (h.llm ? "есть" : "нет");
  } catch (e) { $("meta").textContent = e.message; }
}

async function loadAgents() {
  try {
    const list = await api("/agents");
    const sel = $("agent");
    list.sort((a,b) => a.category.localeCompare(b.category) || a.id.localeCompare(b.id));
    for (const a of list) {
      const o = document.createElement("option");
      o.value = a.id; o.textContent = a.category + " · " + a.id + " — " + a.name;
      sel.appendChild(o);
    }
  } catch (e) { /* токен ещё не введён */ }
}

function renderHistory() {
  const ul = $("hist"); ul.innerHTML = "";
  for (const h of store.hist) {
    const li = document.createElement("li");
    li.textContent = h.agent + " · " + h.query;
    li.title = "повторить";
    li.onclick = () => { $("q").value = h.query; $("agent").value = h.agent || ""; run(); };
    ul.appendChild(li);
  }
  if (!store.hist.length) ul.innerHTML = '<li class="muted">пока пусто</li>';
}

async function run() {
  const q = $("q").value.trim();
  if (!q) return;
  $("run").disabled = true;
  $("meta").textContent = "выполняю…";
  $("out").textContent = "";
  $("alts").innerHTML = "";
  try {
    const body = {query: q};
    if ($("agent").value) body.agent = $("agent").value;
    const r = await api("/ask", {method:"POST", body: JSON.stringify(body)});
    $("meta").textContent = (r.agent || "?") + " · " + (r.ms ?? 0) + " мс · score " + (r.score ?? 0);
    $("out").textContent = r.ok ? r.output : ("Ошибка: " + (r.error || "?"));
    $("out").className = r.ok ? "" : "err";
    for (const a of (r.alternatives || [])) {
      const s = document.createElement("span");
      s.className = "chip";
      s.textContent = a.id + " · " + a.score.toFixed(2);
      s.onclick = () => { $("agent").value = a.id; run(); };
      $("alts").appendChild(s);
    }
    for (const a of (r.suggestions || [])) {
      const s = document.createElement("span");
      s.className = "chip";
      s.textContent = a.id + " · " + a.score.toFixed(2);
      s.onclick = () => { $("agent").value = a.id; run(); };
      $("alts").appendChild(s);
    }
    store.hist = [{agent: r.agent || $("agent").value || "auto", query: q}, ...store.hist];
    renderHistory();
  } catch (e) {
    $("meta").textContent = "ошибка";
    $("out").textContent = e.message;
    $("out").className = "err";
  } finally {
    $("run").disabled = false;
  }
}

$("run").onclick = run;
$("q").addEventListener("keydown", e => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); run(); }
});
$("saveToken").onclick = () => {
  store.token = $("token").value.trim();
  $("authCard").hidden = true;
  loadHealth(); loadAgents();
};
$("token").value = store.token;
$("authCard").hidden = !!store.token;
renderHistory(); loadHealth(); loadAgents();
</script>
</body>
</html>
"""


def lan_ip(ctx: Context) -> str:
    """Локальный адрес без внешних запросов: UDP-connect к шлюзу."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(0.4)
        sock.connect((ctx.cfg.get("gateway", "192.168.1.1"), 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def make_handler(ctx: Context, llm_ok: bool | None = None):
    token = ctx.cfg.get("server", {}).get("token", "")
    if llm_ok is None:
        client = getattr(ctx, "llm_client", None)
        llm_ok = bool(client and client.available)

    class Handler(BaseHTTPRequestHandler):
        server_version = "agentos"

        def _send(self, code: int, obj, *, ctype: str = "application/json; charset=utf-8") -> None:
            body = obj if isinstance(obj, bytes) else json.dumps(
                obj, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        def _auth(self) -> bool:
            given = self.headers.get("Authorization", "")
            if not given:
                qs = parse_qs(urlparse(self.path).query)
                given = f"Bearer {qs.get('token', [''])[0]}"
            return bool(token) and hmac.compare_digest(given, f"Bearer {token}")

        def _path(self) -> str:
            return urlparse(self.path).path

        def do_GET(self):
            path = self._path()
            if path in ("/", "/ui"):
                return self._send(200, UI.encode("utf-8"),
                                  ctype="text/html; charset=utf-8")
            if path == "/health":
                return self._send(200, {"ok": True, "agents": len(REGISTRY),
                                        "version": VERSION,
                                        "dry_run": ctx.dry_run,
                                        "llm": bool(llm_ok)})
            if not self._auth():
                return self._send(401, {"ok": False, "error": "unauthorized"})
            if path == "/agents":
                return self._send(200, [a.row() for a in REGISTRY.all()])
            return self._send(404, {"ok": False, "error": "unknown path"})

        def do_POST(self):
            if not self._auth():
                return self._send(401, {"ok": False, "error": "unauthorized"})
            if self._path() != "/ask":
                return self._send(404, {"ok": False, "error": "unknown path"})
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return self._send(400, {"ok": False, "error": "bad content-length"})
            if length > 64 * 1024:
                return self._send(413, {"ok": False, "error": "too large"})
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                return self._send(400, {"ok": False, "error": "bad json"})
            query = str(payload.get("query", "")).strip()
            if not query:
                return self._send(400, {"ok": False, "error": "пустой запрос"})
            res = answer(ctx, query, agent_id=payload.get("agent"))
            return self._send(200, res)

        def log_message(self, fmt, *args):
            pass

    return Handler


def serve(ctx: Context, port: int = 8765, host: str | None = None,
          open_browser: bool = False) -> int:
    load_agents()
    host = host or ctx.cfg.get("server", {}).get("host", "127.0.0.1")
    token = ctx.cfg.get("server", {}).get("token", "")
    if not token:
        token = secrets.token_urlsafe(24)
        ctx.cfg.setdefault("server", {})["token"] = token
        try:
            save_config(ctx.cfg)
        except OSError:
            pass

    client = getattr(ctx, "llm_client", None)
    llm_ok = bool(client and client.available)
    httpd = ThreadingHTTPServer((host, port), make_handler(ctx, llm_ok=llm_ok))
    local = f"http://127.0.0.1:{port}/?token={token}"
    shown = "0.0.0.0" if host in ("0.0.0.0", "::") else host
    print(f"agentos {VERSION}: http://{shown}:{port}  (API: /health, /agents, /ask)")
    if host not in ("127.0.0.1", "localhost", "::1"):
        print(f"LAN: http://{lan_ip(ctx)}:{port}/?token={token}")
        print("внимание: порт доступен всей локальной сети; токен обязателен")
    print(f"браузер: {local}")
    print(f"токен: {token}")
    if open_browser:
        try:
            webbrowser.open(local)
        except Exception:
            pass
    print("Ctrl+C — остановить")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nостановлено")
    finally:
        httpd.server_close()
    return 0
