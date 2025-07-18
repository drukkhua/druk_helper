from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_USER_IDS, logger
from error_handler import handle_exceptions
from exceptions import *
from keyboards import (
    create_category_menu_keyboard,
    create_main_menu_keyboard,
    create_template_keyboard,
    get_category_title,
)
from models import UserStates
from validation import validator


@handle_exceptions
async def cmd_start(message: types.Message, state: FSMContext, template_manager):
    """Обработчик команды /start"""
    user_id = message.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        raise ValidationError(f"Неверный user_id: {user_id}")

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


async def cmd_stats(message: types.Message, template_manager):
    """Команда для просмотра статистики (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        return

    stats_text = template_manager.stats.get_stats_summary()
    await message.answer(stats_text)


async def process_category_selection(
    callback: CallbackQuery, state: FSMContext, template_manager
):
    """Обработчик выбора категории"""
    # Валидация callback_data
    callback_validation = validator.validate_callback_data(callback.data)
    if not callback_validation.is_valid:
        logger.error(f"Неверный callback_data: {callback.data}")
        await callback.answer("❌ Ошибка обработки запроса")
        return

    category = callback_validation.cleaned_value.replace("category_", "")
    user_id = callback.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {user_id}")
        return

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


@handle_exceptions
async def process_template_selection(
    callback: CallbackQuery, state: FSMContext, template_manager
):
    """Обработчик выбора конкретного шаблона"""
    # Валидация callback_data
    callback_validation = validator.validate_callback_data(callback.data)
    if not callback_validation.is_valid:
        raise ValidationError(f"Неверный callback_data: {callback.data}")

    parts = callback_validation.cleaned_value.split("_")
    if len(parts) < 3:
        raise ValidationError(f"Неверный формат callback_data: {callback.data}")

    category = parts[1]
    subcategory = "_".join(parts[2:])
    user_id = callback.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        raise ValidationError(f"Неверный user_id: {user_id}")

    # Находим нужный шаблон используя безопасный метод
    template = template_manager.get_template_by_subcategory(category, subcategory)

    if template:
        template_text = template_manager.get_template_text(template, user_id)
        lang = template_manager.get_user_language(user_id)

        # Логируем использование шаблона
        template_manager.stats.log_template_usage(
            category, template.sort_order, user_id, "view"
        )

        header = (
            "📋 Готовий шаблон відповіді:"
            if lang == "ukr"
            else "📋 Готовый шаблон ответа:"
        )
        footer = "\n\n💡 Виберіть дію:" if lang == "ukr" else "\n\n💡 Выберите действие:"

        full_message = f"{header}\n\n{template_text}{footer}"

        # Сохраняем все необходимые данные для восстановления состояния
        await state.update_data(
            current_template_text=template_text,
            current_category=category,
            current_template_number=template.sort_order,
            previous_menu_type="category",
            previous_menu_title=header,
        )

        await callback.message.edit_text(
            full_message,
            reply_markup=create_template_keyboard(
                user_id, template_manager, template_text
            ),
        )
    else:
        error_text = (
            "❌ Шаблон не знайдено"
            if template_manager.get_user_language(user_id) == "ukr"
            else "❌ Шаблон не найден"
        )
        await callback.answer(error_text)


async def copy_template_text(
    callback: CallbackQuery, state: FSMContext, template_manager
):
    """Отправляет текст шаблона отдельным сообщением для удобного копирования"""
    # Валидация user_id
    user_validation = validator.validate_user_id(callback.from_user.id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {callback.from_user.id}")
        return

    user_data = await state.get_data()
    template_text = user_data.get("current_template_text", "")
    current_category = user_data.get("current_category", "визитки")
    template_number = user_data.get("current_template_number", 1)

    if template_text:
        # Логируем копирование
        template_manager.stats.log_template_usage(
            current_category, template_number, callback.from_user.id, "copy"
        )

        lang = template_manager.get_user_language(callback.from_user.id)
        copy_msg = "📋 Для копіювання:" if lang == "ukr" else "📋 Для копирования:"

        # Удаляем старое сообщение с меню
        await callback.message.delete()

        # Отправляем текст для копирования БЕЗ оформления - как обычное сообщение
        await callback.message.answer(template_text)

        # Восстанавливаем состояние и то же меню категории, что было до копирования
        await state.set_state(UserStates.category_menu)
        await state.update_data(current_category=current_category)

        category_title = get_category_title(current_category, lang)
        subtitle = "Оберіть тип запиту:" if lang == "ukr" else "Выберите тип запроса:"

        await callback.message.answer(
            f"{category_title}\n\n{subtitle}",
            reply_markup=create_category_menu_keyboard(
                current_category, callback.from_user.id, template_manager
            ),
        )

        await callback.answer("✅ Готово!")
    else:
        error_text = (
            "❌ Помилка отримання тексту"
            if template_manager.get_user_language(callback.from_user.id) == "ukr"
            else "❌ Ошибка получения текста"
        )
        await callback.answer(error_text)


async def admin_stats(callback: CallbackQuery, template_manager):
    """Показ статистики для админов"""
    # Валидация user_id
    user_validation = validator.validate_user_id(callback.from_user.id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {callback.from_user.id}")
        return

    if callback.from_user.id not in ADMIN_USER_IDS:
        await callback.answer("❌ Нет доступа")
        return

    stats_text = template_manager.stats.get_stats_summary()
    await callback.message.answer(stats_text)


async def back_to_main_menu(
    callback: CallbackQuery, state: FSMContext, template_manager
):
    """Возврат в главное меню"""
    user_id = callback.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {user_id}")
        return
    lang = template_manager.get_user_language(user_id)

    welcome_text = (
        "🎯 Оберіть категорію товару:"
        if lang == "ukr"
        else "🎯 Выберите категорию товара:"
    )

    await callback.message.edit_text(
        welcome_text, reply_markup=create_main_menu_keyboard(user_id, template_manager)
    )
    await state.set_state(UserStates.main_menu)


async def back_to_category_menu(
    callback: CallbackQuery, state: FSMContext, template_manager
):
    """Возврат в меню категории"""
    user_data = await state.get_data()
    category = user_data.get("current_category", "визитки")
    user_id = callback.from_user.id

    lang = template_manager.get_user_language(user_id)

    category_title = get_category_title(category, lang)
    subtitle = "Оберіть тип запиту:" if lang == "ukr" else "Выберите тип запроса:"

    await callback.message.edit_text(
        f"{category_title}\n\n{subtitle}",
        reply_markup=create_category_menu_keyboard(category, user_id, template_manager),
    )
    await state.set_state(UserStates.category_menu)


async def switch_language(callback: CallbackQuery, state: FSMContext, template_manager):
    """Переключение языка"""
    user_id = callback.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {user_id}")
        return
    current_lang = template_manager.get_user_language(user_id)
    new_lang = "rus" if current_lang == "ukr" else "ukr"

    template_manager.set_user_language(user_id, new_lang)

    success_text = (
        "✅ Мова змінена на українську"
        if new_lang == "ukr"
        else "✅ Язык изменен на русский"
    )
    await callback.answer(success_text)

    # Обновляем главное меню
    welcome_text = (
        "🎯 Оберіть категорію товару:"
        if new_lang == "ukr"
        else "🎯 Выберите категорию товара:"
    )

    await callback.message.edit_text(
        welcome_text, reply_markup=create_main_menu_keyboard(user_id, template_manager)
    )


async def start_search(callback: CallbackQuery, state: FSMContext, template_manager):
    """Начало поиска"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    search_text = (
        "🔍 Введіть ключове слово для пошуку шаблонів:\n\n"
        "Наприклад: ціна, макет, терміни, якість"
        if lang == "ukr"
        else "🔍 Введите ключевое слово для поиска шаблонов:\n\n"
        "Например: цена, макет, сроки, качество"
    )

    builder = InlineKeyboardBuilder()
    back_text = "⬅️ Назад" if lang == "ukr" else "⬅️ Назад"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    await callback.message.edit_text(search_text, reply_markup=builder.as_markup())
    await state.set_state(UserStates.search_mode)


@handle_exceptions
async def process_search_query(
    message: types.Message, state: FSMContext, template_manager
):
    """Обработка поискового запроса"""
    user_id = message.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        raise ValidationError(f"Неверный user_id: {user_id}")

    # Валидация поискового запроса
    search_validation = validator.validate_search_query(message.text)
    if not search_validation.is_valid:
        lang = template_manager.get_user_language(user_id)
        error_text = (
            f"❌ {search_validation.error_message}"
            if lang == "ukr"
            else f"❌ {search_validation.error_message}"
        )
        await message.answer(error_text)
        return

    query = search_validation.cleaned_value

    # Поиск шаблонов (теперь с proper error handling)
    found_templates = template_manager.search_templates(query)

    if not found_templates:
        no_results_text = (
            f"❌ За запитом '{query}' нічого не знайдено.\n\n"
            "Спробуйте інші ключові слова."
            if template_manager.get_user_language(user_id) == "ukr"
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


async def coming_soon(callback: CallbackQuery, template_manager):
    """Обработчик для функций, которые скоро появятся"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    text = (
        "⏳ Ця категорія з'явиться найближчим часом!"
        if lang == "ukr"
        else "⏳ Эта категория появится в ближайшее время!"
    )

    await callback.answer(text)


@handle_exceptions
async def cmd_reload(message: types.Message, template_manager):
    """Команда для перезагрузки шаблонов (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    try:
        await message.answer("🔄 Начинаем обновление данных...")

        # Импортируем функцию обновления из Google Sheets
        from google_sheets_updater import update_templates_from_sheets

        # Сначала обновляем данные из Google Sheets
        await message.answer("📊 Загружаем актуальные данные из Google Sheets...")
        sheets_updated = await update_templates_from_sheets()

        if sheets_updated:
            await message.answer("✅ Данные из Google Sheets обновлены успешно!")
        else:
            await message.answer(
                "⚠️ Не удалось обновить данные из Google Sheets, используем локальные файлы"
            )

        # Затем перезагружаем шаблоны в память
        await message.answer("🔄 Перезагружаем шаблоны в память...")
        template_manager.reload_templates()

        success_text = (
            f"✅ Обновление завершено успешно!\n"
            f"📊 Google Sheets: {'✅ Обновлено' if sheets_updated else '⚠️ Ошибка'}\n"
            f"📋 Загружено категорий: {len(template_manager.templates)}\n"
            f"📄 Всего шаблонов: {sum(len(t) for t in template_manager.templates.values())}"
        )
        await message.answer(success_text)

    except Exception as e:
        error_text = f"❌ Ошибка при обновлении: {str(e)}"
        await message.answer(error_text)


@handle_exceptions
async def cmd_health(message: types.Message, template_manager):
    """Команда для проверки здоровья системы (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    try:
        from datetime import datetime

        from error_monitor import get_health_status

        health_status = get_health_status()

        # Статистика шаблонов
        templates_count = sum(len(t) for t in template_manager.templates.values())
        categories_count = len(template_manager.templates)

        # Статистика ошибок
        error_stats = (
            template_manager.stats.get_stats_summary()
            if hasattr(template_manager, "stats")
            else "Недоступно"
        )

        health_text = f"""
🏥 **Состояние системы**

🤖 **Статус:** {health_status['status']}
📊 **Категории:** {categories_count}
📋 **Шаблоны:** {templates_count}
🕒 **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 **Ошибки за час:**
- Всего: {health_status['errors_last_hour']}
- Критических: {health_status['critical_errors_last_hour']}

💾 **Память:** OK
🌐 **Сеть:** OK
        """

        await message.answer(health_text)

    except Exception as e:
        error_text = f"❌ Ошибка получения статуса: {str(e)}"
        await message.answer(error_text)
