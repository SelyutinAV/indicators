#!/bin/bash
# Скрипт быстрого запуска Django сервера в фоне
# Использование: ./start_django.sh [PORT]

PORT=${1:-8001}

# Автоматическое определение пути проекта
if [ "$USER" = "root" ]; then
    PROJECT_DIR="/root/models"
else
    PROJECT_DIR="/home/$USER/models"
fi

cd "$PROJECT_DIR" || exit 1

# Проверка, не запущен ли уже сервер
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Порт $PORT уже занят!"
    echo "   Остановите существующий процесс или используйте другой порт"
    exit 1
fi

# Запуск в screen
echo "🚀 Запуск Django сервера на порту $PORT в screen..."
screen -dmS django bash -c "cd $PROJECT_DIR && source venv/bin/activate && cd back && SERVER_MODE=1 ./../scripts/run_server_beget.sh $PORT"

sleep 2

# Проверка запуска
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "✅ Сервер запущен на порту $PORT"
    echo ""
    echo "📊 Информация:"
    echo "   URL: http://217.26.25.154:$PORT"
    echo "   Screen сессия: django"
    echo ""
    echo "💡 Команды для управления:"
    echo "   Просмотр логов: screen -r django"
    echo "   Остановка: screen -S django -X quit"
    echo "   Или: kill \$(lsof -ti :$PORT)"
else
    echo "❌ Не удалось запустить сервер"
    echo "   Проверьте логи: screen -r django"
fi

