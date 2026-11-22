#!/usr/bin/env bash
set -euo pipefail
# Manual APK build (no Gradle daemon/AAPT2-daemon issues). Requires JDK, Android SDK build-tools/platform.
SDK=${ANDROID_SDK_ROOT:-/opt/android-sdk}
BT=$SDK/build-tools/34.0.0
PLAT=$SDK/platforms/android-34/android.jar
AAPT2=${AAPT2:-/opt/aapt2/aapt2}
JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-21-openjdk-arm64}
BUILD=build-manual
cd "$(dirname "$0")"
rm -rf "$BUILD"
mkdir -p "$BUILD/gen" "$BUILD/obj" "$BUILD/apk" "$BUILD/compiled"

# 1) Resources
$AAPT2 compile --dir app/src/main/res -o "$BUILD/compiled/res.zip"
# 2) Link (manifest must have package attr for aapt2 link)
$AAPT2 link -I "$PLAT" --manifest app/src/main/AndroidManifest.xml --java "$BUILD/gen" --auto-add-overlay -o "$BUILD/apk/base.apk" "$BUILD/compiled/res.zip"
# 3) Java
find app/src/main/java "$BUILD/gen" -name '*.java' > "$BUILD/sources.txt"
$JAVA_HOME/bin/javac -source 11 -target 11 -classpath "$PLAT" -d "$BUILD/obj" @"$BUILD/sources.txt"
# 4) DEX (use cmdline-tools r8.jar D8 mode for JDK21-compiled class compatibility in this env)
$JAVA_HOME/bin/java -cp "$SDK/cmdline-tools/latest/lib/r8.jar" com.android.tools.r8.D8 --release --min-api 24 --lib "$PLAT" --output "$BUILD/apk" $(find "$BUILD/obj" -name '*.class')
# 5) Package
cp "$BUILD/apk/base.apk" "$BUILD/apk/unsigned.apk"
(cd "$BUILD/apk" && (zip -u unsigned.apk classes.dex 2>/dev/null || "$JAVA_HOME/bin/jar" uf unsigned.apk classes.dex))
# 6) Zipalign (optional; build-tools zipalign may be wrong arch)
if "$BT/zipalign" -f -p 4 "$BUILD/apk/unsigned.apk" "$BUILD/apk/aligned.apk" 2>/dev/null; then
  INAPK="$BUILD/apk/aligned.apk"
else
  echo "zipalign skipped/failed, signing unsigned apk"
  INAPK="$BUILD/apk/unsigned.apk"
fi
# 7) Debug keystore
mkdir -p "$HOME/.android"
if [ ! -f "$HOME/.android/debug.keystore" ]; then
  $JAVA_HOME/bin/keytool -genkeypair -v -keystore "$HOME/.android/debug.keystore" -storepass android -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
fi
# 8) Sign
$BT/apksigner sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android --key-pass pass:android --ks-key-alias androiddebugkey --out "$BUILD/apk/FreeVoice-debug.apk" "$INAPK"
$BT/apksigner verify --print-certs "$BUILD/apk/FreeVoice-debug.apk"
echo "OK: $BUILD/apk/FreeVoice-debug.apk"
