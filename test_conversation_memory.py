#!/usr/bin/env python3
"""
Тест системы памяти разговора
"""

import pytest
import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai.service import ai_service
from src.ai.conversation_memory import conversation_memory


@pytest.mark.asyncio
async def test_conversation_memory():
    """Тестирует память разговора с несколькими сообщениями"""
    print("🧠 ТЕСТИРОВАНИЕ ПАМЯТИ РАЗГОВОРА")
    print("=" * 50)

    user_id = 12345

    # Очищаем сессию перед тестом
    conversation_memory.clear_session(user_id)

    # Тестовый диалог
    conversation = [
        ("Скільки коштують візитки?", "ukr"),
        ("А футболки?", "ukr"),  # Этот вопрос должен понимать контекст предыдущего
        ("Можете зробити експрес-доставку?", "ukr"),
    ]

    print(f"👤 Пользователь: {user_id}")
    print()

    for i, (question, lang) in enumerate(conversation, 1):
        print(f'📝 Сообщение {i}: "{question}"')
        print("-" * 40)

        try:
            # Обрабатываем запрос
            result = await ai_service.process_query(question, user_id, lang)

            # Показываем ответ
            print(f"🤖 Ответ: {result['answer']}")

            # Показываем статистику сессии
            stats = conversation_memory.get_session_stats(user_id)
            print(f"📊 Сообщений в сессии: {stats['message_count']}")

            # Показываем контекст разговора для следующего сообщения
            if i < len(conversation):
                context = conversation_memory.get_conversation_context(user_id)
                print(f"💭 Контекст для следующего сообщения: {len(context)} сообщений")

            print()

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print()

    print("🏁 Тест завершен!")

    # Показываем финальную статистику
    print("\n📈 ФИНАЛЬНАЯ СТАТИСТИКА:")
    stats = conversation_memory.get_session_stats(user_id)
    if stats["exists"]:
        print(f"  • Сообщений в сессии: {stats['message_count']}")
        print(f"  • Создана: {stats['created_at']}")
        print(f"  • Последняя активность: {stats['last_activity']}")
        print(f"  • Язык: {stats['language']}")
        print(f"  • Возраст сессии: {stats['age_hours']:.2f} часов")
    else:
        print("  • Сессия не найдена")


@pytest.mark.asyncio
async def test_context_understanding():
    """Тестирует понимание контекста"""
    print("\n🎯 ТЕСТ ПОНИМАНИЯ КОНТЕКСТА")
    print("=" * 50)

    user_id = 54321
    conversation_memory.clear_session(user_id)

    # Первый вопрос - устанавливаем контекст
    print("👤 Устанавливаем контекст...")
    result1 = await ai_service.process_query("Расскажите о ваших визитках", user_id, "rus")
    print(f"🤖 Ответ 1: {result1['answer'][:100]}...")

    print("\n👤 Задаем уточняющий вопрос...")
    result2 = await ai_service.process_query("А сколько это будет стоить?", user_id, "rus")
    print(f"🤖 Ответ 2: {result2['answer']}")

    # Проверяем, упоминается ли контекст визиток в ответе
    if (
        "визит" in result2["answer"].lower()
        or "158" in result2["answer"]
        or "920" in result2["answer"]
    ):
        print("✅ Система помнит контекст о визитках!")
    else:
        print("❌ Система не помнит контекст")


if __name__ == "__main__":
    asyncio.run(test_conversation_memory())
    asyncio.run(test_context_understanding())
