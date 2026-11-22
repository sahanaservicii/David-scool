#!/bin/sh
# Reproducible release build. Works offline once the toolchain is installed.
set -eu
cd "$(dirname "$0")/.."
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-21-openjdk-arm64}"
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/opt/android-sdk}"
GRADLE="${GRADLE:-/opt/gradle/gradle-8.7/bin/gradle}"

if [ ! -f keystore.properties ]; then
  echo "keystore.properties missing — create the signing key first (see docs/BUILD.md)" >&2
  exit 1
fi

"$GRADLE" assembleRelease --no-daemon --console=plain -q

mkdir -p dist
rm -f dist/agent-*.apk dist/console-*.apk dist/SHA256SUMS
for m in agent console; do
  VER=$(grep -m1 "versionName" "$m/build.gradle" | sed "s/.*versionName '\(.*\)'.*/\1/")
  cp "$m/build/outputs/apk/release/$m-release.apk" "dist/$m-$VER.apk"
done
cd dist
sha256sum ./*.apk > SHA256SUMS
for f in ./*.apk; do
  "$ANDROID_SDK_ROOT/build-tools/34.0.0/apksigner" verify --print-certs "$f" | head -2
done
ls -lh ./*.apk
