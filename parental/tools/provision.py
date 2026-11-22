#!/usr/bin/env python3
"""Generate a Device-Owner provisioning payload for the HomeGuard agent.

Two provisioning paths are supported:

1. ADB (recommended when the child's phone is at hand):
     adb install -r agent-1.0.0.apk
     adb shell dpm set-device-owner ru.homeguard.agent/.GuardReceiver

2. QR / NFC provisioning of a freshly reset phone: this script prints the
   payload and a JSON blob, and can serve the APK over the LAN so the setup
   wizard can download it. The QR image itself can be produced with any
   offline QR app or `qrencode -o qr.png "$(python3 tools/provision.py ...)"`.
"""
import argparse
import base64
import hashlib
import http.server
import os
import socket
import socketserver
import sys


def lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.4)
        s.connect(("192.168.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "0.0.0.0"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk", default="dist/agent-1.1.1.apk")
    ap.add_argument("--host", default=None, help="IP serving the APK (default: this machine)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--device-id", default="kid-0001")
    ap.add_argument("--code", required=True, help="pairing code from the console, e.g. ABCD-EFGH-JKLM-NPQR")
    ap.add_argument("--console", required=True, help="console address, e.g. 192.168.1.155:8787")
    ap.add_argument("--serve", action="store_true", help="serve the APK directory over HTTP")
    ap.add_argument("--json", action="store_true", help="print the full provisioning JSON")
    args = ap.parse_args()

    apk = os.path.abspath(args.apk)
    if not os.path.isfile(apk):
        print(f"APK not found: {apk}", file=sys.stderr)
        return 2

    with open(apk, "rb") as f:
        data = f.read()
    checksum = base64.b64encode(hashlib.sha256(data).digest()).decode()

    host = args.host or lan_ip()
    url = f"http://{host}:{args.port}/{os.path.basename(apk)}"
    payload = "hg1:{host}:{port}:{dev}:{code}".format(
        host=args.console.split(":")[0],
        port=args.console.split(":")[1] if ":" in args.console else 8787,
        dev=args.device_id,
        code=args.code,
    )

    extras = {
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME":
            "ru.homeguard.agent/.GuardReceiver",
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION": url,
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_CHECKSUM": checksum,
        "android.app.extra.PROVISIONING_LEAVE_ALL_SYSTEM_APPS_ENABLED": True,
        "android.app.extra.PROVISIONING_SKIP_ENCRYPTION": False,
    }

    print("ADB provisioning:")
    print(f"  adb install -r {apk}")
    print("  adb shell dpm set-device-owner ru.homeguard.agent/.GuardReceiver")
    print()
    print("Pairing payload (type into the agent):")
    print(f"  {payload}")
    print()
    import json
    print("QR provisioning payload (this exact JSON goes into the QR code):")
    print(json.dumps(extras, separators=(",", ":"), ensure_ascii=False))
    if args.json:
        print()
        print(json.dumps(extras, indent=2, ensure_ascii=False))
    print()
    print(f"APK checksum (base64 sha256): {checksum}")

    if args.serve:
        directory = os.path.dirname(apk)
        handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=directory, **kw)
        with socketserver.TCPServer(("0.0.0.0", args.port), handler) as httpd:
            print(f"serving {directory} on {url}  (Ctrl+C to stop)")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
