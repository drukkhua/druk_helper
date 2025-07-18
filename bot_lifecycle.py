"""
Управление жизненным циклом бота (запуск, остановка, инициализация)
"""

import signal

import asyncio
import os
import sys
from aiogram import Bot, Dispatcher
from typing import Optional

from bot_factory import (
    cleanup_bot_resources,
    create_bot_instance,
    validate_bot_configuration,
)
from config import logger
from error_handler import error_handler
from error_monitor import cleanup_old_errors
from exceptions import ConfigurationError
from routers import register_handlers
from template_manager import TemplateManager


class BotLifecycle:
    """Управление жизненным циклом бота"""

    def __init__(self):
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.template_manager: Optional[TemplateManager] = None
        self.routers = None
        self.is_running = False
        self.shutdown_event = asyncio.Event()

    async def initialize(self):
        """Инициализация бота"""
        try:
            logger.info("Начало инициализации бота...")

            # Валидация конфигурации
            if not validate_bot_configuration():
                raise ConfigurationError("Конфигурация бота некорректна")

            # Создание необходимых директорий
            await self._create_directories()

            # Создание экземпляров
            self.bot, self.dp, self.template_manager = create_bot_instance()

            # Регистрация обработчиков
            self.routers = register_handlers(self.dp, self.template_manager)

            # Очистка старых ошибок
            cleanup_old_errors(days=30)

            logger.info("Бот успешно инициализирован")
            logger.info(
                f"Загружены категории: {list(self.template_manager.templates.keys())}"
            )

        except Exception as e:
            logger.critical(f"Критическая ошибка инициализации: {e}")
            await self.cleanup()
            raise

    async def _create_directories(self):
        """Создание необходимых директорий"""
        directories = ["./data", "./logs", "./converted-data", "./converted-data/csv"]

        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"Директория создана/проверена: {directory}")
            except Exception as e:
                logger.error(f"Ошибка создания директории {directory}: {e}")

    async def start(self):
        """Запуск бота"""
        if self.is_running:
            logger.warning("Бот уже запущен")
            return

        try:
            if not self.bot or not self.dp:
                await self.initialize()

            self.is_running = True
            logger.info("Запуск бота...")

            # Настройка обработчиков сигналов
            self._setup_signal_handlers()

            # Запуск polling
            await self.dp.start_polling(self.bot)

        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения от пользователя")
            await self.shutdown()
        except Exception as e:
            logger.critical(f"Критическая ошибка при запуске: {e}")
            await error_handler.handle_error(e)
            await self.shutdown()
            raise
        finally:
            self.is_running = False

    async def shutdown(self):
        """Graceful shutdown бота"""
        if not self.is_running:
            logger.info("Бот уже остановлен")
            return

        try:
            logger.info("Начало graceful shutdown...")

            # Останавливаем polling
            if self.dp:
                await self.dp.stop_polling()

            # Очищаем ресурсы
            await self.cleanup()

            self.is_running = False
            self.shutdown_event.set()

            logger.info("Graceful shutdown завершен")

        except Exception as e:
            logger.error(f"Ошибка при shutdown: {e}")
        finally:
            self.is_running = False

    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            logger.info("Очистка ресурсов...")

            # Закрываем сессию бота
            if self.bot:
                await self.bot.session.close()

            # Очищаем фабрику
            cleanup_bot_resources()

            # Сохраняем статистику если нужно
            if self.template_manager and self.template_manager.stats:
                # Здесь можно добавить сохранение финальной статистики
                pass

            logger.info("Ресурсы очищены")

        except Exception as e:
            logger.error(f"Ошибка очистки ресурсов: {e}")

    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""

        def signal_handler(signum, frame):
            logger.info(f"Получен сигнал {signum}")
            # Создаем задачу для graceful shutdown
            asyncio.create_task(self.shutdown())

        # Регистрируем обработчики для Unix-сигналов
        if sys.platform != "win32":
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

    async def restart(self):
        """Перезапуск бота"""
        logger.info("Перезапуск бота...")

        await self.shutdown()
        await asyncio.sleep(2)  # Небольшая пауза
        await self.initialize()
        await self.start()

    async def health_check(self) -> dict:
        """Проверка здоровья бота"""
        try:
            health_status = {
                "status": "healthy",
                "is_running": self.is_running,
                "bot_initialized": self.bot is not None,
                "dp_initialized": self.dp is not None,
                "template_manager_initialized": self.template_manager is not None,
                "templates_loaded": (
                    len(self.template_manager.templates) if self.template_manager else 0
                ),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }

            # Проверяем критические компоненты
            if not self.bot or not self.dp or not self.template_manager:
                health_status["status"] = "unhealthy"
            elif not self.template_manager.templates:
                health_status["status"] = "degraded"

            return health_status

        except Exception as e:
            logger.error(f"Ошибка проверки здоровья: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }

    async def reload_templates(self):
        """Перезагрузка шаблонов"""
        if self.template_manager:
            try:
                await asyncio.to_thread(self.template_manager.reload_templates)
                logger.info("Шаблоны перезагружены")
            except Exception as e:
                logger.error(f"Ошибка перезагрузки шаблонов: {e}")
                raise


# Глобальный экземпляр управления жизненным циклом
bot_lifecycle = BotLifecycle()


async def start_bot():
    """Запуск бота"""
    await bot_lifecycle.start()


async def stop_bot():
    """Остановка бота"""
    await bot_lifecycle.shutdown()


async def restart_bot():
    """Перезапуск бота"""
    await bot_lifecycle.restart()


async def get_bot_health():
    """Получение статуса здоровья бота"""
    return await bot_lifecycle.health_check()


async def reload_bot_templates():
    """Перезагрузка шаблонов бота"""
    await bot_lifecycle.reload_templates()
