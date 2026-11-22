"""Медиа: размеры картинок, длительность mp4, RTSP-ссылки, плейлисты."""
from __future__ import annotations

import re
import struct
from pathlib import Path

from ..core import Context, agent
from ..tools import read_text, resolve_path, ToolError
from ..utils import human_bytes, kv, parse_kv, table

IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic"}
VID_EXT = {".mp4", ".mkv", ".avi", ".mov", ".ts", ".webm", ".m4v"}


def image_size(data: bytes):
    if data.startswith(b"\x89PNG") and len(data) > 24:
        w, h = struct.unpack(">II", data[16:24])
        return w, h, "PNG"
    if data.startswith(b"GIF") and len(data) > 10:
        w, h = struct.unpack("<HH", data[6:10])
        return w, h, "GIF"
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h, "JPEG"
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seg
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return None, None, "WebP"
    if data.startswith(b"BM") and len(data) > 26:
        w, h = struct.unpack("<ii", data[18:26])
        return abs(w), abs(h), "BMP"
    return None, None, "?"


def mp4_duration(data: bytes):
    """Ищет moov/mvhd в первых мегабайтах — без внешних утилит."""
    def atoms(buf, start, end):
        i = start
        while i + 8 <= end:
            size = struct.unpack(">I", buf[i:i + 4])[0]
            kind = buf[i + 4:i + 8]
            if size < 8:
                break
            yield kind, i + 8, min(i + size, end)
            i += size

    for kind, body, end in atoms(data, 0, len(data)):
        if kind == b"moov":
            for k2, b2, e2 in atoms(data, body, end):
                if k2 == b"mvhd" and e2 - b2 >= 20:
                    version = data[b2]
                    if version == 0:
                        timescale = struct.unpack(">I", data[b2 + 12:b2 + 16])[0]
                        duration = struct.unpack(">I", data[b2 + 16:b2 + 20])[0]
                    else:
                        timescale = struct.unpack(">I", data[b2 + 20:b2 + 24])[0]
                        duration = struct.unpack(">Q", data[b2 + 24:b2 + 32])[0]
                    if timescale:
                        return duration / timescale
    return None


@agent("media.image", "Размер картинки", "media",
       "Ширина и высота изображения по заголовку файла",
       keywords=("размер картинки", "image", "ширина", "высота", "фото", "png", "jpeg"),
       examples=("файл=@app/agentos/docs/logo.png",), needs=())
def image(ctx: Context, text: str):
    raw = text.replace("файл=", "").replace("file=", "").strip().split()[0]
    p = resolve_path(ctx, raw)
    with p.open("rb") as fh:
        data = fh.read(4096)
    w, h, kind = image_size(data)
    if not w:
        return kv([("файл", p.name), ("формат", kind), ("размер", "не определён")])
    mp = w * h / 1e6
    return kv([("файл", p.name), ("формат", kind), ("размер", f"{w}×{h}"),
               ("мегапикселей", f"{mp:.2f}"),
               ("соотношение", f"{w / h:.2f}")])


@agent("media.video", "Инфо о видео", "media",
       "Длительность и размер MP4/MOV без ffprobe",
       keywords=("видео", "длительность", "mp4", "сколько идёт", "фильм", "video"),
       examples=("файл=@app/agentos/docs/sample.mp4",), needs=())
def video(ctx: Context, text: str):
    raw = text.replace("файл=", "").replace("file=", "").strip().split()[0]
    p = resolve_path(ctx, raw)
    size = p.stat().st_size
    with p.open("rb") as fh:
        head = fh.read(min(size, 4_000_000))
    dur = mp4_duration(head)
    if dur is None:
        return kv([("файл", p.name), ("размер", human_bytes(size)),
                   ("длительность", "не MP4/MOV — нужен ffprobe")])
    minutes, seconds = divmod(int(dur), 60)
    hours, minutes = divmod(minutes, 60)
    return kv([("файл", p.name), ("размер", human_bytes(size)),
               ("длительность", f"{hours:02d}:{minutes:02d}:{seconds:02d}"),
               ("битрейт", f"{size * 8 / dur / 1e6:.1f} Мбит/с" if dur else "-")])


@agent("media.rtsp", "RTSP-ссылка", "media",
       "Собирает RTSP-URL для XM/NVR-камеры из инвентаря или параметров",
       keywords=("rtsp", "поток", "камера ссылка", "видеопоток", "url камеры"),
       examples=("host=192.168.1.10 user=admin pass=secret stream=0",), needs=("net",))
def rtsp(ctx: Context, text: str):
    params, rest = parse_kv(text)
    host = params.get("host") or rest.split()[0] if (params.get("host") or rest) else ""
    if not host:
        raise ValueError("нужен host=192.168.1.10")
    user = params.get("user", "admin")
    pwd = params.get("pass", "***")
    stream = params.get("stream", "0")
    subtype = {"0": "0", "1": "1"}.get(stream, "0")
    url = f"rtsp://{user}:{pwd}@{host}:554/cam/realmonitor?channel=1&subtype={subtype}"
    alt = f"rtsp://{user}:{pwd}@{host}:554/user={user}_password={pwd}_channel=1_stream={stream}.sdp"
    return ("основной вариант (Dahua/XM):\n" + url +
            "\n\nальтернативный (старые XM):\n" + alt +
            "\n\nпроверка порта: agentos run net.ports \"" + host + " 554\"")


@agent("media.m3u", "Проверка плейлиста", "media",
       "Разбирает M3U/M3U8: каналы, локальные файлы, битые записи",
       keywords=("m3u", "плейлист", "iptv", "каналы", "playlist"),
       examples=("файл=@app/agentos/docs/sample.m3u",), needs=())
def m3u(ctx: Context, text: str):
    raw = text.replace("файл=", "").replace("file=", "").strip().split()[0]
    src = read_text(ctx, raw)
    base = resolve_path(ctx, raw).parent       # относительные пути — от самого .m3u
    entries, names, broken = [], [], 0
    for line in src.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            m = re.search(r",(.+)$", line)
            names.append(m.group(1).strip() if m else "?")
        elif line and not line.startswith("#"):
            entries.append(line)
    local = [e for e in entries if not re.match(r"^\w+://", e)]
    for e in local:
        p = Path(e)
        if not p.is_absolute():
            p = base / e
        if not p.exists():
            broken += 1
    rows = [[i + 1, names[i] if i < len(names) else "?", e[:60]]
            for i, e in enumerate(entries[:40])]
    head = (f"каналов: {len(entries)}, локальных файлов: {len(local)}, "
            f"битых путей: {broken}")
    return head + "\n" + table(rows, ["#", "имя", "источник"], align_right={0})


@agent("media.index", "Медиатека", "media",
       "Индексирует медиафайлы каталога: количество и объём по типам",
       keywords=("медиатека", "индекс", "фото", "видео в папке", "сколько файлов"),
       examples=("path=@app",), needs=())
def index(ctx: Context, text: str):
    params, rest = parse_kv(text)
    base = resolve_path(ctx, params.get("path") or rest or ".")
    stats: dict[str, list] = {}
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in IMG_EXT or ext in VID_EXT:
            kind = "видео" if ext in VID_EXT else "фото"
            bucket = stats.setdefault(kind, [0, 0, set()])
            try:
                bucket[0] += 1
                bucket[1] += p.stat().st_size
            except OSError:
                pass
            bucket[2].add(ext)
    if not stats:
        return f"медиафайлов в {base} нет"
    rows = [[k, v[0], human_bytes(v[1]), ", ".join(sorted(v[2]))]
            for k, v in stats.items()]
    total = sum(v[0] for v in stats.values())
    return table(rows, ["тип", "файлов", "объём", "форматы"], align_right={1}) + \
        f"\nвсего файлов: {total}"
