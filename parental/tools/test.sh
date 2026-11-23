#!/bin/sh
# Offline protocol tests: no JUnit, no device, no network.
set -eu
cd "$(dirname "$0")/.."

export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-21-openjdk-arm64}"
ANDROID_JAR="${ANDROID_SDK_ROOT:-/opt/android-sdk}/platforms/android-34/android.jar"
JAVAC="$JAVA_HOME/bin/javac"
JAVA="$JAVA_HOME/bin/java"

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

echo "== compile =="
"$JAVAC" -nowarn -encoding UTF-8 -cp "$ANDROID_JAR" -d "$OUT" \
    console/src/main/java/ru/homeguard/console/Protocol.java \
    agent/src/main/java/ru/homeguard/agent/Protocol.java \
    tools/tests/TestRunner.java

echo "== keystore IV regression guard =="
# Android Keystore (keystore2, API 31+) запрещает caller-provided IV при
# шифровании. Seal (консоль) и Store (агент) должны брать IV через cipher.getIV().
# Backup использует паролевый ключ — там IV допустим, он не должен трогаться.
for f in \
    console/src/main/java/ru/homeguard/console/Seal.java \
    agent/src/main/java/ru/homeguard/agent/Store.java; do
    if grep -E 'init\(Cipher\.ENCRYPT_MODE[^;]*GCMParameterSpec' "$f" >/dev/null; then
        echo "FAIL: $f использует caller-provided IV при ENCRYPT_MODE" >&2
        exit 1
    fi
    if ! grep -q 'cipher.getIV()\|c.getIV()' "$f"; then
        echo "FAIL: $f не берёт IV через getIV()" >&2
        exit 1
    fi
done
echo "guard OK"

echo "== HA bridge guard =="
# Мост в HA — только локальный webhook, без токенов и хардкод-адресов.
HB=console/src/main/java/ru/homeguard/console/HaBridge.java
if grep -Eqi 'Bearer |HASS_TOKEN|Authorization|sahanovschi|192\.168\.1\.156' "$HB"; then
    echo "FAIL: $HB содержит токен или захардкоженный адрес" >&2
    exit 1
fi
if ! grep -q 'setRequestMethod("POST")' "$HB" || ! grep -q 'setConnectTimeout' "$HB"; then
    echo "FAIL: $HB не задаёт POST/таймауты" >&2
    exit 1
fi
if ! grep -q 'HaBridge.enabled(ctx)' console/src/main/java/ru/homeguard/console/ControlServer.java; then
    echo "FAIL: ControlServer не вызывает мост HA" >&2
    exit 1
fi
echo "HA bridge guard OK"

echo "== protocol tests =="
"$JAVA" -cp "$OUT:$ANDROID_JAR" TestRunner
