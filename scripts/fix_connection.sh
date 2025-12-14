#!/bin/bash
# Скрипт исправления проблем с подключением
# Использование: ./fix_connection.sh [PORT]

PORT=${1:-8001}

echo "🔧 Исправление проблем с подключением..."
echo ""

# 1. Проверка и открытие порта в файрволе
echo "🔥 Проверка файрвола..."

if command -v ufw > /dev/null 2>&1; then
    echo "   Используется ufw"
    if ufw status | grep -q "Status: active"; then
        echo "   Файрвол активен, открываем порт $PORT..."
        ufw allow $PORT/tcp
        echo "   ✅ Порт $PORT открыт в ufw"
    else
        echo "   Файрвол неактивен"
    fi
elif command -v iptables > /dev/null 2>&1; then
    echo "   Используется iptables"
    if iptables -C INPUT -p tcp --dport $PORT -j ACCEPT 2>/dev/null; then
        echo "   ✅ Порт $PORT уже открыт в iptables"
    else
        echo "   Открываем порт $PORT в iptables..."
        iptables -A INPUT -p tcp --dport $PORT -j ACCEPT
        echo "   ✅ Порт $PORT открыт"
        echo "   ⚠️  Для сохранения правил после перезагрузки выполните:"
        echo "      iptables-save > /etc/iptables/rules.v4"
    fi
else
    echo "   Файрвол не найден"
fi

echo ""
echo "📊 Проверка процессов на порту $PORT:"
if command -v lsof > /dev/null 2>&1; then
    PID=$(lsof -ti :$PORT)
    if [ -n "$PID" ]; then
        echo "   Найдено: PID $PID"
        ps aux | grep $PID | grep -v grep
    else
        echo "   Порт $PORT свободен"
    fi
fi

echo ""
echo "💡 Следующие шаги:"
echo "   1. Убедитесь, что сервер запущен:"
echo "      cd /root/models"
echo "      ./scripts/run_server_beget.sh $PORT"
echo ""
echo "   2. Проверьте, что сервер слушает на 0.0.0.0:$PORT"
echo ""
echo "   3. Проверьте доступность:"
echo "      curl http://127.0.0.1:$PORT"
echo "      curl http://217.26.25.154:$PORT"

