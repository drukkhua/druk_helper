#!/usr/bin/env python3
"""
Скрипт для проверки обновлений enhanced_ai_handlers.py
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath("."))


def check_update():
    """Проверяет, обновлены ли обработчики"""
    try:
        # Перезагружаем модуль
        import importlib

        # Импортируем и перезагружаем модуль
        from src.bot.handlers import enhanced_ai_handlers

        importlib.reload(enhanced_ai_handlers)

        print("✅ Enhanced AI handlers обновлены")

        # Проверяем наличие функции умной обрезки
        with open("src/bot/handlers/enhanced_ai_handlers.py", "r", encoding="utf-8") as f:
            content = f.read()

        if "умная обрезка" in content.lower():
            print("✅ Умная обрезка ответов активна")
        else:
            print("❌ Умная обрезка не найдена")

        if "различия найдены" in content.lower():
            print("✅ Улучшенный анализ различий активен")
        else:
            print("❌ Улучшенный анализ не найден")

        return True

    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False


if __name__ == "__main__":
    if check_update():
        print("\n🎉 Все обновления применены! Перезапустите бота для применения изменений.")
    else:
        print("\n❌ Обновления не применены.")
