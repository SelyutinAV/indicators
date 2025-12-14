# Быстрое развертывание на BeGet

## Быстрый старт

### 1. Подключитесь к серверу
```bash
ssh ваш_username@217.26.25.154
```

### 2. Клонируйте репозиторий на сервере
```bash
# На сервере
cd ~
git clone https://github.com/SelyutinAV/indicators.git models
cd models
```

### 3. Отредактируйте скрипты
```bash
# Узнайте ваш username
whoami

# Отредактируйте пути в скриптах
nano scripts/deploy_beget.sh
# Замените /home/u1234567/models на /home/$(whoami)/models

nano scripts/run_server_beget.sh
# Замените /home/u1234567/models на /home/$(whoami)/models
```

### 4. Запустите развертывание
```bash
cd ~/models
chmod +x scripts/*.sh
./scripts/deploy_beget.sh
```

### 5. Создайте суперпользователя
```bash
cd ~/models/back
source ../venv/bin/activate
python manage.py createsuperuser
```

### 6. Запустите сервер
```bash
cd ~/models
# В screen/tmux для постоянной работы
screen -S django
./scripts/run_server_beget.sh 8001
# Отключитесь: Ctrl+A, затем D
```

### 7. Проверьте работу
Откройте в браузере: `http://217.26.25.154:8001`

## Важные замечания

- **Порт:** Используется порт **8001** (8000 уже занят)
- **Username:** Замените `u1234567` на ваш реальный username на BeGet
- **Путь:** Убедитесь, что путь к проекту правильный в скриптах
- **Git:** Скрипт автоматически клонирует/обновляет код из репозитория https://github.com/SelyutinAV/indicators.git

## Обновление кода

При обновлении кода просто запустите скрипт развертывания снова:
```bash
cd ~/models
./scripts/deploy_beget.sh
```
Скрипт автоматически обновит код из Git репозитория.

## Полная инструкция

См. `docs/DEPLOY_BEGET.md` для подробной информации.

