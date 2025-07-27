from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_USER_IDS


# Мапинг латинских названий категорий в кириллические
CATEGORY_MAPPING = {
    "visitki": "визитки",
    "futbolki": "футболки",
    "listovki": "листовки",
    "nakleyki": "наклейки",
    "bloknoty": "блокноты",
}

# Обратный мапинг для получения латинского названия
REVERSE_CATEGORY_MAPPING = {v: k for k, v in CATEGORY_MAPPING.items()}


def get_cyrillic_category(latin_category: str) -> str:
    """Преобразует латинское название категории в кириллическое"""
    return CATEGORY_MAPPING.get(latin_category, latin_category)


def get_latin_category(cyrillic_category: str) -> str:
    """Преобразует кириллическое название категории в латинское"""
    return REVERSE_CATEGORY_MAPPING.get(cyrillic_category, cyrillic_category)


def get_category_title(category: str, lang: str, template_manager=None) -> str:
    """Возвращает заголовок категории на нужном языке"""
    # Если передан template_manager, пытаемся получить название из первого шаблона категории
    if template_manager and category in template_manager.templates:
        templates = template_manager.templates[category]
        if templates:
            # Берем первый шаблон с валидным button_text для получения эмодзи/стиля
            for template in templates:
                if hasattr(template, "has_menu_button") and template.has_menu_button:
                    # Извлекаем эмодзи из button_text первого шаблона
                    button_text = template.button_text
                    if button_text and len(button_text) > 0:
                        # Пытаемся извлечь эмодзи (первый символ, если это эмодзи)
                        first_char = button_text[0] if button_text else "📦"
                        if ord(first_char) > 127:  # Простая проверка на эмодзи
                            emoji = first_char
                        else:
                            emoji = "📦"
                        break
            else:
                emoji = "📦"
        else:
            emoji = "📦"

        # Формируем название категории с правильным эмодзи
        titles = {
            "визитки": {"ukr": f"{emoji} Візитки", "rus": f"{emoji} Визитки"},
            "футболки": {"ukr": f"{emoji} Футболки", "rus": f"{emoji} Футболки"},
            "листовки": {"ukr": f"{emoji} Листівки", "rus": f"{emoji} Листовки"},
            "наклейки": {"ukr": f"{emoji} Наліпки", "rus": f"{emoji} Наклейки"},
            "блокноты": {"ukr": f"{emoji} Блокноти", "rus": f"{emoji} Блокноты"},
        }

        return titles.get(category, {}).get(lang, f"{emoji} {category.title()}")

    # Fallback к статичным значениям
    titles = {
        "визитки": {"ukr": "📇 Візитки", "rus": "📇 Визитки"},
        "футболки": {"ukr": "👕 Футболки", "rus": "👕 Футболки"},
        "листовки": {"ukr": "📄 Листівки", "rus": "📄 Листовки"},
        "наклейки": {"ukr": "🔖 Наліпки", "rus": "🔖 Наклейки"},
        "блокноты": {"ukr": "📋 Блокноти", "rus": "📋 Блокноты"},
    }

    return titles.get(category, {}).get(lang, f"📦 {category.title()}")


def create_main_menu_keyboard(user_id: int, template_manager) -> InlineKeyboardMarkup:
    """Создает клавиатуру главного меню"""
    lang = template_manager.get_user_language(user_id)

    builder = InlineKeyboardBuilder()

    # Основные категории
    builder.row(
        InlineKeyboardButton(
            text="📇 Візитки" if lang == "ukr" else "📇 Визитки",
            callback_data="category_visitki",
        )
    )
    builder.row(InlineKeyboardButton(text="👕 Футболки", callback_data="category_futbolki"))
    builder.row(
        InlineKeyboardButton(
            text="📄 Листівки" if lang == "ukr" else "📄 Листовки",
            callback_data="category_listovki",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔖 Наліпки" if lang == "ukr" else "🔖 Наклейки",
            callback_data="category_nakleyki",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Блокноти" if lang == "ukr" else "📋 Блокноты",
            callback_data="category_bloknoty",
        )
    )
    # Дополнительные функции
    builder.row(
        InlineKeyboardButton(
            text="🔍 Пошук" if lang == "ukr" else "🔍 Поиск", callback_data="search"
        )
    )

    # AI-режим с переключателем
    current_ai_mode = template_manager.get_user_ai_mode(user_id)
    if current_ai_mode == "enhanced":
        ai_text = "🎭 Олена (персонал.)" if lang == "ukr" else "🎭 Олена (персонал.)"
        ai_callback = "switch_to_standard_ai"
    else:
        ai_text = "🤖 AI-помічник" if lang == "ukr" else "🤖 AI-помощник"
        ai_callback = "switch_to_enhanced_ai"

    builder.row(InlineKeyboardButton(text=ai_text, callback_data=ai_callback))

    # Переключатель языка
    lang_text = "🇷🇺 Русский" if lang == "ukr" else "🇺🇦 Українська"
    builder.row(InlineKeyboardButton(text=lang_text, callback_data="switch_language"))

    # Админ-функции (если пользователь админ)
    if user_id in ADMIN_USER_IDS:
        builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))

    return builder.as_markup()


def create_category_menu_keyboard(
    category: str, user_id: int, template_manager
) -> InlineKeyboardMarkup:
    """Создает клавиатуру для конкретной категории"""
    builder = InlineKeyboardBuilder()

    if category in template_manager.templates:
        templates = template_manager.templates[category]
        latin_category = get_latin_category(category)  # Получаем латинское название

        # Добавляем кнопки только для шаблонов с валидным button_text
        for template in templates:
            if getattr(template, "has_menu_button", True):  # Обратная совместимость
                builder.row(
                    InlineKeyboardButton(
                        text=template.button_text,
                        callback_data=f"template_{latin_category}_{template.subcategory}",
                    )
                )

    # Кнопка "Назад"
    lang = template_manager.get_user_language(user_id)
    back_text = "⬅️ Назад" if lang == "ukr" else "⬅️ Назад"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    return builder.as_markup()


def create_template_keyboard(
    user_id: int, template_manager, template_data: str = None
) -> InlineKeyboardMarkup:
    """Создает клавиатуру для отображения шаблона"""
    lang = template_manager.get_user_language(user_id)
    builder = InlineKeyboardBuilder()

    # Кнопка "Копировать" - отправляет текст отдельным сообщением
    if template_data:
        copy_text = "📋 Копіювати" if lang == "ukr" else "📋 Копировать"
        builder.add(InlineKeyboardButton(text=copy_text, callback_data=f"copy_template"))

    # Кнопка "Назад"
    back_text = "⬅️ Назад" if lang == "ukr" else "⬅️ Назад"
    builder.add(InlineKeyboardButton(text=back_text, callback_data="back_to_category"))

    # Размещаем кнопки в одну строку
    builder.adjust(2)

    return builder.as_markup()
