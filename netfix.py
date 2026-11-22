#!/usr/bin/env python3
"""
Ожидание возврата в домашнюю сеть 192.168.1.0/24 и автоматическое исправление
найденных проблем. Запускать: python3 netfix.py [таймаут_сек]
Результат: /tmp/opencode/fix-result.json + лог в stdout.
"""
import socket, struct, subprocess, sys, time, json

NET = "192.168.1."
TARGET = "192.168.1.139"      # ADT-3 с открытым ADB
TIMEOUT = int(sys.argv[1]) if len(sys.argv) > 1 else 900


# ---------- ADB ----------
def adb_pkt(cmd, a0, a1, data=b""):
    c = sum(data) & 0xffffffff
    m = struct.unpack("<I", cmd.encode())[0] ^ 0xffffffff
    return cmd.encode() + struct.pack("<IIII", a0, a1, len(data), c) + struct.pack("<I", m) + data


def adb_open(ip, port=5555, timeout=6):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect((ip, port))
    s.sendall(adb_pkt("CNXN", 0x01000001, 4096, b"host::\x00"))
    d = s.recv(4096)
    if d[:4] != b"CNXN":
        s.close()
        raise RuntimeError(f"неожиданный ответ ADB: {d[:4]!r}")
    return s


def adb_shell(s, cmd, wait=4.0):
    """Выполняет команду в уже открытом соединении."""
    s.sendall(adb_pkt("OPEN", 1, 0, ("shell:" + cmd).encode()))
    out = b""
    end = time.time() + wait
    while time.time() < end:
        try:
            chunk = s.recv(8192)
        except socket.timeout:
            break
        if not chunk:
            break
        out += chunk
        if b"CLSE" in out:
            break
    # разбор пакетов: собираем данные WRTE
    res, i = b"", 0
    while i + 24 <= len(out):
        cmd4 = out[i:i + 4]
        ln = struct.unpack("<I", out[i + 12:i + 16])[0]
        data = out[i + 24:i + 24 + ln]
        if cmd4 == b"WRTE":
            res += data
        i += 24 + ln
    return res.decode("utf-8", "replace")


def tcp_open(ip, port, t=1.5):
    s = socket.socket()
    s.settimeout(t)
    try:
        return s.connect_ex((ip, port)) == 0
    finally:
        s.close()


# ---------- шаги ----------
def wait_for_network():
    deadline = time.time() + TIMEOUT
    n = 0
    while time.time() < deadline:
        n += 1
        if tcp_open(NET + "1", 80, 2) or tcp_open(NET + "1", 53, 2):
            print(f"[{n}] сеть {NET}0/24 доступна", flush=True)
            return True
        if n % 6 == 1:
            print(f"[{n}] ждём домашний Wi-Fi...", flush=True)
        time.sleep(10)
    return False


def fix_adb():
    if not tcp_open(TARGET, 5555, 2):
        return {"skipped": "порт 5555 закрыт или хост недоступен"}
    s = adb_open(TARGET)
    props = {}
    for p in ("persist.adb.tcp.port", "service.adb.tcp.port", "ro.adb.secure", "ro.debuggable", "ro.product.model"):
        props[p] = adb_shell(s, f"getprop {p}", 2).strip()
    model = adb_shell(s, "getprop ro.product.model", 2).strip()
    print("props:", props, flush=True)

    # 1) отключаем сетевой ADB (USB-отладка продолжит работать)
    adb_shell(s, "setprop persist.adb.tcp.port -1", 2)
    adb_shell(s, "setprop service.adb.tcp.port -1", 2)
    # 2) перезапуск демона -> TCP-листенер не поднимается
    try:
        adb_shell(s, "setprop ctl.restart adbd", 2)
    except Exception:
        pass
    s.close()

    time.sleep(6)
    still = tcp_open(TARGET, 5555, 2)
    return {"host": TARGET, "model": model, "props": props,
            "port_5555_after": "OPEN" if still else "CLOSED", "fixed": not still}


def rescan():
    ports = [22, 53, 80, 443, 445, 554, 5000, 7000, 5555, 8080, 8008, 8009,
             8443, 9100, 32400, 3389, 34567, 8000, 8081]
    found = {}

    def probe(ip):
        op = []
        for p in ports:
            if tcp_open(ip, p, 0.6):
                op.append(p)
        return op

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=120) as ex:
        for i, op in zip(range(1, 255), ex.map(lambda n: probe(NET + str(n)), range(1, 255))):
            if op:
                found[NET + str(i)] = sorted(op)
    return found


def main():
    result = {"started": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not wait_for_network():
        result["status"] = "timeout: домашняя сеть не появилась"
        print(json.dumps(result, ensure_ascii=False, indent=1))
        json.dump(result, open("/tmp/opencode/fix-result.json", "w"), ensure_ascii=False, indent=1)
        return
    result["hosts"] = rescan()
    print("хосты:", json.dumps(result["hosts"], ensure_ascii=False), flush=True)
    result["adb_fix"] = fix_adb()
    print("ADB:", json.dumps(result["adb_fix"], ensure_ascii=False), flush=True)
    # контрольная проверка после перезапуска adbd
    time.sleep(3)
    result["verified_hosts"] = rescan()
    result["status"] = "done"
    result["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(result, open("/tmp/opencode/fix-result.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
