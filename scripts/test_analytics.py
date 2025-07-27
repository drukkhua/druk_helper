#!/usr/bin/env python3
"""
Скрипт для тестирования системы аналитики
Создает тестовые данные и показывает отчет
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics.analytics_service import analytics_service
from src.analytics.dashboard import create_simple_report
from src.ai.service import ai_service


async def test_analytics():
    """Тестирует систему аналитики"""
    print("🔬 Тестирование системы аналитики...")

    # Тестовые запросы
    test_queries = [
        "Скільки коштують візитки?",
        "Які терміни виготовлення футболок?",
        "Чи можна замовити листівки?",
        "Яка ціна на блокноти?",
        "Коли ви працюєте?",
        "Невідомий запрос про щось дивне",
        "Ще один незрозумілий запит",
        "Скільки коштують візитки?",  # Повтор
    ]

    print(f"📝 Тестування {len(test_queries)} запросів...")

    # Обрабатываем тестовые запросы
    for i, query in enumerate(test_queries, 1):
        user_id = 12345 + (i % 3)  # 3 разных пользователя
        print(f"  {i}. Обрабатываем: {query}")

        try:
            result = await ai_service.process_query(query, user_id, "ukr")
            print(f"     ✅ Ответ получен (confidence: {result.get('confidence', 0):.3f})")
        except Exception as e:
            print(f"     ❌ Ошибка: {e}")

    print("\n📊 Генерируем отчет...")

    # Получаем отчет
    report = create_simple_report()
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    # Получаем предложения по улучшению
    print("\n💡 Предложения по улучшению:")
    suggestions = analytics_service.get_improvement_suggestions()

    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. [{suggestion['priority'].upper()}] {suggestion['description']}")
            if "examples" in suggestion:
                for example in suggestion["examples"][:2]:
                    print(f"   - Пример: {example}")
    else:
        print("✅ Предложений нет - все работает отлично!")

    print(f"\n🎯 Тестирование завершено!")
    print(f"📄 База данных аналитики: ./data/analytics.db")
    print(f"🌐 Для запуска веб-dashboard: python -m src.analytics.dashboard")


if __name__ == "__main__":
    asyncio.run(test_analytics())
