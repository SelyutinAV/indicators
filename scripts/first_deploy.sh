#!/bin/bash
# Скрипт первого развертывания на сервере
# Использование: ./first_deploy.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Автоматическое определение пути
if [ "$USER" = "root" ]; then
    PROJECT_DIR="/root/models"
else
    PROJECT_DIR="/home/$USER/models"
fi

GIT_REPO="https://github.com/SelyutinAV/indicators.git"
BRANCH="main"

echo -e "${GREEN}🚀 Первое развертывание на сервере${NC}"
echo -e "${YELLOW}Пользователь: $USER${NC}"
echo -e "${YELLOW}Директория проекта: $PROJECT_DIR${NC}"
echo ""

# Проверка наличия git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git не установлен! Установка...${NC}"
    apt-get update
    apt-get install -y git
fi

# Клонирование репозитория
if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠️  Директория $PROJECT_DIR уже существует${NC}"
    read -p "Удалить и пересоздать? (y/N): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        rm -rf "$PROJECT_DIR"
        echo -e "${GREEN}✅ Директория удалена${NC}"
    else
        echo -e "${YELLOW}Используем существующую директорию${NC}"
        cd "$PROJECT_DIR"
        if [ -d ".git" ]; then
            echo -e "${GREEN}✅ Это уже git репозиторий, запускаем обычное развертывание...${NC}"
            ./scripts/deploy_beget.sh
            exit 0
        fi
    fi
fi

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${GREEN}📥 Клонирование репозитория...${NC}"
    cd "$(dirname $PROJECT_DIR)"
    git clone -b "$BRANCH" "$GIT_REPO" "$(basename $PROJECT_DIR)"
    echo -e "${GREEN}✅ Репозиторий склонирован${NC}"
fi

# Переход в директорию проекта
cd "$PROJECT_DIR" || {
    echo -e "${RED}❌ Ошибка: Не удалось перейти в директорию $PROJECT_DIR!${NC}"
    exit 1
}

# Запуск скрипта развертывания
echo -e "${GREEN}📦 Запуск развертывания...${NC}"
chmod +x scripts/*.sh
./scripts/deploy_beget.sh

echo ""
echo -e "${GREEN}✅ Первое развертывание завершено!${NC}"
echo ""
echo -e "${YELLOW}📝 Следующие шаги:${NC}"
echo "   1. Создайте суперпользователя:"
echo "      cd $PROJECT_DIR/back"
echo "      source ../venv/bin/activate"
echo "      python manage.py createsuperuser"
echo ""
echo "   2. Запустите сервер:"
echo "      cd $PROJECT_DIR"
echo "      ./scripts/run_server_beget.sh 8001"
echo ""

