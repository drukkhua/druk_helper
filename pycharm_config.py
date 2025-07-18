"""
Конфигурация для запуска в PyCharm
"""

from pathlib import Path

import asyncio
import logging
import os
import sys

# Добавляем текущую директорию в Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Настройка логирования для PyCharm
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pycharm_debug.log", encoding="utf-8"),
    ],
)


def check_pycharm_environment():
    """Проверка окружения PyCharm"""
    print("🔍 Проверка окружения PyCharm...")

    # Проверяем переменные окружения
    env_vars = ["BOT_TOKEN", "ADMIN_USER_IDS", "GOOGLE_SHEETS_API_KEY"]

    missing_vars = []
    for var in env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Отсутствуют переменные окружения: {missing_vars}")
        print("💡 Создайте файл .env в корне проекта или настройте в PyCharm:")
        print("   Run -> Edit Configurations -> Environment variables")
        return False

    print("✅ Переменные окружения настроены")
    return True


def check_virtual_environment():
    """Проверка виртуального окружения"""
    print("🔍 Проверка виртуального окружения...")

    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print("✅ Виртуальное окружение активировано")
        print(f"📍 Python path: {sys.prefix}")
        return True
    else:
        print("❌ Виртуальное окружение не активировано")
        print("💡 В PyCharm: File -> Settings -> Project -> Python Interpreter")
        print("   Выберите интерпретатор из venv/bin/python")
        return False


def check_working_directory():
    """Проверка рабочей директории"""
    print("🔍 Проверка рабочей директории...")

    current_dir = os.getcwd()
    print(f"📍 Текущая директория: {current_dir}")

    # Проверяем наличие основных файлов
    required_files = ["main.py", "config.py", "template_manager.py", "requirements.txt"]
    missing_files = []

    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f"❌ Отсутствуют файлы: {missing_files}")
        print("💡 В PyCharm: Run -> Edit Configurations -> Working directory")
        print("   Установите путь к корню проекта")
        return False

    print("✅ Рабочая директория настроена правильно")
    return True


def setup_pycharm_debugging():
    """Настройка отладки для PyCharm"""
    print("🔧 Настройка отладки...")

    # Включаем отладку asyncio
    os.environ["PYTHONASYNCIODEBUG"] = "1"

    # Включаем отладку aiogram
    logging.getLogger("aiogram").setLevel(logging.DEBUG)

    # Отключаем некоторые шумные логи
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    print("✅ Отладка настроена")


async def test_bot_components():
    """Тестирование компонентов бота"""
    print("🧪 Тестирование компонентов...")

    try:
        # Тестируем импорты
        from aiogram import Bot

        from config import ADMIN_USER_IDS, BOT_TOKEN
        from template_manager import TemplateManager

        print("✅ Импорты успешны")

        # Тестируем создание бота
        bot = Bot(token=BOT_TOKEN)
        print("✅ Бот создан")

        # Тестируем менеджер шаблонов
        tm = TemplateManager()
        template_count = sum(len(templates) for templates in tm.templates.values())
        print(f"✅ Загружено шаблонов: {template_count}")

        # Закрываем сессию бота
        await bot.session.close()

        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Основная функция для настройки PyCharm"""
    print("🚀 Настройка PyCharm для запуска бота...")
    print("=" * 50)

    # Проверки
    checks = [
        check_virtual_environment,
        check_working_directory,
        check_pycharm_environment,
    ]

    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
        print("-" * 30)

    if all_passed:
        print("✅ Все проверки пройдены!")
        setup_pycharm_debugging()

        # Тестируем компоненты
        try:
            asyncio.run(test_bot_components())
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("🎉 PyCharm готов к запуску бота!")
        print("💡 Используйте debug_runner.py для отладочного запуска")
    else:
        print("❌ Необходимо исправить ошибки конфигурации")
        print("📖 Смотрите инструкции выше")


if __name__ == "__main__":
    main()
