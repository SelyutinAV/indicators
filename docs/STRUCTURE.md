# Структура проекта

Проект организован по принципу разделения на модули для удобства разработки и поддержки.

## Структура директорий

```
models/
├── back/                    # Backend (Django приложение)
│   ├── indicators/          # Django app с моделями и логикой
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── admin.py
│   │   ├── urls.py
│   │   ├── generators.py
│   │   ├── formula_parser.py
│   │   └── migrations/
│   ├── indicators_project/   # Настройки Django проекта
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── manage.py            # Django management script
│   └── requirements.txt     # Зависимости (копия из корня)
│
├── front/                   # Frontend (шаблоны и статика)
│   ├── templates/           # HTML шаблоны
│   │   ├── base.html
│   │   └── indicators/
│   ├── static/              # Исходные статические файлы
│   │   └── indicators/
│   │       └── css/
│   └── staticfiles/         # Собранные статические файлы (генерируется)
│
├── db/                      # База данных
│   └── db.sqlite3          # SQLite база данных
│
├── docs/                    # Документация
│   ├── README.md           # Полная документация
│   ├── QUICKSTART.md       # Быстрый старт
│   └── STRUCTURE.md        # Описание структуры (этот файл)
│
├── scripts/                 # Вспомогательные скрипты
│   ├── run_server.py       # Скрипт запуска сервера
│   └── create_superuser.py # Скрипт создания админа
│
├── config/                  # Конфигурационные файлы
│   ├── .vscode/            # Настройки VSCode/Cursor
│   │   ├── tasks.json
│   │   ├── launch.json
│   │   └── settings.json
│   └── .gitignore          # Правила игнорирования Git
│
├── venv/                   # Виртуальное окружение Python
├── requirements.txt        # Зависимости Python
├── .gitignore             # Git ignore (копия из config/)
└── README.md              # Главный README проекта
```

## Описание директорий

### `back/`
Содержит весь backend код на Django:
- **indicators/** - основное Django приложение с бизнес-логикой
  - `models.py` - модели данных
  - `views.py` - представления (контроллеры)
  - `admin.py` - настройка Django Admin
  - `urls.py` - маршруты приложения
  - `generators.py` - генерация тестовых данных
  - `formula_parser.py` - парсинг и валидация формул
  - `migrations/` - миграции базы данных
- **indicators_project/** - настройки проекта Django
  - `settings.py` - основные настройки
  - `urls.py` - корневые маршруты
  - `wsgi.py` / `asgi.py` - интерфейсы для деплоя
- **manage.py** - утилита для управления Django проектом

### `front/`
Содержит все файлы, связанные с фронтендом:
- **templates/** - HTML шаблоны Django
  - `base.html` - базовый шаблон с навигацией
  - `indicators/` - шаблоны для работы с показателями
- **static/** - исходные CSS, JS, изображения
  - `indicators/css/style.css` - основные стили
- **staticfiles/** - собранные статические файлы (создается командой `collectstatic`)

### `db/`
Содержит файлы базы данных:
- **db.sqlite3** - SQLite база данных (в продакшене лучше использовать PostgreSQL)
- Здесь же можно хранить дампы и бэкапы БД

### `docs/`
Документация проекта:
- **README.md** - основная документация с описанием возможностей
- **QUICKSTART.md** - быстрый старт с примерами
- **STRUCTURE.md** - описание структуры (этот файл)

### `scripts/`
Вспомогательные скрипты для разработки:
- **run_server.py** - запуск сервера с проверкой порта и автоматическим перезапуском
- **create_superuser.py** - создание администратора с дефолтными учетными данными

### `config/`
Конфигурационные файлы:
- **.vscode/** - настройки для VSCode/Cursor
  - `tasks.json` - задачи для запуска (сервер, миграции и т.д.)
  - `launch.json` - конфигурации отладки
  - `settings.json` - настройки Python интерпретатора
- **.gitignore** - правила игнорирования файлов Git

## Преимущества такой структуры

1. **Разделение ответственности** - четкое разделение frontend и backend
2. **Удобство разработки** - легко найти нужные файлы
3. **Масштабируемость** - легко добавлять новые компоненты
4. **Чистота проекта** - все файлы на своих местах
5. **Готовность к продакшену** - структура подходит для деплоя
6. **Командная работа** - разные разработчики могут работать над разными частями

## Работа с проектом

### Запуск сервера
```bash
# Из корня проекта
python scripts/run_server.py

# Или через Cursor/VSCode: Tasks → "Запустить Django сервер"
```

### Работа с Django
```bash
cd back
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Сборка статики
```bash
cd back
python manage.py collectstatic
```

### Создание суперпользователя
```bash
python scripts/create_superuser.py
```

## Миграции базы данных

Миграции Django находятся в `back/indicators/migrations/`.
База данных - в `db/db.sqlite3`.

При изменении моделей:
```bash
cd back
python manage.py makemigrations
python manage.py migrate
```

## Настройки путей

Все пути настроены в `back/indicators_project/settings.py`:
- `BASE_DIR` - указывает на `back/`
- `PROJECT_ROOT` - указывает на корень проекта (`models/`)
- База данных: `PROJECT_ROOT / 'db' / 'db.sqlite3'`
- Шаблоны: `PROJECT_ROOT / 'front' / 'templates'`
- Статика: `PROJECT_ROOT / 'front' / 'static'`

## Дополнительные директории (опционально)

Можно добавить:
- **`tests/`** - тесты проекта
- **`logs/`** - логи приложения
- **`data/`** - данные для импорта/экспорта
- **`deploy/`** - скрипты для деплоя
- **`api/`** - API документация (если будет REST API)
