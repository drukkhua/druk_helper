#!/usr/bin/env python3
"""
Тест интеграции с реальным OpenAI API
Проверяет работу AI сервиса с настоящими запросами
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
async def test_real_ai():
    """Тестирует реальные AI запросы"""
    print("🚀 Тестирование интеграции с OpenAI API...")
    print(f"AI включен: {ai_service.enabled}")
    print(f"Использует реальный AI: {ai_service.use_real_ai}")
    print(f"AI доступен: {ai_service.is_available()}")
    print()

    # Тестовые запросы
    test_queries = [
        ("Скільки коштують візитки?", "ukr"),
        ("Які терміни виготовлення футболок?", "ukr"),
        ("Сколько стоят визитки?", "rus"),
        ("Можете ли сделать макет с нуля?", "rus"),
        ("What are your prices?", "ukr"),  # Должен отвечать на украинском
    ]

    print("📝 Выполняем тестовые запросы:")
    print("=" * 50)

    for i, (query, lang) in enumerate(test_queries, 1):
        print(f"\n{i}. Запрос: {query}")
        print(f"   Язык: {lang}")

        try:
            result = await ai_service.process_query(query, 12345, lang)

            print(f"   ✅ Успех: {result['success']}")
            print(f"   🎯 Источник: {result['source']}")
            print(f"   📊 Уверенность: {result['confidence']:.2f}")
            print(f"   📞 Связаться с менеджером: {result['should_contact_manager']}")
            print(
                f"   💬 Ответ: {result['answer'][:150]}{'...' if len(result['answer']) > 150 else ''}"
            )

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

    print("\n" + "=" * 50)
    print("🏁 Тестирование завершено!")


@pytest.mark.asyncio
async def test_cost_estimation():
    """Простая оценка стоимости"""
    print("\n💰 Оценка стоимости:")

    # Примерные данные (основано на предыдущих тестах)
    cost_per_request = 0.000045  # $
    balance = 10.0  # $

    requests_possible = int(balance / cost_per_request)
    print(f"   💳 Баланс: ${balance}")
    print(f"   💲 Стоимость запроса: ~${cost_per_request}")
    print(f"   🔢 Возможных запросов: ~{requests_possible:,}")


if __name__ == "__main__":
    print("🤖 Тест интеграции с реальным OpenAI API")
    print("=" * 50)

    # Проверяем конфигурацию
    config = Config()
    print(f"OpenAI API Key: {'✅ Настроен' if config.OPENAI_API_KEY else '❌ Не настроен'}")
    print(f"AI Enabled: {config.AI_ENABLED}")
    print(f"AI Model: {config.AI_MODEL}")
    print()

    asyncio.run(test_real_ai())
    asyncio.run(test_cost_estimation())
