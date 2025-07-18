"""
Главный файл бота - точка входа
"""

import asyncio
import sys

from bot_lifecycle import start_bot
from config import logger
from exceptions import ConfigurationError


async def main():
    """Главная функция запуска бота"""
    try:
        logger.info("🚀 Запуск Telegram-бота 'Яскравий друк'")
        logger.info("📋 Версия: 1.05")

        # Запуск бота
        await start_bot()

    except ConfigurationError as e:
        logger.critical(f"❌ Ошибка конфигурации: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")

    except Exception as e:
        logger.critical(f"💥 Критическая ошибка: {e}")
        sys.exit(1)

    finally:
        logger.info("👋 Завершение работы бота!!!")


if __name__ == "__main__":
    asyncio.run(main())
