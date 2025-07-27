#!/bin/bash

# Скрипт безопасного запуска бота
# Останавливает старые процессы и запускает новый

echo "🔍 Проверка запущенных процессов бота..."
RUNNING_PIDS=$(pgrep -f "main.py")

if [ ! -z "$RUNNING_PIDS" ]; then
    echo "⚠️  Найдены запущенные процессы: $RUNNING_PIDS"
    echo "🛑 Останавливаем старые процессы..."
    pkill -f main.py
    sleep 2
    echo "✅ Старые процессы остановлены"
else
    echo "✅ Запущенных процессов не найдено"
fi

echo "🚀 Запускаем бот..."
cd /Volumes/work/TG_bots/Bot-answers
python main.py
