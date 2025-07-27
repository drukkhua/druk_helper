"""
Тест RAG системы с базой знаний из CSV файлов
Проверяет загрузку данных, векторный поиск и генерацию ответов
"""

import pytest
import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai.knowledge_base import knowledge_base
from src.ai.rag_service import rag_service


@pytest.mark.asyncio
async def test_knowledge_base():
    """Тестирует загрузку и поиск в базе знаний"""
    print("🗄️ Тестирование базы знаний...")

    # Инициализируем базу знаний
    print("Инициализация базы знаний...")
    success = knowledge_base.populate_vector_store(force_reload=True)
    print(f"Инициализация: {'✅ Успешно' if success else '❌ Ошибка'}")

    # Получаем статистику
    stats = knowledge_base.get_statistics()
    print(f"Статистика базы знаний:")
    print(f"  📊 Всего документов: {stats.get('total_documents', 0)}")
    print(f"  📂 Категории: {list(stats.get('categories', {}).keys())}")

    # Тестовые запросы для поиска
    test_queries = [
        ("Скільки коштують візитки?", "ukr"),
        ("цена футболки", "rus"),
        ("терміни виготовлення", "ukr"),
        ("качество печати", "rus"),
        ("что-то несуществующее", "ukr"),
    ]

    print("\n🔍 Тестирование поиска по базе знаний:")
    print("=" * 60)

    for i, (query, lang) in enumerate(test_queries, 1):
        print(f"\n{i}. Запрос: '{query}' (язык: {lang})")

        # Ищем в базе знаний
        results = knowledge_base.search_knowledge(query, lang, n_results=2)

        if results:
            print(f"   ✅ Найдено {len(results)} результатов:")
            for j, result in enumerate(results, 1):
                relevance = result.get("relevance_score", 0)
                category = result.get("category", "unknown")
                answer = (
                    result.get("answer", "")[:100] + "..."
                    if len(result.get("answer", "")) > 100
                    else result.get("answer", "")
                )
                print(f"      {j}. [{category}] Релевантность: {relevance:.3f}")
                print(f"         Ответ: {answer}")
        else:
            print("   ❌ Ничего не найдено")


@pytest.mark.asyncio
async def test_rag_service():
    """Тестирует RAG сервис"""
    print("\n🤖 Тестирование RAG сервиса...")

    # Тестовые запросы
    test_queries = [
        ("Скільки коштують візитки?", "ukr"),
        ("Сколько стоят футболки?", "rus"),
        ("Які терміни виготовлення?", "ukr"),
        ("Можете сделать дизайн?", "rus"),
    ]

    print("\n📝 Тестирование генерации контекста:")
    print("=" * 60)

    for i, (query, lang) in enumerate(test_queries, 1):
        print(f"\n{i}. Запрос: '{query}' (язык: {lang})")

        # Получаем контекст
        context = await rag_service.get_context_for_query(query, lang)

        if context:
            print(f"   ✅ Контекст найден ({len(context)} символов):")
            print(f"   {context[:200]}{'...' if len(context) > 200 else ''}")

            # Создаем системный промпт
            system_prompt = rag_service.create_system_prompt(lang, context)
            print(f"   📋 Системный промпт создан ({len(system_prompt)} символов)")
        else:
            print("   ❌ Контекст не найден")
            # Создаем базовый системный промпт
            system_prompt = rag_service.create_system_prompt(lang)
            print(f"   📋 Базовый системный промпт создан ({len(system_prompt)} символов)")


@pytest.mark.asyncio
async def test_csv_data_loading():
    """Тестирует загрузку данных из CSV файлов"""
    print("\n📄 Тестирование загрузки CSV данных...")

    # Загружаем данные напрямую
    csv_data = knowledge_base.load_csv_data()

    print(f"📊 Загружено записей: {len(csv_data)}")

    # Группируем по категориям
    categories = {}
    for item in csv_data:
        category = item["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(item)

    print("\n📂 Данные по категориям:")
    for category, items in categories.items():
        print(f"  {category}: {len(items)} записей")
        if items:
            # Показываем первую запись как пример
            first_item = items[0]
            keywords = first_item.get("keywords", "")[:50]
            answer_ukr = first_item.get("answer_ukr", "")[:50]
            print(f"    Пример - Ключевые слова: {keywords}...")
            print(f"           - Ответ (укр): {answer_ukr}...")


async def main():
    """Основная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ RAG СИСТЕМЫ")
    print("=" * 60)

    try:
        # Тест загрузки CSV данных
        await test_csv_data_loading()

        # Тест базы знаний
        await test_knowledge_base()

        # Тест RAG сервиса
        await test_rag_service()

        print("\n" + "=" * 60)
        print("🎉 Все тесты завершены!")

    except Exception as e:
        print(f"\n❌ Ошибка во время тестирования: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
