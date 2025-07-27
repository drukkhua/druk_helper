#!/usr/bin/env python3
"""
Полный тест RAG системы с реальным OpenAI API
Проверяет работу полной интеграции
"""

import pytest
import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai.service import ai_service
from config import Config


@pytest.mark.asyncio
async def test_full_rag_pipeline():
    """Тестирует полный RAG pipeline с реальным OpenAI"""
    print("🧠 Тестирование полного RAG pipeline с OpenAI...")

    # Проверяем статус AI сервиса
    print(f"AI включен: {ai_service.enabled}")
    print(f"Использует реальный AI: {ai_service.use_real_ai}")
    print(f"База знаний готова: {ai_service.knowledge_ready}")
    print(f"AI доступен: {ai_service.is_available()}")

    if ai_service.knowledge_ready:
        stats = ai_service.knowledge_base.get_statistics()
        print(f"Документов в базе знаний: {stats.get('total_documents', 0)}")

    print()

    # Тестовые запросы, которые должны найти релевантную информацию
    test_queries = [
        ("Скільки коштують візитки?", "ukr"),
        ("Які терміни виготовлення футболок?", "ukr"),
        ("Сколько стоят визитки?", "rus"),
        ("Можете ли сделать макет с нуля?", "rus"),
        ("Чи можете зробити дизайн?", "ukr"),
    ]

    print("📝 Тестирование запросов:")
    print("=" * 70)

    for i, (query, lang) in enumerate(test_queries, 1):
        print(f"\n{i}. Запрос: '{query}' (язык: {lang})")

        try:
            # Обрабатываем запрос через AI сервис
            result = await ai_service.process_query(query, 12345, lang)

            print(f"   ✅ Успех: {result['success']}")
            print(f"   🎯 Источник: {result['source']}")
            print(f"   📊 Уверенность: {result['confidence']:.2f}")
            print(f"   📞 Связаться с менеджером: {result['should_contact_manager']}")

            # Показываем ответ
            answer = result["answer"]
            if len(answer) > 200:
                print(f"   💬 Ответ: {answer[:200]}...")
            else:
                print(f"   💬 Ответ: {answer}")

            print(f"   📏 Длина ответа: {len(answer)} символов")

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

    print("\n" + "=" * 70)
    print("🏁 Тестирование завершено!")


@pytest.mark.asyncio
async def test_rag_vs_mock():
    """Сравнивает ответы RAG и mock системы"""
    print("\n🆚 Сравнение RAG vs Mock ответов...")

    test_query = "Скільки коштують візитки?"
    lang = "ukr"

    print(f"Запрос: '{test_query}' (язык: {lang})")

    try:
        # Получаем RAG ответ (если база знаний работает)
        if ai_service.knowledge_ready and ai_service.use_real_ai:
            print("\n🧠 RAG + OpenAI ответ:")
            result = await ai_service.process_query(test_query, 12345, lang)
            print(f"   {result['answer'][:300]}...")

        # Получаем mock ответ для сравнения
        print("\n🎭 Mock ответ:")
        mock_result = ai_service._create_mock_ai_response(test_query, lang)
        print(f"   {mock_result['answer'][:300]}...")

    except Exception as e:
        print(f"❌ Ошибка при сравнении: {e}")


async def main():
    """Основная функция тестирования"""
    print("🧪 ПОЛНОЕ ТЕСТИРОВАНИЕ RAG СИСТЕМЫ")
    print("=" * 70)

    # Проверяем конфигурацию
    config = Config()
    print(f"OpenAI API Key: {'✅ Настроен' if config.OPENAI_API_KEY else '❌ Не настроен'}")
    print(f"AI Enabled: {config.AI_ENABLED}")
    print(f"AI Model: {config.AI_MODEL}")
    print()

    try:
        # Тест полного pipeline
        await test_full_rag_pipeline()

        # Сравнение подходов
        await test_rag_vs_mock()

        print("\n" + "=" * 70)
        print("🎉 Все тесты завершены!")

    except Exception as e:
        print(f"\n❌ Ошибка во время тестирования: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
