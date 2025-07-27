#!/usr/bin/env python3
"""
Скрипт для тестирования новых Telegram команд
Проверяет работу /analytics, /sync, /suggestions без запуска бота
"""

import sys
import os
import asyncio
from unittest.mock import Mock

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot.handlers.main import cmd_analytics, cmd_sync, cmd_suggestions
from src.core.template_manager import TemplateManager


class MockMessage:
    """Мок-объект для сообщения Telegram"""

    def __init__(self, user_id: int):
        self.from_user = Mock()
        self.from_user.id = user_id
        self.text = ""
        self.responses = []

    async def answer(self, text: str, **kwargs):
        """Мок метод для ответа"""
        self.responses.append(text)
        print(f"📤 Ответ боту: {text[:100]}{'...' if len(text) > 100 else ''}")


async def test_telegram_commands():
    """Тестирует новые Telegram команды"""
    print("🤖 Тестирование новых Telegram команд...")
    print("=" * 60)

    # Создаем мок объекты
    admin_user_id = 12345  # Замените на реальный admin ID из config
    mock_message = MockMessage(admin_user_id)

    # Инициализируем template_manager (может быть None для тестов)
    template_manager = None

    # Тестируем каждую команду
    commands_to_test = [
        ("analytics", cmd_analytics, "Детальная аналитика AI"),
        ("sync", cmd_sync, "Умная синхронизация"),
        ("suggestions", cmd_suggestions, "Предложения по улучшению"),
    ]

    for cmd_name, cmd_func, description in commands_to_test:
        print(f"\n🧪 Тестируем команду /{cmd_name} - {description}")
        print("-" * 40)

        try:
            # Очищаем предыдущие ответы
            mock_message.responses = []

            # Вызываем команду
            await cmd_func(mock_message, template_manager)

            # Анализируем результат
            if mock_message.responses:
                print(f"✅ Команда /{cmd_name} выполнена успешно")
                print(f"📝 Получено ответов: {len(mock_message.responses)}")

                # Показываем первые 200 символов каждого ответа
                for i, response in enumerate(mock_message.responses, 1):
                    print(f"   Ответ {i}: {response[:200]}{'...' if len(response) > 200 else ''}")
            else:
                print(f"⚠️ Команда /{cmd_name} не вернула ответов")

        except Exception as e:
            print(f"❌ Ошибка при выполнении /{cmd_name}: {e}")
            print(f"   Тип ошибки: {type(e).__name__}")

    print("\n" + "=" * 60)
    print("🎯 Тестирование завершено!")

    # Проверяем регистрацию команд в роутере
    print("\n🔍 Проверка регистрации команд в роутере:")
    try:
        from src.bot.routers import BotRouters

        print("✅ BotRouters импортируется успешно")

        # Проверяем наличие обработчиков
        import inspect

        router_methods = inspect.getmembers(BotRouters, predicate=inspect.ismethod)
        print(f"📋 Найдено методов в BotRouters: {len(router_methods)}")

    except Exception as e:
        print(f"❌ Ошибка импорта BotRouters: {e}")

    print("\n💡 Для тестирования в реальном боте:")
    print("   1. Запустите бота: python main.py")
    print("   2. Отправьте команды от админского аккаунта:")
    print("      /analytics - детальная аналитика")
    print("      /sync - умная синхронизация")
    print("      /suggestions - предложения по улучшению")


if __name__ == "__main__":
    asyncio.run(test_telegram_commands())
