#!/usr/bin/env python3
"""
Простой офлайн-экстрактор текста из PDF (только stdlib: re, zlib).
Работает для текстовых PDF с незашифрованными/распаковываемыми потоками и
простыми строками (Tj/TJ). Не работает для сканов/изображений, CID-шрифтов
со сложным ToUnicode, защищённых/нестандартных PDF. Ничего не устанавливает.
"""
from __future__ import annotations

import argparse
import re
import sys
import zlib
from pathlib import Path


def decode_pdf_string(data: bytes) -> str:
    # literal string escapes: \n \r \t \b \f \( \) \\ \ddd
    out = bytearray()
    i = 0
    while i < len(data):
        c = data[i:i+1]
        if c != b"\\":
            out += c
            i += 1
            continue
        i += 1
        if i >= len(data):
            break
        n = data[i:i+1]
        if n in b"nrtbf":
            out += {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}[n]
            i += 1
        elif n in b"()\\":
            out += n
            i += 1
        elif n.isdigit():
            octs = data[i:i+3]
            m = re.match(rb"[0-7]{1,3}", octs)
            if m:
                out.append(int(m.group(0), 8) & 0xFF)
                i += len(m.group(0))
            else:
                i += 1
        elif n in b"\r\n":
            if n == b"\r" and i + 1 < len(data) and data[i+1:i+2] == b"\n":
                i += 2
            else:
                i += 1
        else:
            out += n
            i += 1
    # try utf-16be (common with BOM FE FF in PDF strings) then latin-1
    b = bytes(out)
    if b.startswith(b"\xfe\xff"):
        try:
            return b[2:].decode("utf-16-be", errors="replace")
        except Exception:
            pass
    for enc in ("utf-8", "latin-1"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("latin-1", errors="replace")


def decode_hex_string(hexdata: bytes) -> str:
    h = re.sub(rb"\s+", b"", hexdata)
    if len(h) % 2:
        h += b"0"
    try:
        b = bytes.fromhex(h.decode("ascii", errors="ignore"))
    except Exception:
        return ""
    if b.startswith(b"\xfe\xff"):
        try:
            return b[2:].decode("utf-16-be", errors="replace")
        except Exception:
            pass
    for enc in ("utf-8", "latin-1"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("latin-1", errors="replace")


def extract_from_content(content: bytes) -> list[str]:
    parts: list[str] = []

    def lit(m: re.Match) -> str:
        return decode_pdf_string(m.group(1))

    # TJ arrays: [(...)] TJ  or [<...> (...)] TJ
    for m in re.finditer(rb"\[(.*?)\]\s*TJ", content, re.S):
        arr = m.group(1)
        segs = []
        for sm in re.finditer(rb"\((?:\\.|[^\\)])*\)|<([0-9A-Fa-f\s]*)>", arr, re.S):
            token = sm.group(0)
            if token.startswith(b"("):
                inner = token[1:-1]
                segs.append(decode_pdf_string(inner))
            else:
                segs.append(decode_hex_string(sm.group(1) or b""))
        if segs:
            parts.append("".join(segs))
    # Tj single string
    for m in re.finditer(rb"(\((?:\\.|[^\\)])*\)|<([0-9A-Fa-f\s]*)>)\s*Tj", content, re.S):
        token = m.group(1)
        if token.startswith(b"("):
            parts.append(decode_pdf_string(token[1:-1]))
        else:
            parts.append(decode_hex_string(m.group(2) or b""))

    # keep order roughly by appearance
    # simple heuristic: re-run in sequence
    ordered: list[str] = []
    for m in re.finditer(rb"\[(.*?)\]\s*TJ|(\((?:\\.|[^\\)])*\)|<([0-9A-Fa-f\s]*)>)\s*Tj", content, re.S):
        if m.group(0).endswith(b"TJ") and m.group(0).lstrip().startswith(b"["):
            arr = m.group(1)
            segs = []
            for sm in re.finditer(rb"\((?:\\.|[^\\)])*\)|<([0-9A-Fa-f\s]*)>", arr, re.S):
                token = sm.group(0)
                if token.startswith(b"("):
                    segs.append(decode_pdf_string(token[1:-1]))
                else:
                    segs.append(decode_hex_string(sm.group(1) or b""))
            if segs:
                ordered.append("".join(segs))
        else:
            token = m.group(2)
            if token and token.startswith(b"("):
                ordered.append(decode_pdf_string(token[1:-1]))
            elif token:
                ordered.append(decode_hex_string(m.group(3) or b""))
    return ordered or parts


def iter_streams(data: bytes):
    for m in re.finditer(rb"<<(.*?)>>\s*stream\r?\n", data, re.S):
        dict_raw = m.group(1)
        start = m.end()
        end = data.find(b"endstream", start)
        if end == -1:
            continue
        stream = data[start:end]
        if stream.endswith(b"\r\n"):
            stream = stream[:-2]
        elif stream.endswith(b"\n") or stream.endswith(b"\r"):
            stream = stream[:-1]
        yield dict_raw, stream


def try_decompress(dict_raw: bytes, stream: bytes) -> bytes:
    if b"/FlateDecode" in dict_raw:
        for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
            try:
                return zlib.decompress(stream, wbits)
            except Exception:
                pass
    return stream


def extract_text(pdf_bytes: bytes) -> tuple[str, dict]:
    texts: list[str] = []
    seen = set()
    streams_total = 0
    streams_decoded = 0
    for dict_raw, stream in iter_streams(pdf_bytes):
        streams_total += 1
        decoded = try_decompress(dict_raw, stream)
        if decoded is not stream:
            streams_decoded += 1
        # skip obvious image streams
        if b"/Subtype" in dict_raw and b"/Image" in dict_raw:
            continue
        for t in extract_from_content(decoded):
            if t and t.strip():
                if t not in seen:
                    texts.append(t)
                    seen.add(t)
    # fallback: try whole file for uncompressed text operators
    if not texts:
        for t in extract_from_content(pdf_bytes):
            if t and t.strip() and t not in seen:
                texts.append(t)
                seen.add(t)
    meta = {
        "streams_total": streams_total,
        "streams_decoded": streams_decoded,
        "chunks": len(texts),
    }
    return "\n".join(texts).strip(), meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Офлайн-извлечение текста из простого PDF (stdlib)")
    ap.add_argument("path", help="Путь к PDF")
    ap.add_argument("--meta", action="store_true", help="Показать метаданные извлечения в stderr")
    args = ap.parse_args()
    p = Path(args.path)
    if not p.exists():
        print(f"Файл не найден: {p}", file=sys.stderr)
        return 2
    data = p.read_bytes()
    if not data.startswith(b"%PDF"):
        print("Не похоже на PDF (%PDF заголовок отсутствует)", file=sys.stderr)
        return 2
    text, meta = extract_text(data)
    if args.meta:
        print(f"[meta] {meta}", file=sys.stderr)
    if text:
        print(text)
        return 0
    print("Текст не извлечён (возможно скан/изображения, сложное кодирование или защита).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
