import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, logger
from models import UserStates
from template_manager import TemplateManager
import handlers

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Глобальный менеджер шаблонов
template_manager = TemplateManager()


# Регистрация обработчиков
@dp.message(Command("start"))
async def cmd_start_wrapper(message, state):
    await handlers.cmd_start(message, state, template_manager)


@dp.message(Command("stats"))
async def cmd_stats_wrapper(message):
    await handlers.cmd_stats(message, template_manager)


@dp.callback_query(lambda c: c.data.startswith("category_"))
async def process_category_selection_wrapper(callback, state):
    await handlers.process_category_selection(callback, state, template_manager)


@dp.callback_query(lambda c: c.data.startswith("template_"))
async def process_template_selection_wrapper(callback, state):
    await handlers.process_template_selection(callback, state, template_manager)


@dp.callback_query(lambda c: c.data == "copy_template")
async def copy_template_text_wrapper(callback, state):
    await handlers.copy_template_text(callback, state, template_manager)


@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats_wrapper(callback):
    await handlers.admin_stats(callback, template_manager)


@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main_menu_wrapper(callback, state):
    await handlers.back_to_main_menu(callback, state, template_manager)


@dp.callback_query(lambda c: c.data == "back_to_category")
async def back_to_category_menu_wrapper(callback, state):
    await handlers.back_to_category_menu(callback, state, template_manager)


@dp.callback_query(lambda c: c.data == "switch_language")
async def switch_language_wrapper(callback, state):
    await handlers.switch_language(callback, state, template_manager)


@dp.callback_query(lambda c: c.data == "search")
async def start_search_wrapper(callback, state):
    await handlers.start_search(callback, state, template_manager)


@dp.message(StateFilter(UserStates.search_mode))
async def process_search_query_wrapper(message, state):
    await handlers.process_search_query(message, state, template_manager)


@dp.callback_query(lambda c: c.data == "coming_soon")
async def coming_soon_wrapper(callback):
    await handlers.coming_soon(callback, template_manager)


async def main():
    """Главная функция для запуска бота"""
    # Создаем директорию для данных, если её нет
    os.makedirs('./data', exist_ok=True)

    logger.info("Запуск бота...")
    logger.info(f"Загружены категории: {list(template_manager.templates.keys())}")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())