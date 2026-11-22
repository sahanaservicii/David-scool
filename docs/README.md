# Интерактивные домашки

Сайт для сына (3-й класс): домашние задания превращаются в короткие игры —
викторину, примеры на скорость, карточки с английскими словами.

## Как добавить новую домашку

1. Папа присылает текст задания из приложения (файл в `inbox/` или сообщением).
2. Добавляем новый объект в конец массива `lessons` в `assets/data.js`, копируя
   структуру существующего дня: дата, предметы, вопросы/слова/количество примеров.
3. Коммит и push — GitHub Pages обновит сайт автоматически.

Менять `index.html`, `style.css` и `app.js` для новых заданий не нужно.

## Как обновить сайт

```bash
cd /root/workspace
git add docs/
git commit -m "site: новая домашка"
git push origin main
```

## Публикация (один раз)

В настройках репозитория `David-scool`: Settings → Pages → Source:
**Deploy from a branch** → Branch `main`, папка `/docs` → Save.
Ссылка: `https://sahanaservicii.github.io/David-scool/`

## Офлайн-проверка

```bash
cd /root/workspace/docs
python3 -m http.server 8080 --bind 127.0.0.1
# opened http://127.0.0.1:8080/
```

Прогресс и звёздочки хранятся в браузере (localStorage), сервер не нужен.
