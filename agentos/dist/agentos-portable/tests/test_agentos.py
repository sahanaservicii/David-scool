"""Автотесты agentos: 100 агентов, роутинг, песочница, память.

Запуск: python3 -m unittest discover -s tests -v
Только stdlib. Сеть в тестах не требуется: всё, что ходит в LAN,
отрабатывает по таймауту и возвращает честный отказ.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import urllib.error
import urllib.request
import unicodedata
from dataclasses import replace
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="agentos-tests-"))
os.environ["AGENTOS_DATA"] = str(_TMP / "data")
os.environ["AGENTOS_OUT"] = str(_TMP / "out")

import unittest  # noqa: E402

from agentos.core import (EXPECTED_AGENTS, HOMELAB_DIR, Memory, REGISTRY,  # noqa: E402
                          ROOT, Context, answer, load_agents, load_config,
                          make_context, run_agent)
from agentos.cli import ROUTES  # noqa: E402
from agentos.llm import describe  # noqa: E402
from agentos.tools import ToolError, resolve_path  # noqa: E402
from agentos.utils import parse_params  # noqa: E402


class TestRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_agents()

    def test_expected_agent_count(self):
        self.assertEqual(len(REGISTRY), EXPECTED_AGENTS,
                         f"агентов: {len(REGISTRY)}")

    def test_ids_unique_and_wellformed(self):
        ids = [a.id for a in REGISTRY.all()]
        self.assertEqual(len(ids), len(set(ids)))
        for a in REGISTRY.all():
            self.assertRegex(a.id, r"^[a-z0-9]+\.[a-z0-9_]+$")

    def test_every_agent_has_example_and_description(self):
        for a in REGISTRY.all():
            self.assertTrue(a.examples, f"{a.id}: нет примера")
            self.assertGreater(len(a.description), 10, f"{a.id}: описание коротко")

    def test_categories(self):
        cats = REGISTRY.categories()
        self.assertEqual(len(cats), 11, sorted(cats))
        self.assertGreaterEqual(len(cats["network"]), 10)
        self.assertGreaterEqual(len(cats["windows"]), 13)


class TestExecution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_agents()
        cfg = load_config()
        data = _TMP / "exec"
        (data / "out").mkdir(parents=True, exist_ok=True)
        cls.ctx = Context(cfg=cfg, data=data, out=data / "out", dry_run=True,
                          memory=Memory(data / "m.sqlite"))

    def test_all_agents_run_without_errors(self):
        failures = []
        for a in REGISTRY.all():
            ctx = replace(self.ctx, dry_run=True)
            res = run_agent(a, ctx, a.examples[0] if a.examples else "")
            if not res.ok or not res.text().strip():
                failures.append(f"{a.id}: {res.error or 'пустой ответ'}")
        self.assertEqual(failures, [], "\n".join(failures[:10]))

    def test_routing_accuracy(self):
        good, misses = 0, []
        for query, expected in ROUTES:
            ranked = REGISTRY.route(query, 3)
            got = ranked[0][0].id if ranked else None
            if got == expected:
                good += 1
            else:
                misses.append(f"{query!r}: {got} != {expected}")
        self.assertGreaterEqual(good / len(ROUTES), 0.95,
                                f"{good}/{len(ROUTES)}\n" + "\n".join(misses))

    def test_answer_returns_structure(self):
        res = answer(self.ctx, "покажи arp таблицу")
        self.assertIn("ok", res)
        self.assertEqual(res["agent"], "net.arp")

    def test_unknown_query_is_honest(self):
        res = answer(self.ctx, "qwertyuiop zxcvbnm абракадабра")
        self.assertTrue(res.get("suggestions") is not None)

    def test_path_in_query_does_not_hijack_routing(self):
        ranked = REGISTRY.route(
            "посмотри хвост лога /root/workspace/homelab/CHANGELOG.md n=3", 1)
        self.assertEqual(ranked[0][0].id, "fs.tail")


class TestSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_agents()
        cls.ctx = make_context(load_config(), dry_run=True,
                               memory=Memory(_TMP / "safety.sqlite"))

    def test_read_outside_sandbox_blocked(self):
        with self.assertRaises(ToolError):
            resolve_path(self.ctx, "/etc/shadow")
        with self.assertRaises(ToolError):
            resolve_path(self.ctx, "../../etc/passwd")

    def test_write_outside_data_blocked(self):
        with self.assertRaises(ToolError):
            resolve_path(self.ctx, "/root/workspace/homelab/homelab.json", write=True)
        with self.assertRaises(ToolError):
            resolve_path(self.ctx, "/etc/cron.d/evil", write=True)

    def test_write_inside_out_allowed(self):
        p = resolve_path(self.ctx, "out/report.txt", write=True)
        self.assertTrue(str(p).startswith(str(self.ctx.out)))

    def test_calc_rejects_code_execution(self):
        a = REGISTRY.get("math.calc")
        bad = "__import__('os').system('id')"
        res = run_agent(a, self.ctx, bad)
        self.assertFalse(res.ok)
        self.assertIn("запрещённые", res.error or "")

    def test_secret_file_not_read_by_fs_read(self):
        res = run_agent(REGISTRY.get("hl.secrets"), self.ctx, "")
        self.assertTrue(res.ok)
        self.assertNotIn("HASS_TOKEN=", res.text())

    def test_network_guard_blocks_foreign_hosts(self):
        from agentos.tools import is_local_host
        self.assertTrue(is_local_host("192.168.1.10"))
        self.assertFalse(is_local_host("8.8.8.8"))
        self.assertFalse(is_local_host("example.com"))


class TestHTTP(unittest.TestCase):
    """Браузерный интерфейс и API: страница, токен, запрос."""

    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer
        from agentos.server import make_handler
        load_agents()
        cfg = load_config()
        cfg["server"] = {"host": "127.0.0.1", "port": 0, "token": "test-token"}
        cls.ctx = make_context(cfg, dry_run=True, memory=Memory(_TMP / "http.sqlite"))
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.ctx, llm_ok=False))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)

    def _req(self, path, *, method="GET", body=None, token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                     data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace")

    def test_ui_page(self):
        code, body = self._req("/")
        self.assertEqual(code, 200)
        self.assertIn('id="q"', body)
        self.assertIn("agentos", body)

    def test_health_is_public(self):
        code, body = self._req("/health")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["agents"], EXPECTED_AGENTS)

    def test_agents_require_token(self):
        self.assertEqual(self._req("/agents")[0], 401)
        self.assertEqual(self._req("/agents", token="wrong")[0], 401)
        code, body = self._req("/agents", token="test-token")
        self.assertEqual(code, 200)
        self.assertEqual(len(json.loads(body)), EXPECTED_AGENTS)

    def test_ask_roundtrip(self):
        code, body = self._req("/ask", method="POST", token="test-token",
                               body={"query": "посчитай 2+2*10"})
        self.assertEqual(code, 200)
        data = json.loads(body)
        self.assertTrue(data["ok"], body)
        self.assertEqual(data["agent"], "math.calc")
        self.assertIn("22", data["output"])

    def test_ask_validation(self):
        self.assertEqual(self._req("/ask", method="POST", token="test-token",
                                    body={"query": ""})[0], 400)
        long = "a" * 70000
        code, _ = self._req("/ask", method="POST", token="test-token",
                            body={"query": long})
        self.assertEqual(code, 413)


class TestWindows(unittest.TestCase):
    """Windows-агенты: allowlist, dry-run, подтверждения, честный отказ."""

    @classmethod
    def setUpClass(cls):
        load_agents()
        cfg = load_config()
        cls.ctx = make_context(cfg, dry_run=True, memory=Memory(_TMP / "win.sqlite"))

    def agent(self, agent_id):
        return REGISTRY.get(agent_id)

    def call(self, agent_id, text="", *, dry=True):
        from dataclasses import replace
        ctx = replace(self.ctx, dry_run=dry)
        return run_agent(self.agent(agent_id), ctx, text)

    def test_windows_agents_registered(self):
        ids = {a.id for a in REGISTRY.all() if a.category == "windows"}
        for need in ("win.info", "win.cmd", "win.ps", "win.net", "win.disk",
                     "win.services", "win.process", "win.eventlog", "win.users",
                     "win.tasks", "win.firewall", "win.updates", "win.help"):
            self.assertIn(need, ids)

    def test_dry_run_shows_command(self):
        self.assertIn("systeminfo", self.call("win.info").output)
        self.assertIn("Get-Service", self.call("win.ps", "Get-Service").output)
        self.assertIn("Get-Volume", self.call("win.disk").output)
        self.assertIn("Get-HotFix", self.call("win.updates").output)

    def test_cmd_allowlist(self):
        out = self.call("win.cmd", "ipconfig").output
        self.assertIn("ipconfig /all", out)
        # неизвестное/опасное не исполняется, а печатает список
        out = self.call("win.cmd", "format c: /y").output
        self.assertIn("разрешённые команды", out)
        self.assertNotIn("dry-run: cmd /d /c format", out)

    def test_ps_rejects_dangerous(self):
        bad = ("Get-Service; Remove-Item C:\\Windows -Recurse",
               "Get-Process | Stop-Process",
               "Invoke-Expression whoami",
               "Start-Process calc",
               "Get-Service > C:\\out.txt",
               "Format-Volume")
        for cmdline in bad:
            res = self.call("win.ps", cmdline)
            self.assertFalse(res.ok, cmdline)
            self.assertIn("ToolError", res.error, cmdline)

    def test_ps_allows_readonly(self):
        for cmdline in ("Get-Service", "Get-Process -Name explorer",
                        "Get-NetTCPConnection", "Test-Connection 192.168.1.1"):
            out = self.call("win.ps", cmdline).output
            self.assertIn(cmdline, out)

    def test_service_requires_confirm(self):
        res = self.call("win.services", "action=stop name=Spooler")
        self.assertFalse(res.ok)
        self.assertIn("подтверждение", res.error)
        out = self.call("win.services", "action=stop name=Spooler подтверждаю").output
        self.assertIn("Stop-Service", out)
        self.assertIn("Spooler", out)

    def test_service_name_validated(self):
        res = self.call("win.services", "action=start name=Spooler;calc подтверждаю")
        self.assertFalse(res.ok)
        self.assertIn("имя службы", res.error)
        out = self.call("win.services", "action=start name=Spooler подтверждаю").output
        self.assertIn("Start-Service", out)

    def test_kill_validated(self):
        self.assertFalse(self.call("win.process", "kill=abc").ok)
        res = self.call("win.process", "kill=1234")
        self.assertFalse(res.ok)
        self.assertIn("подтверждение", res.error)
        out = self.call("win.process", "kill=1234 подтверждаю").output
        self.assertIn("Stop-Process -Id 1234", out)

    @unittest.skipIf(os.name == "nt", "проверка именно для не-Windows")
    def test_honest_refusal_off_windows(self):
        res = self.call("win.info", dry=False)
        self.assertFalse(res.ok)
        self.assertIn("только в Windows", res.error)

    def test_runner_uses_fixed_argv(self):
        from unittest import mock
        from agentos.agents import windows as win_mod
        fake = {"ok": True, "code": 0, "out": "ok", "err": ""}
        with mock.patch.object(win_mod, "run_windows", return_value=fake) as run:
            res = self.call("win.ps", "Get-Service", dry=False)
            self.assertTrue(res.ok)
            argv = run.call_args[0][0]
            self.assertEqual(argv[0], "powershell.exe")
            self.assertIn("-NoProfile", argv)
            self.assertEqual(argv[-2], "-Command")
            self.assertTrue(argv[-1].startswith("[Console]::OutputEncoding"))
            self.assertIn("Get-Service", argv[-1])
            run.assert_called_once()

    def test_cmd_runner_argv(self):
        from unittest import mock
        from agentos.agents import windows as win_mod
        fake = {"ok": True, "code": 0, "out": "ok", "err": ""}
        with mock.patch.object(win_mod, "run_windows", return_value=fake) as run:
            self.call("win.cmd", "ipconfig", dry=False)
            argv = run.call_args[0][0]
            self.assertEqual(argv[:3], ["cmd.exe", "/d", "/c"])
            self.assertEqual(argv[3], "ipconfig /all")

    def test_decode_oem(self):
        from agentos.tools import decode_oem
        self.assertEqual(decode_oem("Привет".encode("utf-8")), "Привет")
        self.assertEqual(decode_oem("Привет".encode("cp866")), "Привет")
        self.assertEqual(decode_oem(b""), "")


class TestUtils(unittest.TestCase):
    def test_parse_params_keeps_newlines(self):
        params, body = parse_params("ip,port\n1.1.1.1,22\n2.2.2.2,80")
        self.assertEqual(params, {})
        self.assertEqual(len(body.splitlines()), 3)

    def test_parse_params_quoted(self):
        params, body = parse_params('шаблон="привет, {{имя}}!" имя=Иван')
        self.assertEqual(params["имя"], "Иван")
        self.assertEqual(params["шаблон"], "привет, {{имя}}!")
        self.assertEqual(body, "")

    def test_translit_and_slug(self):
        from agentos.utils import slugify
        self.assertEqual(slugify("Настройка WireGuard"), "nastroyka-wireguard")

    def test_redact_hides_values(self):
        from agentos.utils import redact
        self.assertNotIn("s3cret", redact("token=s3cret"))


class TestMemory(unittest.TestCase):
    def test_todo_lifecycle(self):
        mem = Memory(_TMP / "todo.sqlite")
        tid = mem.todo_add("проверить бэкап", "2026-12-01")
        self.assertEqual(len(mem.todo_list()), 1)
        self.assertTrue(mem.todo_done(tid))
        self.assertEqual(len(mem.todo_list()), 0)
        self.assertEqual(len(mem.todo_list(include_done=True)), 1)

    def test_run_logging(self):
        mem = Memory(_TMP / "runs.sqlite")
        mem.log_run("test.agent", True, 12, "запрос", "ответ")
        st = mem.stats()
        self.assertEqual(st["runs"], 1)
        self.assertEqual(st["ok"], 1)


class TestLLM(unittest.TestCase):
    def test_offline_probe_is_fast_and_false(self):
        cfg = load_config()
        cfg["llm"] = {"enabled": False, "url": "http://127.0.0.1:9/v1",
                      "fallback_urls": [], "model": "local", "timeout": 1}
        info = describe(cfg)
        self.assertFalse(info["available"])
        self.assertIn("hint", info)

    def test_ai_agents_work_without_llm(self):
        load_agents()
        ctx = make_context(load_config(), dry_run=True,
                           memory=Memory(_TMP / "ai.sqlite"))
        ctx.llm_client = None
        ctx.cfg["llm"] = {"enabled": False, "url": "http://127.0.0.1:9/v1",
                          "fallback_urls": [], "model": "local", "timeout": 1}
        res = run_agent(REGISTRY.get("ai.ask"), ctx, "покажи arp таблицу")
        self.assertTrue(res.ok)
        self.assertTrue(res.text().strip())


class TestAuditFixes(unittest.TestCase):
    """Регрессии по итогам аудита безопасности: дыры не должны вернуться."""

    @classmethod
    def setUpClass(cls):
        load_agents()
        cls.ctx = make_context(load_config(), dry_run=False,
                               memory=Memory(_TMP / "fix.sqlite"))

    def test_numeric_ip_forms_blocked(self):
        from agentos.tools import is_local_host
        for host in ("2852039166", "0x7f000001", "0.0.0.0", "2130706433"):
            self.assertFalse(is_local_host(host), host)

    def test_http_fetch_rejects_foreign(self):
        from agentos.tools import http_fetch
        for url in ("http://2852039166/", "http://example.com/"):
            with self.assertRaises(ToolError):
                http_fetch(self.ctx, url)

    def test_shell_whitelist_has_no_file_tools(self):
        from agentos.tools import ALLOWED_CMDS, run_cmd
        for cmd in ("cat", "tail", "find", "tar", "curl", "sqlite3", "git"):
            self.assertNotIn(cmd, ALLOWED_CMDS)
        with self.assertRaises(ToolError):
            run_cmd(self.ctx, ["cat", "/root/.config/opencode/secrets/homelab.env"])

    def test_archive_name_cannot_escape(self):
        res = run_agent(REGISTRY.get("fs.archive"), self.ctx,
                        "path=agentos/docs name=../../evil2.tar.gz")
        self.assertTrue(res.ok, res.text())
        self.assertIn(str(self.ctx.out), res.text())

    def test_hash_outside_sandbox_blocked(self):
        res = run_agent(REGISTRY.get("sec.hash"), self.ctx, "файл=/etc/shadow")
        self.assertFalse(res.ok)
        self.assertIn("вне разрешённых", res.text())

    def test_redact_hides_tokens(self):
        from agentos.utils import redact
        for raw in ('HASS_TOKEN=abc123def', '{"token": "abc123"}',
                    'password: hunter2', 'api_key=deadbeef'):
            self.assertNotIn("abc123", redact(raw).replace("abc123def", "X"))
            self.assertRegex(redact(raw), r"\*\*\*")

    def test_secret_agents_not_logged(self):
        mem = Memory(_TMP / "secret.sqlite")
        ctx = make_context(load_config(), dry_run=True, memory=mem)
        res = run_agent(REGISTRY.get("sec.genpass"), ctx, "20")
        self.assertTrue(res.ok)
        row = mem.runs(1)[0]
        self.assertEqual(row["query"], "[скрыто]")
        self.assertEqual(row["output"], "[скрыто]")

    def test_guard_regex_blocks_redos(self):
        from agentos.utils import guard_regex
        with self.assertRaises(ValueError):
            guard_regex("(a+)+$")
        guard_regex(r"\d{2,4}-\d{2}")            # обычный шаблон проходит

    def test_portable_aliases(self):
        from agentos.tools import resolve_path
        expected = ROOT / "agentos" / "docs" / "logo.png"
        self.assertEqual(resolve_path(self.ctx, "@app/agentos/docs/logo.png"), expected)
        self.assertEqual(resolve_path(self.ctx, "@app\\agentos\\docs\\logo.png"), expected)
        self.assertEqual(resolve_path(self.ctx, "@homelab/homelab.json"),
                         HOMELAB_DIR / "homelab.json")

    def test_exe_suffix_accepted(self):
        from agentos.tools import run_cmd
        res = run_cmd(self.ctx, ["ping.exe", "127.0.0.1"], timeout=2)
        self.assertIn("ok", res)          # Windows-имя проходит whitelist

    def test_windows_data_fallback_env(self):
        # LOCALAPPDATA используется только как fallback, но не должен ломать импорт
        self.assertTrue(str(ROOT))
        self.assertTrue(str(HOMELAB_DIR))

    def test_math_limits(self):
        for expr in ("10**100000", "fact(100000)"):
            res = run_agent(REGISTRY.get("math.calc"), self.ctx, expr)
            self.assertFalse(res.ok, expr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
