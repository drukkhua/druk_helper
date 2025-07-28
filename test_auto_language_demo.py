#!/usr/bin/env python3
"""
Демонстрация автоопределения языка в боте
"""

import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ai.enhanced_ai_service import enhanced_ai_service


async def demo_auto_language():
    """Демонстрирует автоопределение языка в AI сервисе"""

    print("=== Демонстрация автоопределения языка ===\n")

    # Тестовые запросы на разных языках
    test_queries = [
        ("Скільки коштують візитки?", "украинский"),
        ("Сколько стоят визитки?", "русский"),
        ("Що таке тиснення фольгою?", "украинский"),
        ("Что такое тиснение фольгой?", "русский"),
        ("Потрібно надрукувати футболки", "украинский"),
        ("Нужно напечатать футболки", "русский"),
    ]

    user_id = 12345  # Тестовый пользователь

    for query, expected_lang in test_queries:
        print(f"📝 Запрос: '{query}'")
        print(f"🎯 Ожидаемый язык: {expected_lang}")

        try:
            # Вызываем AI сервис БЕЗ указания языка - он должен автоопределиться
            result = await enhanced_ai_service.process_query(
                user_query=query, user_id=user_id, language=None  # Язык не указываем!
            )

            print(f"🤖 Ответ: {result['answer'][:100]}...")
            print(f"📊 Источник: {result['source']}")
            print(f"💯 Уверенность: {result['confidence']:.2f}")

        except Exception as e:
            print(f"❌ Ошибка: {e}")

        print("-" * 60)


if __name__ == "__main__":
    # Запускаем демонстрацию
    asyncio.run(demo_auto_language())
