#!/bin/bash
# Скрипт развертывания на сервере BeGet
# Использование: ./deploy_beget.sh

set -e  # Остановка при ошибке

echo "🚀 Начало развертывания на BeGet..."

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Переменные
# Автоматическое определение пути проекта
if [ "$USER" = "root" ]; then
    PROJECT_DIR="/root/models"
else
    PROJECT_DIR="/home/$USER/models"
fi
GIT_REPO="https://github.com/SelyutinAV/indicators.git"
BRANCH="main"  # Ветка для развертывания
PORT=8001
HOST="0.0.0.0"

echo -e "${YELLOW}📋 Параметры развертывания:${NC}"
echo "   Директория проекта: $PROJECT_DIR"
echo "   Git репозиторий: $GIT_REPO"
echo "   Ветка: $BRANCH"
echo "   Порт: $PORT"
echo "   Хост: $HOST"
echo ""

# Проверка наличия git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git не установлен! Установите git и повторите попытку.${NC}"
    exit 1
fi

# Клонирование или обновление репозитория
if [ -d "$PROJECT_DIR/.git" ]; then
    echo -e "${GREEN}📥 Обновление кода из репозитория...${NC}"
    cd "$PROJECT_DIR"
    
    # Сохраняем локальные изменения (если есть)
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}⚠️  Обнаружены локальные изменения. Создание резервной копии...${NC}"
        git stash save "Backup before deploy $(date +%Y%m%d_%H%M%S)"
    fi
    
    # Переключение на нужную ветку
    git fetch origin
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
        echo -e "${YELLOW}Переключение на ветку $BRANCH...${NC}"
        git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" "origin/$BRANCH"
    fi
    
    # Обновление кода
    git pull origin "$BRANCH"
    echo -e "${GREEN}✅ Код обновлен${NC}"
else
    # Клонирование репозитория
    echo -e "${GREEN}📥 Клонирование репозитория...${NC}"
    
    # Создаем родительскую директорию, если не существует
    PARENT_DIR=$(dirname "$PROJECT_DIR")
    if [ ! -d "$PARENT_DIR" ]; then
        echo -e "${YELLOW}Создание родительской директории: $PARENT_DIR${NC}"
        mkdir -p "$PARENT_DIR"
    fi
    
    # Если директория существует, но не является git репозиторием
    if [ -d "$PROJECT_DIR" ] && [ ! -d "$PROJECT_DIR/.git" ]; then
        echo -e "${YELLOW}⚠️  Директория $PROJECT_DIR существует, но не является git репозиторием${NC}"
        echo "   Перемещение в резервную копию..."
        BACKUP_NAME="${PROJECT_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
        mv "$PROJECT_DIR" "$BACKUP_NAME"
        echo -e "${GREEN}✅ Резервная копия создана: $BACKUP_NAME${NC}"
    fi
    
    # Клонирование
    cd "$PARENT_DIR"
    PROJECT_NAME=$(basename "$PROJECT_DIR")
    echo -e "${YELLOW}Клонирование из $GIT_REPO в $PROJECT_NAME...${NC}"
    git clone -b "$BRANCH" "$GIT_REPO" "$PROJECT_NAME"
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✅ Репозиторий склонирован${NC}"
fi

# Переход в директорию проекта (если еще не там)
cd "$PROJECT_DIR" || {
    echo -e "${RED}❌ Ошибка: Не удалось перейти в директорию $PROJECT_DIR!${NC}"
    exit 1
}

# Активация виртуального окружения
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ Активация виртуального окружения...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}⚠️  Виртуальное окружение не найдено. Создание...${NC}"
    python3 -m venv venv
    source venv/bin/activate
fi

# Обновление pip
echo -e "${GREEN}📦 Обновление pip...${NC}"
pip install --upgrade pip

# Установка зависимостей
echo -e "${GREEN}📦 Установка зависимостей...${NC}"
pip install -r requirements.txt
pip install -r back/requirements.txt

# Установка gunicorn для production
echo -e "${GREEN}📦 Установка gunicorn...${NC}"
pip install gunicorn

# Сбор статических файлов
echo -e "${GREEN}📦 Сбор статических файлов...${NC}"
cd back
python manage.py collectstatic --noinput

# Применение миграций
echo -e "${GREEN}🔄 Применение миграций...${NC}"
python manage.py migrate --noinput

# Создание суперпользователя (если нужно)
echo -e "${YELLOW}💡 Для создания суперпользователя выполните:${NC}"
echo "   cd $PROJECT_DIR/back && python manage.py createsuperuser"

echo -e "${GREEN}✅ Развертывание завершено!${NC}"
echo ""
echo -e "${YELLOW}📝 Следующие шаги:${NC}"
echo "   1. Проверьте настройки в back/indicators_project/settings.py"
echo "   2. Убедитесь, что ALLOWED_HOSTS содержит IP сервера: 217.26.25.154"
echo "   3. Запустите сервер: ./scripts/run_server_beget.sh"
echo ""

