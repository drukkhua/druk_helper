from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_USER_IDS


def get_category_title(category: str, lang: str) -> str:
    """Возвращает заголовок категории на нужном языке"""
    titles = {
        'визитки': {'ukr': '📇 Візитки', 'rus': '📇 Визитки'},
        'футболки': {'ukr': '👕 Футболки', 'rus': '👕 Футболки'},
        'листовки': {'ukr': '📄 Листівки', 'rus': '📄 Листовки'}
    }

    return titles.get(category, {}).get(lang, f"📦 {category.title()}")


def create_main_menu_keyboard(user_id: int, template_manager) -> InlineKeyboardMarkup:
    """Создает клавиатуру главного меню"""
    lang = template_manager.get_user_language(user_id)

    builder = InlineKeyboardBuilder()

    # Основные категории
    builder.row(InlineKeyboardButton(text="📇 Візитки" if lang == 'ukr' else "📇 Визитки",
                                     callback_data="category_визитки"))
    builder.row(InlineKeyboardButton(text="👕 Футболки",
                                     callback_data="category_футболки"))
    builder.row(InlineKeyboardButton(text="📄 Листівки" if lang == 'ukr' else "📄 Листовки",
                                     callback_data="category_листовки"))
    builder.row(InlineKeyboardButton(text="🔖 Наліпки" if lang == 'ukr' else "🔖 Наклейки",
                                     callback_data="category_наклейки"))

    # Дополнительные функции
    builder.row(InlineKeyboardButton(text="🔍 Пошук" if lang == 'ukr' else "🔍 Поиск",
                                     callback_data="search"))

    # Переключатель языка
    lang_text = "🇷🇺 Русский" if lang == 'ukr' else "🇺🇦 Українська"
    builder.row(InlineKeyboardButton(text=lang_text, callback_data="switch_language"))

    # Админ-функции (если пользователь админ)
    if user_id in ADMIN_USER_IDS:
        builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))

    return builder.as_markup()


def create_category_menu_keyboard(category: str, user_id: int, template_manager) -> InlineKeyboardMarkup:
    """Создает клавиатуру для конкретной категории"""
    builder = InlineKeyboardBuilder()

    if category in template_manager.templates:
        templates = template_manager.templates[category]

        # Добавляем кнопки для каждого шаблона
        for template in templates:
            builder.row(InlineKeyboardButton(
                text=template.button_text,
                callback_data=f"template_{category}_{template.subcategory}"
            ))

    # Кнопка "Назад"
    lang = template_manager.get_user_language(user_id)
    back_text = "⬅️ Назад" if lang == 'ukr' else "⬅️ Назад"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    return builder.as_markup()


def create_template_keyboard(user_id: int, template_manager, template_data: str = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру для отображения шаблона"""
    lang = template_manager.get_user_language(user_id)
    builder = InlineKeyboardBuilder()

    # Кнопка "Копировать" - отправляет текст отдельным сообщением
    if template_data:
        copy_text = "📋 Копіювати" if lang == 'ukr' else "📋 Копировать"
        builder.add(InlineKeyboardButton(text=copy_text, callback_data=f"copy_template"))

    # Кнопка "Назад"
    back_text = "⬅️ Назад" if lang == 'ukr' else "⬅️ Назад"
    builder.add(InlineKeyboardButton(text=back_text, callback_data="back_to_category"))

    # Размещаем кнопки в одну строку
    builder.adjust(2)

    return builder.as_markup()
