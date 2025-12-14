# Инструкция по развертыванию на BeGet

## Подготовка

### 1. Подключение к серверу

```bash
ssh ваш_username@217.26.25.154
```

### 2. Определение вашего username на BeGet

Обычно username на BeGet имеет формат `u1234567`. Вы можете узнать его:
- В панели управления BeGet
- Выполнив команду `whoami` после подключения по SSH
- Проверив путь к домашней директории: `echo $HOME`

### 3. Обновление скриптов

Отредактируйте файлы `scripts/deploy_beget.sh` и `scripts/run_server_beget.sh`:
- Замените `/home/u1234567/models` на ваш реальный путь к проекту
- Убедитесь, что порт 8001 свободен (или выберите другой)

## Развертывание

### Шаг 1: Первое развертывание

Для первого развертывания у вас есть два варианта:

#### Вариант A: Клонирование репозитория вручную (рекомендуется)

```bash
# На сервере
cd ~
git clone https://github.com/SelyutinAV/indicators.git models
cd models

# Отредактируйте скрипт и укажите правильный путь
nano scripts/deploy_beget.sh
# Замените /home/u1234567/models на ваш реальный путь (например, /home/$(whoami)/models)

# Запустите развертывание
chmod +x scripts/*.sh
./scripts/deploy_beget.sh
```

#### Вариант B: Запуск скрипта из родительской директории

Если вы скачали скрипт отдельно или хотите запустить его до клонирования:

```bash
# На сервере
cd ~
# Скачайте скрипт (или создайте его вручную)
# Отредактируйте путь в скрипте
nano deploy_beget.sh
# Замените /home/u1234567/models на ваш реальный путь

# Запустите - скрипт автоматически клонирует репозиторий
chmod +x deploy_beget.sh
./deploy_beget.sh
```

### Шаг 2: Последующие обновления

Скрипт автоматически обновляет код из Git репозитория:
- **Репозиторий:** https://github.com/SelyutinAV/indicators.git
- **Ветка:** main (по умолчанию)

```bash
cd ~/models
./scripts/deploy_beget.sh
```

**Примечание:** Скрипт автоматически выполнит `git pull` для обновления кода, сохранит локальные изменения в stash (если есть), обновит зависимости и применит миграции.

```bash
cd ~/models
chmod +x scripts/*.sh
./scripts/deploy_beget.sh
```

Скрипт выполнит:
- **Клонирование/обновление кода** из Git репозитория
- Создание/активацию виртуального окружения
- Установку зависимостей
- Установку gunicorn
- Сбор статических файлов
- Применение миграций

### Шаг 3: Настройка переменных окружения (опционально)

Для production рекомендуется использовать переменные окружения:

```bash
# Добавьте в ~/.bashrc или создайте файл ~/models/.env
export DJANGO_DEBUG='False'
export DJANGO_SECRET_KEY='ваш_секретный_ключ_для_production'
export DJANGO_ALLOWED_HOSTS='217.26.25.154,yourdomain.com'
```

### Шаг 4: Создание суперпользователя

```bash
cd ~/models/back
source ../venv/bin/activate
python manage.py createsuperuser
```

### Шаг 5: Запуск сервера

#### Вариант A: Запуск через скрипт (для тестирования)
```bash
cd ~/models
./scripts/run_server_beget.sh 8001
```

#### Вариант B: Запуск через screen/tmux (для постоянной работы)

```bash
# Установка screen (если не установлен)
# На BeGet обычно уже установлен

# Создание сессии screen
screen -S django

# В сессии screen
cd ~/models
source venv/bin/activate
cd back
gunicorn indicators_project.wsgi:application \
    --bind 0.0.0.0:8001 \
    --workers 3 \
    --timeout 120 \
    --access-logfile ../logs/access.log \
    --error-logfile ../logs/error.log

# Отключение от screen: Ctrl+A, затем D
# Подключение к screen: screen -r django
```

#### Вариант C: Запуск через systemd (для автозапуска)

Создайте файл `/etc/systemd/system/django-models.service` (требуются права root):

```ini
[Unit]
Description=Django Models Application
After=network.target

[Service]
User=ваш_username
Group=ваш_username
WorkingDirectory=/home/ваш_username/models/back
Environment="PATH=/home/ваш_username/models/venv/bin"
ExecStart=/home/ваш_username/models/venv/bin/gunicorn \
    indicators_project.wsgi:application \
    --bind 0.0.0.0:8001 \
    --workers 3 \
    --timeout 120

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable django-models
sudo systemctl start django-models
sudo systemctl status django-models
```

## Проверка работы

После запуска сервера проверьте:

1. **Доступность сервера:**
   ```bash
   curl http://127.0.0.1:8001
   ```

2. **Доступность извне:**
   Откройте в браузере: `http://217.26.25.154:8001`

3. **Проверка порта:**
   ```bash
   netstat -tuln | grep 8001
   # или
   lsof -i :8001
   ```

## Настройка файрвола (если нужно)

На BeGet обычно порты открыты, но если нужно открыть порт вручную:

```bash
# Для iptables (если есть права)
sudo iptables -A INPUT -p tcp --dport 8001 -j ACCEPT
```

## Логи

Логи приложения можно найти:
- В консоли (если запущено через screen/tmux)
- В файлах `~/models/logs/access.log` и `~/models/logs/error.log` (если настроено)
- В systemd журнале: `sudo journalctl -u django-models -f`

## Обновление приложения

При обновлении кода просто запустите скрипт развертывания - он автоматически обновит код из Git:

```bash
cd ~/models
./scripts/deploy_beget.sh
# Скрипт автоматически выполнит git pull и обновит все зависимости
# Перезапустите сервер после обновления
```

**Примечание:** Скрипт автоматически:
- Обновляет код из репозитория (`git pull`)
- Сохраняет локальные изменения в stash (если есть)
- Обновляет зависимости
- Собирает статические файлы
- Применяет новые миграции

## Решение проблем

### Порт занят
```bash
# Найти процесс на порту
lsof -i :8001

# Остановить процесс
kill -9 PID
```

### Ошибки с правами доступа
```bash
# Проверьте права на директории
chmod -R 755 ~/models
chmod -R 644 ~/models/back/db/db.sqlite3
```

### Ошибки со статическими файлами
```bash
cd ~/models/back
source ../venv/bin/activate
python manage.py collectstatic --noinput
```

### Проблемы с базой данных
```bash
cd ~/models/back
source ../venv/bin/activate
python manage.py migrate
```

## Безопасность

⚠️ **Важно для production:**

1. Измените `SECRET_KEY` в `settings.py` или используйте переменную окружения
2. Установите `DEBUG = False` в production
3. Настройте `ALLOWED_HOSTS` правильно
4. Используйте HTTPS (настройте nginx/apache как reverse proxy)
5. Регулярно обновляйте зависимости
6. Делайте резервные копии базы данных

## Резервное копирование

```bash
# Создание резервной копии базы данных
cp ~/models/db/db.sqlite3 ~/models/db/db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)
```

## Контакты и поддержка

При возникновении проблем проверьте:
- Логи приложения
- Логи systemd (если используется)
- Статус процесса: `ps aux | grep gunicorn`
- Доступность порта: `netstat -tuln | grep 8001`

