#!/usr/bin/env python3
"""Локальный мост «сигнал -> видео URL» для караоке. Только stdlib, без облака.

Не включает ТВ сам по себе: по появлению файла-триггера готовит URL локального
видео, оповещает телефон и (опционально) выполняет настраиваемую команду
проигрывания. Реальный запуск на ТВ подключается через `play_cmd` или DLNA-клиент.
"""

import argparse
import fnmatch
import json
import logging
import os
import shlex
import socket
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_DIR = SCRIPT_DIR / "state"
DEFAULT_CONFIG = SCRIPT_DIR / "karaoke_bridge.json"

CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
}

ACTIVE_SERVER = None

DEFAULTS = {
    "watch_dir": "/root/workspace/inbox",
    "trigger_file": "karaoke.play",
    "video_patterns": ["*.mp4", "*.mkv", "*.webm", "*.avi", "*.mov"],
    "min_video_bytes": 1048576,
    "http_port": 8766,
    "bind": "0.0.0.0",
    "probe_host": "192.168.0.1",
    "notify": True,
    "play_cmd": "",
    "poll_seconds": 2.0,
}


def load_config(path: Path) -> dict:
    cfg = dict(DEFAULTS)
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("не удалось прочитать конфиг %s: %s", path, exc)
    return cfg


def local_ip(probe_host: str) -> str:
    """IP исходящего интерфейса без отправки пакетов (UDP connect)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((probe_host, 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class VideoHandler(BaseHTTPRequestHandler):
    def __init__(self, video_path: Path, *args, **kwargs):
        self.video_path = video_path
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] not in ("/", "/video"):
            self.send_error(404)
            return
        size = self.video_path.stat().st_size
        start, end, status = 0, size - 1, 200
        requested = self.headers.get("Range", "")
        if requested.startswith("bytes="):
            spec = requested[6:].split("-", 1)
            try:
                if spec[0]:
                    start = int(spec[0])
                    if len(spec) > 1 and spec[1]:
                        end = int(spec[1])
                elif len(spec) > 1 and spec[1]:
                    suffix = int(spec[1])
                    start = max(0, size - suffix)
                    end = size - 1
                status = 206
            except ValueError:
                start, end, status = 0, size - 1, 200
            start = max(0, min(start, size - 1))
            end = max(start, min(end, size - 1))
        length = end - start + 1
        content_type = CONTENT_TYPES.get(
            self.video_path.suffix.lower(), "application/octet-stream"
        )

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()

        remaining = length
        with self.video_path.open("rb") as handle:
            handle.seek(start)
            while remaining > 0:
                chunk = handle.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_HEAD(self) -> None:
        if self.path.split("?", 1)[0] not in ("/", "/video"):
            self.send_error(404)
            return
        size = self.video_path.stat().st_size
        content_type = CONTENT_TYPES.get(
            self.video_path.suffix.lower(), "application/octet-stream"
        )
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        logging.info("http %s: %s", self.address_string(), fmt % args)


def start_server(video: Path, port: int, bind: str) -> ThreadingHTTPServer:
    global ACTIVE_SERVER
    handler = partial(VideoHandler, video)
    server = ThreadingHTTPServer((bind, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    ACTIVE_SERVER = server
    return server


def find_videos(watch: Path, patterns: list) -> list:
    found = []
    if not watch.is_dir():
        return found
    for entry in watch.iterdir():
        if not entry.is_file():
            continue
        name = entry.name.lower()
        if any(fnmatch.fnmatch(name, str(p).lower()) for p in patterns):
            found.append(entry)
    return found


def notify_phone(message: str) -> None:
    helper = Path(
        os.environ.get("OPENCODE_CONFIG_HOME", "/root/.config/opencode")
    ) / "skills/android-device/android_device.py"
    if not helper.exists():
        logging.warning("мост телефона недоступен: %s", helper)
        return
    try:
        subprocess.run(
            [sys.executable, str(helper), "notify", "--title", "Караоке-мост",
             "--message", message],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logging.warning("уведомление не отправлено: %s", exc)


def run_play_cmd(cfg: dict, url: str, video: Path) -> None:
    template = str(cfg.get("play_cmd", "")).strip()
    if not template:
        logging.info("play_cmd не задан — ТВ не переключался")
        return
    rendered = template.replace("{url}", url).replace("{video}", str(video))
    try:
        result = subprocess.run(
            shlex.split(rendered), capture_output=True, text=True, timeout=30,
            check=False,
        )
        logging.info("play_cmd код=%s", result.returncode)
    except (OSError, subprocess.SubprocessError) as exc:
        logging.error("play_cmd не выполнен: %s", exc)


def move_trigger(trigger: Path, suffix: str) -> None:
    target = trigger.with_name(f"{trigger.name}.{suffix}.{int(time.time())}")
    try:
        trigger.rename(target)
        logging.info("триггер перемещён в %s", target.name)
    except OSError as exc:
        logging.error("не удалось переместить триггер: %s", exc)


def process_trigger(cfg: dict, trigger: Path, dry_run: bool) -> bool:
    watch = Path(str(cfg["watch_dir"])).expanduser()
    overrides = {}
    try:
        for line in trigger.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                overrides[key.strip()] = value.strip()
    except OSError as exc:
        logging.error("не прочитан триггер: %s", exc)
        return False

    video = None
    if overrides.get("video"):
        candidate = Path(overrides["video"]).expanduser()
        if candidate.is_file():
            video = candidate
    if video is None:
        candidates = [p for p in find_videos(watch, cfg["video_patterns"])
                      if p.name != trigger.name]
        if candidates:
            video = max(candidates, key=lambda p: p.stat().st_mtime)

    if video is None:
        logging.error("видеофайл не найден в %s", watch)
        move_trigger(trigger, "failed")
        return False
    size = video.stat().st_size
    if size < int(cfg["min_video_bytes"]):
        logging.error("файл слишком маленький, байт=%s: %s", size, video)
        move_trigger(trigger, "failed")
        return False

    probe_host = str(cfg.get("probe_host", "192.168.0.1"))
    url = f"http://{local_ip(probe_host)}:{int(cfg['http_port'])}/video"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "video": str(video),
        "url": url,
        "bytes": size,
        "trigger": str(trigger),
        "dry_run": dry_run,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (STATE_DIR / "karaoke_current.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logging.info("видео готово: %s (%s байт), URL %s", video, size, url)

    if not dry_run:
        try:
            start_server(video, int(cfg["http_port"]), str(cfg["bind"]))
        except OSError as exc:
            logging.error("HTTP-сервер не стартовал: %s", exc)
        if cfg.get("notify", True):
            notify_phone(f"Караоке готово: {video.name} -> {url}")
        run_play_cmd(cfg, url, video)

    move_trigger(trigger, "done")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--once", action="store_true",
                        help="обработать один триггер и выйти")
    parser.add_argument("--dry-run", action="store_true",
                        help="не поднимать сервер и не выполнять play_cmd")
    args = parser.parse_args()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(STATE_DIR / "karaoke_bridge.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    cfg = load_config(args.config)
    watch = Path(str(cfg["watch_dir"])).expanduser()
    trigger = watch / str(cfg["trigger_file"])

    if args.once and not trigger.exists():
        logging.error("триггера нет: %s", trigger)
        return 1

    logging.info("мост запущен: каталог=%s, триггер=%s, dry_run=%s",
                 watch, trigger.name, args.dry_run)
    while True:
        if trigger.exists():
            ok = process_trigger(cfg, trigger, args.dry_run)
            if args.once:
                if not ok:
                    return 1
                if not args.dry_run and ACTIVE_SERVER is not None:
                    logging.info("HTTP-сервер работает; Ctrl+C для остановки")
                    try:
                        threading.Event().wait()
                    except KeyboardInterrupt:
                        ACTIVE_SERVER.shutdown()
                return 0
        if args.once:
            logging.error("триггер не дал готовое видео")
            return 1
        time.sleep(float(cfg["poll_seconds"]))


if __name__ == "__main__":
    raise SystemExit(main())
