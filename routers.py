"""
Регистрация обработчиков (роутеров) бота
"""

from aiogram import Dispatcher
from aiogram.filters import Command, StateFilter

import handlers
from config import logger
from error_handler import error_handler
from models import UserStates
from template_manager import TemplateManager


class BotRouters:
    """Класс для регистрации обработчиков бота"""

    def __init__(self, dp: Dispatcher, template_manager: TemplateManager) -> None:
        self.dp = dp
        self.template_manager = template_manager
        self.bot_version = "1.05"

    def register_command_handlers(self) -> None:
        """Регистрация обработчиков команд"""

        @self.dp.message(Command("start"))
        async def cmd_start_wrapper(message, state) -> None:
            """Обработчик команды /start с проверкой версии"""
            # Получаем данные пользователя
            user_data = await state.get_data()
            current_user_version = user_data.get("bot_version")

            # Проверяем версию
            if current_user_version != self.bot_version:
                # Если версия отличается или отсутствует
                await state.clear()  # Очищаем старые данные
                await state.update_data(bot_version=self.bot_version)

                # Опционально: уведомляем об обновлении
                if current_user_version:  # Если это не первый запуск
                    await message.answer("🔄 Бот был обновлен! Загружаем новое меню...")

            # Вызываем обычный обработчик start
            await handlers.cmd_start(message, state, self.template_manager)

        @self.dp.message(Command("stats"))
        async def cmd_stats_wrapper(message) -> None:
            """Обработчик команды /stats"""
            await handlers.cmd_stats(message, self.template_manager)

        @self.dp.message(Command("reload"))
        async def cmd_reload_wrapper(message) -> None:
            """Обработчик команды /reload (перезагрузка шаблонов)"""
            await handlers.cmd_reload(message, self.template_manager)

        @self.dp.message(Command("health"))
        async def cmd_health_wrapper(message) -> None:
            """Обработчик команды /health (проверка здоровья системы)"""
            await handlers.cmd_health(message, self.template_manager)

        logger.info("Обработчики команд зарегистрированы")

    def register_callback_handlers(self) -> None:
        """Регистрация обработчиков callback-запросов"""

        @self.dp.callback_query(lambda c: c.data.startswith("category_"))
        async def process_category_selection_wrapper(callback, state) -> None:
            """Обработчик выбора категории"""
            await handlers.process_category_selection(callback, state, self.template_manager)

        @self.dp.callback_query(lambda c: c.data.startswith("template_"))
        async def process_template_selection_wrapper(callback, state) -> None:
            """Обработчик выбора шаблона"""
            await handlers.process_template_selection(callback, state, self.template_manager)

        @self.dp.callback_query(lambda c: c.data == "copy_template")
        async def copy_template_text_wrapper(callback, state) -> None:
            """Обработчик копирования шаблона"""
            await handlers.copy_template_text(callback, state, self.template_manager)

        @self.dp.callback_query(lambda c: c.data == "admin_stats")
        async def admin_stats_wrapper(callback) -> None:
            """Обработчик админской статистики"""
            await handlers.admin_stats(callback, self.template_manager)

        @self.dp.callback_query(lambda c: c.data == "back_to_main")
        async def back_to_main_menu_wrapper(callback, state) -> None:
            """Обработчик возврата в главное меню"""
            await handlers.back_to_main_menu(callback, state, self.template_manager)

        @self.dp.callback_query(lambda c: c.data == "back_to_category")
        async def back_to_category_menu_wrapper(callback, state) -> None:
            """Обработчик возврата в меню категории"""
            await handlers.back_to_category_menu(callback, state, self.template_manager)

        @self.dp.callback_query(lambda c: c.data == "switch_language")
        async def switch_language_wrapper(callback, state) -> None:
            """Обработчик переключения языка"""
            await handlers.switch_language(callback, state, self.template_manager)

        @self.dp.callback_query(lambda c: c.data == "search")
        async def start_search_wrapper(callback, state) -> None:
            """Обработчик начала поиска"""
            await handlers.start_search(callback, state, self.template_manager)

        @self.dp.callback_query(lambda c: c.data == "coming_soon")
        async def coming_soon_wrapper(callback) -> None:
            """Обработчик для функций в разработке"""
            await handlers.coming_soon(callback, self.template_manager)

        @self.dp.callback_query(lambda c: c.data == "ai_mode")
        async def start_ai_mode_wrapper(callback, state) -> None:
            """Обработчик перехода в AI-режим"""
            await handlers.start_ai_mode(callback, state, self.template_manager)

        @self.dp.callback_query(lambda c: c.data == "contact_manager")
        async def contact_manager_wrapper(callback) -> None:
            """Обработчик связи с менеджером"""
            await handlers.contact_manager(callback, self.template_manager)

        logger.info("Обработчики callback-запросов зарегистрированы")

    def register_message_handlers(self) -> None:
        """Регистрация обработчиков сообщений"""

        @self.dp.message(StateFilter(UserStates.search_mode))
        async def process_search_query_wrapper(message, state) -> None:
            """Обработчик поисковых запросов"""
            await handlers.process_search_query(message, state, self.template_manager)

        @self.dp.message(StateFilter(UserStates.ai_mode))
        async def process_ai_message_wrapper(message, state) -> None:
            """Обработчик AI-сообщений"""
            await handlers.process_ai_message(message, state, self.template_manager)

        logger.info("Обработчики сообщений зарегистрированы")

    def register_error_handlers(self) -> None:
        """Регистрация обработчиков ошибок"""

        async def global_error_handler(event, exception) -> bool:
            """Глобальный обработчик ошибок для dispatcher"""
            logger.error(f"Глобальная ошибка: {exception}")
            await error_handler.handle_error(exception, event)
            return True  # Помечаем как обработанную

        # Регистрируем обработчик ошибок
        self.dp.errors.register(global_error_handler)

        logger.info("Обработчики ошибок зарегистрированы")

    def register_all_handlers(self) -> None:
        """Регистрация всех обработчиков"""
        try:
            self.register_command_handlers()
            self.register_callback_handlers()
            self.register_message_handlers()
            self.register_error_handlers()

            logger.info("Все обработчики успешно зарегистрированы")

        except Exception as e:
            logger.critical(f"Ошибка регистрации обработчиков: {e}")
            raise


def register_handlers(dp: Dispatcher, template_manager: TemplateManager) -> BotRouters:
    """
    Функция для регистрации всех обработчиков

    Args:
        dp: Dispatcher
        template_manager: TemplateManager
    """
    routers = BotRouters(dp, template_manager)
    routers.register_all_handlers()
    return routers
