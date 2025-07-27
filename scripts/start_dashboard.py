#!/usr/bin/env python3
"""
Скрипт для запуска веб-dashboard аналитики
"""

import sys
import os

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics.dashboard import dashboard

if __name__ == "__main__":
    if dashboard:
        print("🌐 Запуск Analytics Dashboard...")
        print("📊 Доступ: http://127.0.0.1:8080")
        print("🔄 Автообновление каждые 30 секунд")
        print("⏹️  Остановка: Ctrl+C")
        dashboard.run(debug=False)
    else:
        print("❌ Flask не установлен")
        print("📦 Установите Flask: pip install flask")
