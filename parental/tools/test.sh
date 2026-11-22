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

echo "== protocol tests =="
"$JAVA" -cp "$OUT:$ANDROID_JAR" TestRunner
