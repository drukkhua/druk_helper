"""
Безопасные обработчики с автоматической валидацией
Пример использования декораторов безопасности
"""

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards import create_main_menu_keyboard
from models import UserStates
from security_decorators import (
    admin_only,
    rate_limit,
    validate_callback_data,
    validate_message_text,
    validate_user_id,
)


@validate_user_id
@rate_limit(calls_per_minute=10)
async def secure_start(message: types.Message, state: FSMContext, template_manager):
    """Безопасный обработчик команды /start"""
    user_id = message.from_user.id

    welcome_text = (
        "👋 Привіт! Я бот-помічник для швидких відповідей клієнтам.\n\n"
        "🎯 Оберіть категорію товару, щоб отримати готові шаблони відповідей:"
        if template_manager.get_user_language(user_id) == "ukr"
        else "👋 Привет! Я бот-помощник для быстрых ответов клиентам.\n\n"
        "🎯 Выберите категорию товара, чтобы получить готовые шаблоны ответов:"
    )

    await message.answer(
        welcome_text, reply_markup=create_main_menu_keyboard(user_id, template_manager)
    )
    await state.set_state(UserStates.main_menu)


@validate_user_id
@validate_callback_data
@rate_limit(calls_per_minute=20)
async def secure_category_selection(
    callback: CallbackQuery, state: FSMContext, template_manager
):
    """Безопасный обработчик выбора категории"""
    from keyboards import create_category_menu_keyboard, get_category_title

    category = callback.data.replace("category_", "")
    user_id = callback.from_user.id

    lang = template_manager.get_user_language(user_id)

    # Проверяем, есть ли шаблоны для этой категории
    if (
        category not in template_manager.templates
        or not template_manager.templates[category]
    ):
        error_text = (
            f"⏳ Шаблони для категорії '{category}' ще не додані.\nЗ'являться найближчим часом!"
            if lang == "ukr"
            else f"⏳ Шаблоны для категории '{category}' еще не добавлены.\nПоявятся в ближайшее время!"
        )
        await callback.answer(error_text)
        return

    # Определяем заголовок категории
    title = get_category_title(category, lang)
    subtitle = "Оберіть тип запиту:" if lang == "ukr" else "Выберите тип запроса:"

    await callback.message.edit_text(
        f"{title}\n\n{subtitle}",
        reply_markup=create_category_menu_keyboard(category, user_id, template_manager),
    )

    await state.update_data(current_category=category)
    await state.set_state(UserStates.category_menu)


@validate_user_id
@validate_message_text
@rate_limit(calls_per_minute=15)
async def secure_search_query(
    message: types.Message, state: FSMContext, template_manager
):
    """Безопасный обработчик поискового запроса"""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    user_id = message.from_user.id
    query = message.text.strip()

    # Поиск шаблонов (уже с валидацией внутри)
    found_templates = template_manager.search_templates(query)

    if not found_templates:
        lang = template_manager.get_user_language(user_id)
        no_results_text = (
            f"❌ За запитом '{query}' нічого не знайдено.\n\n"
            "Спробуйте інші ключові слова."
            if lang == "ukr"
            else f"❌ По запросу '{query}' ничего не найдено.\n\n"
            "Попробуйте другие ключевые слова."
        )
        await message.answer(no_results_text)
        return

    # Показываем результаты поиска
    builder = InlineKeyboardBuilder()

    for template in found_templates[:10]:  # Ограничиваем 10 результатами
        builder.row(
            InlineKeyboardButton(
                text=f"{template.button_text}",
                callback_data=f"template_{template.category}_{template.subcategory}",
            )
        )

    lang = template_manager.get_user_language(user_id)
    back_text = "⬅️ Назад" if lang == "ukr" else "⬅️ Назад"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    results_text = (
        f"🔍 Знайдено {len(found_templates)} результатів за запитом '{query}':"
        if lang == "ukr"
        else f"🔍 Найдено {len(found_templates)} результатов по запросу '{query}':"
    )

    await message.answer(results_text, reply_markup=builder.as_markup())


@validate_user_id
@admin_only
@rate_limit(calls_per_minute=5)
async def secure_admin_stats(callback: CallbackQuery, template_manager):
    """Безопасный обработчик статистики для админов"""
    stats_text = template_manager.stats.get_stats_summary()
    await callback.message.answer(stats_text)
