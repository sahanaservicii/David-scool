# Караоке-мост (локальный минимум)

`karaoke_bridge.py` — детерминированный мост «сигнал → видео URL». Только stdlib,
без облака и без установки пакетов. Он **не управляет Алисой и не включает ТВ сам**:
он подготавливает локальное видео и отдаёт команду на проигрывание через
настраиваемый `play_cmd`.

## Как работает

1. Следит за появлением файла `inbox/karaoke.play`.
2. Берёт видео: из строки `video=/путь/к/файлу` в триггере, иначе самый свежий
   `*.(mp4|mkv|webm|avi|mov)` в `inbox`.
3. Проверяет, что файл не заглушка (`min_video_bytes`, по умолчанию 1 МиБ).
4. Поднимает HTTP-сервер `http://<IP>:8766/video` с поддержкой Range.
5. Пишет `homelab/state/karaoke_current.json`, шлёт уведомление на телефон
   и выполняет `play_cmd` (если задан).
6. Переименовывает триггер в `karaoke.play.done.<timestamp>` (или `.failed.`).

## Формат триггера

Пустой файл — взять свежее видео из `inbox`. Или:

```
video=/root/workspace/inbox/karaoke.mp4
```

## Настройка

Править `homelab/karaoke_bridge.json`:

- `play_cmd` — команда запуска на ТВ. Примеры (нужен соответствующий инструмент):
  - `python3 /path/to/dlnacast.py {url}` — DLNA-контроллер;
  - `python3 homelab.py tv shell am start -d {url}` — локальный ADB на ТВ;
  - оставьте `""`, чтобы только готовить URL и уведомление.
- `http_port`, `bind`, `probe_host` (адрес для определения собственного IP),
  `min_video_bytes`, `notify`, `poll_seconds`.
- `--once` без `--dry-run` после обработки триггера **оставляет HTTP-сервер
  запущенным** до Ctrl+C — иначе URL успевал исчезнуть вместе с процессом.

## Запуск

```bash
cd /root/workspace/homelab
python3 karaoke_bridge.py                 # постоянно
python3 karaoke_bridge.py --once          # один триггер
python3 karaoke_bridge.py --dry-run --once # проверка без сервера и команд
```

Лог: `homelab/state/karaoke_bridge.log`. Текущее состояние:
`homelab/state/karaoke_current.json`.

## Что не закрыто (честные разрывы)

- Алиса/Яндекс — облако; офлайн мост не видит «выбор караоке» в приложении.
- Нет доступа к `192.168.0.0/24`, нет IP/модели Samsung, нет ADB и реального
  видеофайла. Поэтому end-to-end «голос → экран» сейчас недоступен.
- Samsung Tizen не имеет нативного Google Cast; нужен DLNA (AllShare) или
  внешний Cast-стик. YouTube额外 требует рабочий интернет-апстрим (сейчас мертв).
