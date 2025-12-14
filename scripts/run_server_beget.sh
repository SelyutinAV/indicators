#!/bin/bash
# Скрипт запуска Django сервера на BeGet
# Использование: ./run_server_beget.sh [PORT]

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Параметры по умолчанию
PORT=${1:-8001}
HOST="0.0.0.0"
# Автоматическое определение пути проекта
if [ "$USER" = "root" ]; then
    PROJECT_DIR="/root/models"
else
    PROJECT_DIR="/home/$USER/models"
fi

echo -e "${GREEN}🚀 Запуск Django сервера на BeGet${NC}"
echo "   Порт: $PORT"
echo "   Хост: $HOST"
echo ""

# Переход в директорию проекта
cd "$PROJECT_DIR" || {
    echo -e "${RED}❌ Ошибка: Директория $PROJECT_DIR не найдена!${NC}"
    exit 1
}

# Активация виртуального окружения
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Виртуальное окружение не найдено!${NC}"
    echo "   Выполните сначала: ./scripts/deploy_beget.sh"
    exit 1
fi

source venv/bin/activate

# Переход в директорию back
cd back || {
    echo -e "${RED}❌ Директория back не найдена!${NC}"
    exit 1
}

# Проверка занятости порта
if command -v lsof > /dev/null 2>&1; then
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${YELLOW}⚠️  Порт $PORT занят!${NC}"
        echo "   Остановите процесс или используйте другой порт"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Порт $PORT свободен${NC}"
echo ""

# Выбор способа запуска
echo -e "${YELLOW}Выберите способ запуска:${NC}"
echo "   1) Gunicorn (рекомендуется для production)"
echo "   2) Django runserver (для разработки)"
read -p "Ваш выбор [1]: " choice
choice=${choice:-1}

case $choice in
    1)
        echo -e "${GREEN}🚀 Запуск через Gunicorn...${NC}"
        echo ""
        echo "   Сервер будет доступен по адресу:"
        echo "   http://217.26.25.154:$PORT"
        echo ""
        echo "   Для остановки нажмите Ctrl+C"
        echo ""
        
        # Запуск через gunicorn
        gunicorn indicators_project.wsgi:application \
            --bind $HOST:$PORT \
            --workers 3 \
            --timeout 120 \
            --access-logfile - \
            --error-logfile -
        ;;
    2)
        echo -e "${GREEN}🚀 Запуск через Django runserver...${NC}"
        echo ""
        echo "   Сервер будет доступен по адресу:"
        echo "   http://217.26.25.154:$PORT"
        echo ""
        echo "   Для остановки нажмите Ctrl+C"
        echo ""
        
        python manage.py runserver $HOST:$PORT
        ;;
    *)
        echo -e "${RED}❌ Неверный выбор!${NC}"
        exit 1
        ;;
esac

