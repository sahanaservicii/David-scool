# Сборка

Проект собирается без Android Studio: Java 17+, Gradle 8.7+, Android SDK 34.
Сборка проверена на x86_64 и на aarch64 (Ubuntu 24.04, arm64).

## Тулчейн

| Компонент | Версия | Примечание |
|---|---|---|
| JDK | 17+ (проверено на 21) | нужен полный JDK с `jlink`, не `-headless` (AGP вызывает `jlink`) |
| Gradle | 8.7 | AGP 8.5.2 требует 8.7+ |
| Android SDK | `platforms;android-34`, `build-tools;34.0.0` | `platform-tools` для `adb` |

Пути задаются через окружение, в репозиторий не пишутся:

```bash
export ANDROID_SDK_ROOT="$HOME/Android/Sdk"   # или ANDROID_HOME
export JAVA_HOME=/path/to/jdk
cp local.properties.example local.properties  # при желании sdk.dir=... вместо env
cp keystore.properties.example keystore.properties  # только для релизной подписи
```

## Тесты и сборка

```bash
sh tools/test.sh          # 34 офлайн-проверки протокола, без устройства и сети
gradle --no-daemon assembleDebug lintDebug
sh tools/build.sh         # подписанный релиз + dist/ + SHA256SUMS + проверка подписи
```

`tools/*.sh` читают `ANDROID_SDK_ROOT`/`ANDROID_HOME`, `JAVA_HOME` и `GRADLE`
(по умолчанию `gradle` из PATH). Результат:

* `agent/build/outputs/apk/release/agent-release.apk` → `dist/agent-1.4.0.apk`
* `console/build/outputs/apk/release/console-release.apk` → `dist/console-1.4.2.apk`

Проверка подписанного APK:

```bash
"$ANDROID_SDK_ROOT/build-tools/34.0.0/apksigner" verify -v dist/agent-1.4.0.apk
```

## Ключ подписи

`keystore.jks` и `keystore.properties` не коммитятся (см. `.gitignore`).
Создайте свой ключ один раз и храните копию в надёжном месте — потеря ключа
означает, что обновление не установится поверх прежнего APK:

```bash
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

Пароль и приватный ключ не должны попадать в чат, логи или репозиторий.

## Сборка на arm64 (опционально)

Google поставляет `aapt2` как x86_64 ELF. На arm64 нужны amd64-библиотеки и
обёртка (имя файла обязательно `aapt2`, AGP проверяет имя):

```bash
dpkg --add-architecture amd64
printf 'deb [arch=amd64] http://archive.ubuntu.com/ubuntu noble main universe\ndeb [arch=amd64] http://archive.ubuntu.com/ubuntu noble-updates main universe\n' \
  > /etc/apt/sources.list.d/amd64.list
apt-get update && apt-get install -y libc6:amd64 libstdc++6:amd64 zlib1g:amd64 libgcc-s1:amd64 qemu-user-static

mkdir -p "$HOME/.local/aapt2"
cat > "$HOME/.local/aapt2/aapt2" <<'EOF'
#!/bin/sh
exec qemu-x86_64-static "$ANDROID_SDK_ROOT/build-tools/34.0.0/aapt2" "$@"
EOF
chmod +x "$HOME/.local/aapt2/aapt2"
```

Затем раскомментируйте в `gradle.properties` строку
`android.aapt2FromMavenOverride=...` и укажите путь к обёртке.

## Версии

`agent/build.gradle` и `console/build.gradle`: `versionCode` +1,
`versionName` — семантическая. Оба APK подписываются одним ключом; обновление
агента на устройстве с Device Owner проходит обычным `adb install -r`
(подпись та же). Протокол 1.4.0/1.3.0 несовместим со старой парой:
сначала обновляйте консоль, потом агента.

## Типовые ошибки

| Сообщение | Причина |
|---|---|
| `Custom AAPT2 location does not point to an AAPT2 executable` | обёртка названа не `aapt2` или не исполняемая |
| `jlink executable ... does not exist` | установлен `-headless` JDK; нужен полный JDK |
| `qemu-x86_64-static: Could not open '/lib64/ld-linux-x86-64.so.2'` | не установлены amd64-библиотеки |
| `android.jar not found` | не задан `ANDROID_SDK_ROOT`/`ANDROID_HOME` |
| `Not allowed to set the device owner...` | на телефоне есть аккаунты/пользователи — нужен сброс |
