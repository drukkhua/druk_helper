#!/usr/bin/env python3
"""
Тест Enhanced AI Service для диагностики проблем
"""

import pytest
import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath("."))


@pytest.mark.asyncio
async def test_enhanced_ai():
    """Тестирует Enhanced AI Service"""

    print("🧪 Тестирование Enhanced AI Service...")

    try:
        # Импортируем сервис
        from src.ai.enhanced_ai_service import enhanced_ai_service

        print("✅ Enhanced AI Service импортирован")

        # Проверяем доступность
        is_available = enhanced_ai_service.is_available()
        print(f"🔍 Доступность: {is_available}")

        # Получаем информацию о сервисе
        service_info = enhanced_ai_service.get_service_info()
        print(f"ℹ️  Информация о сервисе: {service_info}")

        # Тестируем простой запрос
        print("📝 Тестируем запрос: 'Сколько стоят визитки?'")

        result = await enhanced_ai_service.process_query("Сколько стоят визитки?", 12345, "ukr")

        print(f"✅ Результат получен:")
        print(f"   Ответ: {result.get('answer', 'Нет ответа')[:100]}...")
        print(f"   Уверенность: {result.get('confidence', 0):.1%}")
        print(f"   Источник: {result.get('source', 'unknown')}")
        print(f"   Время: {result.get('response_time_ms', 0)}ms")

    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_enhanced_ai())
