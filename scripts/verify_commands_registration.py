#!/usr/bin/env python3
"""
Скрипт для проверки регистрации команд в боте
Проверяет полную цепочку: handlers -> routers -> main
"""

import sys
import os

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_handlers():
    """Проверяет наличие обработчиков команд"""
    print("🔍 Проверка обработчиков команд...")

    try:
        from src.bot.handlers import main as handlers

        # Проверяем наличие функций
        functions_to_check = ["cmd_analytics", "cmd_sync", "cmd_suggestions"]

        missing_functions = []
        for func_name in functions_to_check:
            if hasattr(handlers, func_name):
                print(f"   ✅ {func_name} - найден")
            else:
                print(f"   ❌ {func_name} - НЕ НАЙДЕН")
                missing_functions.append(func_name)

        if missing_functions:
            print(f"❌ Отсутствующие функции: {missing_functions}")
            return False
        else:
            print("✅ Все обработчики команд найдены")
            return True

    except Exception as e:
        print(f"❌ Ошибка импорта handlers: {e}")
        return False


def check_routers():
    """Проверяет регистрацию команд в роутерах"""
    print("\n🔍 Проверка регистрации в роутерах...")

    try:
        # Читаем файл роутера и ищем команды
        router_file = "/Volumes/work/TG_bots/Bot-answers/src/bot/routers.py"

        with open(router_file, "r", encoding="utf-8") as f:
            router_content = f.read()

        commands_to_check = ['Command("analytics")', 'Command("sync")', 'Command("suggestions")']

        missing_commands = []
        for cmd in commands_to_check:
            if cmd in router_content:
                print(f"   ✅ {cmd} - зарегистрирована")
            else:
                print(f"   ❌ {cmd} - НЕ НАЙДЕНА")
                missing_commands.append(cmd)

        if missing_commands:
            print(f"❌ Отсутствующие команды в роутере: {missing_commands}")
            return False
        else:
            print("✅ Все команды зарегистрированы в роутере")
            return True

    except Exception as e:
        print(f"❌ Ошибка чтения файла роутера: {e}")
        return False


def check_main_integration():
    """Проверяет интеграцию с main.py"""
    print("\n🔍 Проверка интеграции с main.py...")

    try:
        from bot_lifecycle import BotLifeCycleManager

        print("✅ BotLifeCycleManager импортируется успешно")

        # Проверяем, что register_handlers импортируется
        from src.bot.routers import register_handlers

        print("✅ register_handlers импортируется успешно")

        return True

    except Exception as e:
        print(f"❌ Ошибка интеграции с main: {e}")
        return False


def check_admin_config():
    """Проверяет конфигурацию админов"""
    print("\n🔍 Проверка конфигурации админов...")

    try:
        from config import ADMIN_USER_IDS

        if ADMIN_USER_IDS:
            print(f"✅ Админы настроены: {len(ADMIN_USER_IDS)} пользователей")
            print(f"   ID админов: {ADMIN_USER_IDS}")
        else:
            print("⚠️ Админы не настроены (ADMIN_USER_IDS пустой)")
            print("   Добавьте в .env: ADMIN_USER_IDS=123456789,987654321")

        return True

    except Exception as e:
        print(f"❌ Ошибка конфигурации админов: {e}")
        return False


def main():
    """Основная функция проверки"""
    print("🤖 Проверка регистрации новых Telegram команд")
    print("=" * 60)

    checks = [
        ("Обработчики команд", check_handlers),
        ("Регистрация в роутерах", check_routers),
        ("Интеграция с main.py", check_main_integration),
        ("Конфигурация админов", check_admin_config),
    ]

    results = []

    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в {check_name}: {e}")
            results.append((check_name, False))

    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)

    all_passed = True
    for check_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{status} - {check_name}")
        if not result:
            all_passed = False

    print("\n🎯 ОБЩИЙ РЕЗУЛЬТАТ:")
    if all_passed:
        print(
            "✅ Все проверки пройдены! Команды /analytics и /sync должны работать в Telegram боте."
        )
        print("\n📋 Команды для тестирования в боте (от админского аккаунта):")
        print("   /analytics - детальная аналитика AI системы")
        print("   /sync - умная синхронизация базы знаний")
        print("   /suggestions - предложения по улучшению")
        print("   /reload - полная синхронизация (обновлено)")
        print("   /stats - расширенная статистика (обновлено)")
    else:
        print("❌ Есть проблемы с регистрацией команд.")
        print("   Проверьте ошибки выше и исправьте их.")

    print(f"\n💡 Не забудьте добавить админский user_id в .env:")
    print(f"   ADMIN_USER_IDS=ваш_telegram_user_id")


if __name__ == "__main__":
    main()
