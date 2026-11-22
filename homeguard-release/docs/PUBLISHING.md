# Публикация репозитория

## 1. Что уже готово

* Исходники агенты и консоли, тесты протокола, скрипты сборки.
* Документация: `README.md`, `CHANGELOG.md`, `docs/*.md`.
* Лицензия MIT, `.gitignore`, примеры конфигов, CI
  (`.github/workflows/ci.yml`).
* Подписанные APK и контрольные суммы в `dist/`.

Секретов в каталоге нет: `local.properties`, `keystore.properties`,
`keystore.jks` и `.gradle/` намеренно не копируются.

## 2. Первый push

```bash
cd homeguard-release
git init
git add .
git commit -m "HomeGuard: offline parental control, initial public release"
git branch -M main
git remote add origin <URL_ВАШЕГО_REPO>
git push -u origin main
```

Перед `git add .` проверьте, что в каталоге нет локальных файлов из
`.gitignore` и что в документации остались только адреса-примеры.

## 3. Релиз

1. Поднимите версии в `agent/build.gradle` и `console/build.gradle`.
2. Соберите подписанный релиз: `sh tools/build.sh` (нужны свой keystore
   и `keystore.properties` — не коммитьте их).
3. Добавьте запись в `CHANGELOG.md`, закоммитьте и поставьте тег `vX.Y.Z`.
4. В GitHub Releases прикрепите `dist/agent-*.apk`, `dist/console-*.apk`
   и `dist/SHA256SUMS`; в описании дайте контрольные суммы и напоминание:
   протокол 1.4.0 ↔ 1.3.0 обновляется парой.

## 4. Что не публиковать никогда

* keystore, пароли, токены, HMAC-секреты;
* реальные IP, MAC, DDNS-домена, серийные номера устройств;
* логи, бэкапы консоли (`.hgbak`), конфиги WireGuard с приватными ключами;
* скриншоты с личными данными.
