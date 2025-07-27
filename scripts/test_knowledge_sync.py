#!/usr/bin/env python3
"""
Скрипт для тестирования интеграции Google Sheets с системой аналитики
Проверяет работу синхронизации базы знаний
"""

import sys
import os
import asyncio
from datetime import datetime

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.knowledge_sync import knowledge_sync_service
from src.analytics.analytics_service import analytics_service


async def test_knowledge_sync():
    """Тестирует систему синхронизации знаний"""
    print("🧪 Тестирование интеграции Google Sheets + Analytics + ChromaDB...")
    print("=" * 70)

    # 1. Проверяем текущий статус
    print("\n📊 1. Текущий статус синхронизации:")
    status = knowledge_sync_service.get_sync_status()
    print(f"   • Последняя синхронизация: {status['last_sync_time'] or 'Не выполнялась'}")
    print(f"   • Успешность: {'✅' if status['last_sync_success'] else '❌'}")
    print(f"   • Изменений: {status['last_sync_changes']}")
    print(f"   • Google Таблица: {status['spreadsheet_url'][:50]}...")
    print(f"   • Доступные листы: {', '.join(status['available_sheets'])}")

    # 2. Проверяем необходимость синхронизации
    print("\n🔍 2. Проверка необходимости синхронизации:")
    sync_needed, reason = await knowledge_sync_service.check_sync_needed()
    print(f"   • Нужна синхронизация: {'✅' if sync_needed else '❌'}")
    print(f"   • Причина: {reason}")

    # 3. Тестируем умную синхронизацию
    print("\n🤖 3. Тестируем умную синхронизацию:")
    smart_sync_result = await knowledge_sync_service.smart_sync()

    if smart_sync_result.get("skipped"):
        print(f"   ⏭️ Синхронизация пропущена: {smart_sync_result['reason']}")
    elif smart_sync_result["success"]:
        print(f"   ✅ Умная синхронизация выполнена:")
        print(f"      • Изменений: {smart_sync_result['changes']}")
        print(f"      • Время: {smart_sync_result['duration_ms']}ms")
    else:
        print(f"   ❌ Ошибка умной синхронизации: {smart_sync_result.get('error')}")

    # 4. Принудительная полная синхронизация для демонстрации
    print("\n🔄 4. Принудительная полная синхронизация:")
    full_sync_result = await knowledge_sync_service.full_sync_knowledge_base(force_reload=False)

    if full_sync_result["success"]:
        print(f"   ✅ Полная синхронизация выполнена:")
        print(f"      • CSV файлов обновлено: {full_sync_result['csv_files_updated']}")
        print(
            f"      • ChromaDB обновлена: {'✅' if full_sync_result['chromadb_updated'] else '❌'}"
        )
        print(
            f"      • Аналитика записана: {'✅' if full_sync_result['analytics_recorded'] else '❌'}"
        )
        print(f"      • Время выполнения: {full_sync_result['duration_ms']}ms")
        print(f"      • Общие изменения: {full_sync_result['changes']}")
    else:
        print(f"   ❌ Ошибки полной синхронизации:")
        for error in full_sync_result["errors"]:
            print(f"      • {error}")

    # 5. Проверяем статистику после синхронизации
    print("\n📈 5. Статистика после синхронизации:")
    try:
        summary = analytics_service.get_analytics_summary(days=1)
        print(f"   • Всего запросов: {summary['overall_stats']['total_queries']}")
        print(f"   • Документов в базе: {summary['overall_stats']['total_documents']}")
        print(f"   • Процент ответов: {summary['overall_stats']['answer_rate']:.1f}%")
        print(f"   • Пробелы в знаниях: {summary['overall_stats']['knowledge_gaps']}")
    except Exception as e:
        print(f"   ❌ Ошибка получения статистики: {e}")

    # 6. Получаем предложения по улучшению
    print("\n💡 6. Предложения по улучшению:")
    try:
        suggestions = analytics_service.get_improvement_suggestions()
        if suggestions:
            for i, suggestion in enumerate(suggestions[:3], 1):
                priority = suggestion.get("priority", "medium")
                emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🔵")
                print(f"   {emoji} {i}. {suggestion['description']}")
        else:
            print("   ✅ Предложений нет - система работает оптимально!")
    except Exception as e:
        print(f"   ❌ Ошибка получения предложений: {e}")

    # 7. Итоговый статус
    print("\n🎯 7. Итоговый статус интеграции:")
    final_status = knowledge_sync_service.get_sync_status()
    print(f"   • Последняя синхронизация: {final_status['last_sync_time']}")
    print(f"   • Успешность: {'✅' if final_status['last_sync_success'] else '❌'}")
    print(f"   • Изменений в последней синхронизации: {final_status['last_sync_changes']}")

    print("\n" + "=" * 70)
    print("🎉 Тестирование интеграции завершено!")
    print("\n📋 Доступные команды в Telegram боте:")
    print("   • /reload - Полная синхронизация с Google Sheets")
    print("   • /sync - Умная синхронизация (только при необходимости)")
    print("   • /stats - Расширенная статистика с AI аналитикой")
    print("   • /analytics - Детальная аналитика AI системы")
    print("   • /suggestions - Предложения по улучшению")
    print("   • /health - Проверка состояния системы")


if __name__ == "__main__":
    asyncio.run(test_knowledge_sync())
