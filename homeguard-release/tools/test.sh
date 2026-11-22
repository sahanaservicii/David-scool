#!/bin/sh
# Offline protocol tests: no JUnit, no device, no network.
set -eu
cd "$(dirname "$0")/.."

JAVAC="${JAVA_HOME:+$JAVA_HOME/bin/}javac"
JAVA="${JAVA_HOME:+$JAVA_HOME/bin/}java"
ANDROID_SDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Android/Sdk}}"
ANDROID_JAR="$ANDROID_SDK/platforms/android-34/android.jar"
if [ ! -f "$ANDROID_JAR" ]; then
  echo "android.jar not found: $ANDROID_JAR (set ANDROID_SDK_ROOT)" >&2
  exit 1
fi

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

echo "== compile =="
"$JAVAC" -nowarn -encoding UTF-8 -cp "$ANDROID_JAR" -d "$OUT" \
    console/src/main/java/ru/homeguard/console/Protocol.java \
    agent/src/main/java/ru/homeguard/agent/Protocol.java \
    tools/tests/TestRunner.java

echo "== protocol tests =="
"$JAVA" -cp "$OUT:$ANDROID_JAR" TestRunner
