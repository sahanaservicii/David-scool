# Сборка

Сборка проверена на aarch64 (Ubuntu 24.04, arm64) без Android Studio.

## Тулчейн

| Компонент | Путь | Примечание |
|---|---|---|
| JDK 21 (полный, с `jlink`) | `/usr/lib/jvm/java-21-openjdk-arm64` | `openjdk-21-jdk`, не `-headless`: AGP вызывает `jlink` |
| Gradle 8.7 | `/opt/gradle/gradle-8.7` | AGP 8.5.2 требует 8.7+ |
| Android SDK | `/opt/android-sdk` | `platforms;android-34`, `build-tools;34.0.0` |
| qemu-user-static | `/usr/bin/qemu-x86_64-static` | для `aapt2` |

```bash
apt-get install -y openjdk-21-jdk unzip qemu-user-static
curl -fL -o /tmp/cmdline.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
python3 -m zipfile -e /tmp/cmdline.zip /opt/android-sdk/cmdline-tools/
mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest
yes | /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/opt/android-sdk --licenses
/opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/opt/android-sdk \
    "platform-tools" "platforms;android-34" "build-tools;34.0.0"
```

## aapt2 на arm64

Google поставляет `aapt2` только как x86_64 ELF. Нужны x86_64-библиотеки и
обёртка (файл обязательно должен называться `aapt2`, AGP проверяет имя):

```bash
# 1) amd64-библиотеки. ports.ubuntu.com НЕ содержит amd64 — нужен archive.ubuntu.com
dpkg --add-architecture amd64
printf 'deb [arch=amd64] http://archive.ubuntu.com/ubuntu noble main universe\ndeb [arch=amd64] http://archive.ubuntu.com/ubuntu noble-updates main universe\n' \
  > /etc/apt/sources.list.d/amd64.list
apt-get update && apt-get install -y libc6:amd64 libstdc++6:amd64 zlib1g:amd64 libgcc-s1:amd64

# 2) обёртка
mkdir -p /opt/aapt2
cat > /opt/aapt2/aapt2 <<'EOF'
#!/bin/sh
exec qemu-x86_64-static /opt/android-sdk/build-tools/34.0.0/aapt2 "$@"
EOF
chmod +x /opt/aapt2/aapt2
/opt/aapt2/aapt2 version   # Android Asset Packaging Tool (aapt) 2.19-10229193
```

`gradle.properties`:

```properties
android.aapt2FromMavenOverride=/opt/aapt2/aapt2
```

Если `gcc-14-base:amd64` конфликтует с arm64-версией по общему doc-файлу:

```bash
dpkg --force-overwrite -i /var/cache/apt/archives/gcc-14-base_*_amd64.deb
apt-get -f install -y
```

## Ключ подписи

```bash
cd parental
PASS=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))")
keytool -genkeypair -keystore keystore.jks -alias homeguard -keyalg RSA -keysize 4096 \
  -validity 10950 -storepass "$PASS" -keypass "$PASS" \
  -dname "CN=HomeGuard, O=HomeLab, C=RU"
cat > keystore.properties <<EOF
storeFile=keystore.jks
storePassword=$PASS
keyAlias=homeguard
keyPassword=$PASS
EOF
chmod 600 keystore.jks keystore.properties
```

`keystore.jks` и `keystore.properties` в `.gitignore`. Копия пароля —
`~/.config/opencode/secrets/homeguard.env` (chmod 600), не печатать.

## Сборка

```bash
cd parental
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-arm64
/opt/gradle/gradle-8.7/bin/gradle assembleRelease --no-daemon
# или
sh tools/build.sh      # + dist/, SHA256SUMS, проверка подписи
```

Результат: `agent/build/outputs/apk/release/agent-release.apk`,
`console/build/outputs/apk/release/console-release.apk`,
копии в `dist/agent-1.0.0.apk`, `dist/console-1.0.0.apk`.

Проверка:

```bash
/opt/android-sdk/build-tools/34.0.0/apksigner verify -v dist/agent-1.0.0.apk
/opt/aapt2/aapt2 dump badging dist/agent-1.0.0.apk | head -5
```

## Версии

`agent/build.gradle` и `console/build.gradle`: `versionCode` +1,
`versionName` — семантическая. Оба APK подписываются одним ключом; обновление
агента на устройстве с Device Owner проходит обычным `adb install -r`
(подпись та же).

## Типовые ошибки

| Сообщение | Причина |
|---|---|
| `Custom AAPT2 location does not point to an AAPT2 executable` | файл обёртки назван не `aapt2` или не исполняемый |
| `jlink executable ... does not exist` | установлен `-headless` JDK; нужен полный `openjdk-21-jdk` |
| `Unable to locate package openjdk-21-jdk-headless` | не выполнен `apt-get update` |
| `qemu-x86_64-static: Could not open '/lib64/ld-linux-x86-64.so.2'` | не установлены amd64-библиотеки |
| `Not allowed to set the device owner...` | на телефоне есть аккаунты/пользователи — нужен сброс |
