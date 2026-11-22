# FreeVoice Android (клиент APK)

Android-приложение-обёртка (WebView) для доступа к веб-интерфейсу **Свободного Голос**.

## Как это работает
- Приложение открывает URL сервера FreeVoice (`python3 main.py --web ...`) во встроенном WebView.
- Голосовой ввод/вывод выполняются средствами веб-интерфейса и браузерного движка WebView (Web Speech API), при поддержке устройством.
- Серверная часть (навыки, поиск, LLM, заметки и т.д.) работает там, где запущен FreeVoice.

## Сборка (локально/офлайн, при наличии зависимостей)

Требования в окружении: JDK 17+ (проверено на 21), Android SDK (`/opt/android-sdk`, platform 34, build-tools 34.0.0), Gradle 8.7 (`/opt/gradle/gradle-8.7`), кэш AGP 8.5.2 в `~/.gradle/caches`.

```bash
export ANDROID_HOME=/opt/android-sdk
export ANDROID_SDK_ROOT=/opt/android-sdk
export JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-21-openjdk-arm64}
cd android-app

# Debug APK (оффлайн, если зависимости в кэше)
/opt/gradle/gradle-8.7/bin/gradle :app:assembleDebug --offline --stacktrace

# Результат:
# app/build/outputs/apk/debug/app-debug.apk
```

Установка на устройство (если доступен adb): `adb install -r app/build/outputs/apk/debug/app-debug.apk`

## Использование
1. Запустите сервер FreeVoice на устройстве/ПК в той же сети: `python3 main.py --web --host 0.0.0.0 --port 8766`.
2. Откройте приложение, укажите адрес (например `http://192.168.1.10:8766` или `http://127.0.0.1:8766`) и нажмите «Подключиться».
3. Разрешите микрофон при запросе для голосового ввода.

## Примечания
- Для локальных `http://` адресов включён cleartext traffic (`networkSecurityConfig`).
- Разрешения: `INTERNET`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, `ACCESS_NETWORK_STATE`.
- Если распознавание речи в WebView недоступно/требует сеть — это ограничение движка WebView/устройства; используйте текстовый ввод или подключите офлайн STT на стороне сервера.
- Release-сборка/подпись: настройте keystore и `signingConfigs` (см. `android-apk-build` skill / стандартный Gradle-процесс). Не коммитьте ключи.
