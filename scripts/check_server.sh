#!/bin/bash
# Скрипт проверки состояния сервера
# Использование: ./check_server.sh [PORT]

PORT=${1:-8001}

echo "🔍 Проверка состояния сервера на порту $PORT..."
echo ""

# Проверка процессов
echo "📊 Процессы Python/Django:"
ps aux | grep -E "(python|gunicorn|django)" | grep -v grep || echo "   Нет запущенных процессов"

echo ""
echo "📊 Процессы на порту $PORT:"
if command -v lsof > /dev/null 2>&1; then
    lsof -i :$PORT || echo "   Порт $PORT не используется"
elif command -v netstat > /dev/null 2>&1; then
    netstat -tuln | grep ":$PORT" || echo "   Порт $PORT не используется"
else
    echo "   Не удалось проверить порт (lsof и netstat недоступны)"
fi

echo ""
echo "🌐 Проверка доступности порта:"
if command -v curl > /dev/null 2>&1; then
    echo "   Локально:"
    curl -s -o /dev/null -w "   HTTP статус: %{http_code}\n" http://127.0.0.1:$PORT || echo "   ❌ Недоступен локально"
    echo "   Снаружи:"
    curl -s -o /dev/null -w "   HTTP статус: %{http_code}\n" http://217.26.25.154:$PORT || echo "   ❌ Недоступен снаружи"
else
    echo "   curl не установлен, пропускаем проверку HTTP"
fi

echo ""
echo "🔥 Проверка файрвола:"
if command -v ufw > /dev/null 2>&1; then
    ufw status | grep $PORT || echo "   Порт $PORT не открыт в ufw"
elif command -v iptables > /dev/null 2>&1; then
    iptables -L -n | grep $PORT || echo "   Порт $PORT не найден в правилах iptables"
else
    echo "   Файрвол не найден или недоступен"
fi

echo ""
echo "💡 Рекомендации:"
echo "   1. Убедитесь, что сервер запущен: ./scripts/run_server_beget.sh $PORT"
echo "   2. Проверьте, что сервер слушает на 0.0.0.0, а не на 127.0.0.1"
echo "   3. Если используется файрвол, откройте порт:"
echo "      sudo ufw allow $PORT/tcp"
echo "      или"
echo "      sudo iptables -A INPUT -p tcp --dport $PORT -j ACCEPT"

