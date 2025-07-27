"""
Пример интеграции системы менеджеров с основным ботом
Показывает, как подключить все модули к главному обработчику сообщений
"""

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from typing import Dict, Optional
import logging
import asyncio
from datetime import datetime

# Импорты системы менеджеров
from src.managers.integration import (
    setup_manager_system,
    get_manager_router,
    process_client_message,
    save_conversation_message,
    is_manager_available,
    health_check,
)
from src.managers.models import unified_db
from config import Config

logger = logging.getLogger(__name__)

# Основной роутер бота
main_router = Router()


async def initialize_bot_with_managers(bot: Bot, dp: Dispatcher):
    """
    Инициализация бота с системой менеджеров

    Args:
        bot: Экземпляр бота
        dp: Диспетчер
    """
    try:
        # Настраиваем систему менеджеров
        if not await setup_manager_system(bot):
            logger.error("Не удалось инициализировать систему менеджеров")
            return False

        # Подключаем роутер менеджеров
        manager_router = get_manager_router()
        dp.include_router(manager_router)

        # Подключаем основной роутер
        dp.include_router(main_router)

        logger.info("Бот с системой менеджеров инициализирован успешно")
        return True

    except Exception as e:
        logger.error(f"Ошибка инициализации бота: {e}")
        return False


@main_router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Команда /start с интеграцией системы менеджеров"""

    try:
        # Сохраняем команду start в историю
        await save_conversation_message(
            user_id=message.from_user.id,
            message_type="user",
            content="/start",
            metadata={"command": True},
        )

        # Проверяем доступность менеджеров
        managers_available = is_manager_available()

        welcome_text = f"""👋 Добро пожаловать в "Яркая печать"!

🎨 Мы занимаемся качественной полиграфией:
• Визитки, листовки, наклейки
• Быстрые сроки и доступные цены
• Профессиональная консультация

{'🟢 Наши менеджеры сейчас онлайн!' if managers_available else '🔴 Менеджеры сейчас офлайн, но мы обязательно ответим!'}

💬 Опишите, что вас интересует, или отправьте готовый макет!

📋 Доступные команды:
• /history - история ваших обращений
• /help - помощь"""

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="💰 Прайс-лист", callback_data="show_prices"),
                    types.InlineKeyboardButton(text="📞 Контакты", callback_data="show_contacts"),
                ],
                [
                    types.InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders"),
                    types.InlineKeyboardButton(
                        text="❓ Часто задаваемые вопросы", callback_data="show_faq"
                    ),
                ],
            ]
        )

        await message.answer(welcome_text, reply_markup=keyboard)

        # Сохраняем ответ в историю
        await save_conversation_message(
            user_id=message.from_user.id,
            message_type="assistant",
            content=welcome_text,
            metadata={
                "command_response": True,
                "managers_available": managers_available,
                "response_type": "welcome",
            },
        )

        # Уведомляем менеджеров о новом пользователе (если это первый визит)
        user_history = unified_db.get_user_history(message.from_user.id, limit=2)
        if len(user_history) <= 2:  # Новый пользователь
            await process_client_message(
                message=message,
                response_text=welcome_text,
                metadata={"new_user": True, "urgency": "low", "category": "welcome"},
            )

    except Exception as e:
        logger.error(f"Ошибка обработки команды /start: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")


@main_router.message(F.text & ~F.text.startswith("/"))
async def handle_text_messages(message: types.Message, state: FSMContext):
    """
    Обработка текстовых сообщений с интеграцией менеджеров

    Здесь можно интегрировать любую логику обработки:
    - AI-ответы
    - Поиск в базе знаний
    - Автоматические ответы
    """

    try:
        user_id = message.from_user.id
        query_text = message.text

        # Сохраняем вопрос пользователя
        await save_conversation_message(
            user_id=user_id,
            message_type="user",
            content=query_text,
            metadata={"timestamp": datetime.now().isoformat()},
        )

        # --- ЗДЕСЬ ВСТАВЛЯЕТСЯ ВАША ЛОГИКА ОБРАБОТКИ ---
        # Например:
        # 1. Поиск в базе знаний
        # 2. AI-анализ запроса
        # 3. Генерация ответа

        # Для примера - простая логика
        response_text, metadata = await generate_response(query_text, user_id)

        # Отправляем ответ пользователю
        await message.answer(response_text)

        # Обрабатываем через систему менеджеров
        await process_client_message(
            message=message, response_text=response_text, metadata=metadata
        )

    except Exception as e:
        logger.error(f"Ошибка обработки текстового сообщения: {e}")
        await message.answer("❌ Произошла ошибка при обработке сообщения.")


@main_router.message(F.document)
async def handle_document_upload(message: types.Message, state: FSMContext):
    """Обработка загрузки файлов (макетов)"""

    try:
        user_id = message.from_user.id
        document = message.document

        # Анализируем файл
        file_analysis = analyze_uploaded_file(document)

        # Генерируем ответ о файле
        file_response = generate_file_response(file_analysis)

        # Отправляем ответ пользователю
        await message.answer(file_response)

        # Уведомляем менеджеров через систему (высокий приоритет для файлов)
        await process_client_message(
            message=message,
            response_text=file_response,
            metadata={
                "file_analysis": file_analysis,
                "urgency": "high",
                "category": "files",
                "requires_manager_attention": True,
            },
        )

    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}")
        await message.answer("❌ Ошибка при обработке файла.")


@main_router.message(F.photo)
async def handle_photo_upload(message: types.Message, state: FSMContext):
    """Обработка загрузки фотографий"""

    try:
        # Простой ответ на фото
        photo_response = """📸 Фото получено!

⚠️ Для качественной печати лучше отправить файл в векторном формате (AI, EPS, PDF) или высококачественном растровом (PSD, TIFF).

🔍 Наши менеджеры оценят качество изображения и свяжутся с вами для уточнений."""

        await message.answer(photo_response)

        # Уведомляем менеджеров
        await process_client_message(
            message=message,
            response_text=photo_response,
            metadata={"media_type": "photo", "urgency": "normal", "category": "media"},
        )

    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}")
        await message.answer("❌ Ошибка при обработке фото.")


# Обработчики callback-ов
@main_router.callback_query(F.data == "show_prices")
async def show_prices(callback: types.CallbackQuery):
    """Показывает прайс-лист"""

    prices_text = """💰 **Наш прайс-лист**

📇 **Визитки:**
• Стандартные (300 гр/м²): от 0.50 грн/шт
• Премиум (350 гр/м²): от 0.80 грн/шт
• С ламинацией: от 1.20 грн/шт

📄 **Листовки:**
• А6 (105×148 мм): от 0.80 грн/шт
• А5 (148×210 мм): от 1.20 грн/шт
• А4 (210×297 мм): от 2.00 грн/шт

🏷️ **Наклейки:**
• Круглые (от 2 см): от 0.30 грн/шт
• Фигурные: от 0.50 грн/шт
• Прозрачные: от 0.80 грн/шт

⏰ **Сроки:** 1-3 рабочих дня
📞 **Минимальный заказ:** от 100 шт

💡 Точную стоимость рассчитают наши менеджеры!"""

    await callback.message.edit_text(
        prices_text,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
            ]
        ),
        parse_mode="Markdown",
    )

    # Логируем просмотр цен
    await save_conversation_message(
        user_id=callback.from_user.id,
        message_type="assistant",
        content=prices_text,
        metadata={"action": "price_list_viewed"},
    )


@main_router.callback_query(F.data == "show_contacts")
async def show_contacts(callback: types.CallbackQuery):
    """Показывает контакты"""

    contacts_text = """📞 **Наши контакты**

🏢 **Адрес:** г. Киев, ул. Печатная, 123

📱 **Телефоны:**
• +38 (044) 123-45-67
• +38 (050) 123-45-67

🕐 **Рабочее время:**
• Пн-Пт: 9:00 - 18:00
• Сб: 10:00 - 16:00
• Вс: выходной

🌐 **Интернет:**
• Сайт: print-company.ua
• Email: info@print-company.ua
• Instagram: @print_company_ua

🚗 **Как добраться:**
• Метро "Печатники" (5 мин пешком)
• Остановка "Типография" (автобус 15, 27)"""

    await callback.message.edit_text(
        contacts_text,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
            ]
        ),
        parse_mode="Markdown",
    )


@main_router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery):
    """Возврат к стартовому сообщению"""

    await cmd_start(callback.message, None)


# Вспомогательные функции
async def generate_response(query_text: str, user_id: int) -> tuple:
    """
    Генерирует ответ на запрос пользователя

    Args:
        query_text: Текст запроса
        user_id: ID пользователя

    Returns:
        tuple: (response_text, metadata)
    """

    # Простая логика для примера
    query_lower = query_text.lower()

    # Проверяем на ключевые слова
    if any(word in query_lower for word in ["цена", "стоимость", "сколько"]):
        response = """💰 **Стоимость зависит от:**
• Тиража (количества)
• Материала и плотности бумаги
• Размера изделия
• Сложности макета

📋 Для точного расчета пришлите:
• Размеры изделия
• Желаемый тираж
• Макет (если есть)

🎯 Наши менеджеры рассчитают стоимость в течение 15 минут!"""

        metadata = {
            "category": "pricing",
            "confidence": 0.9,
            "has_upselling": False,
            "urgency": "normal",
        }

    elif any(word in query_lower for word in ["срок", "когда", "быстро"]):
        response = """⏰ **Сроки изготовления:**

🔥 **Срочно (24 часа):** +50% к стоимости
⚡ **Быстро (1-2 дня):** стандартная цена
📅 **Обычно (3-5 дней):** скидка 10%

📋 **Сроки зависят от:**
• Сложности макета
• Количества изделий
• Загруженности производства

💡 Точные сроки назовут наши менеджеры после анализа заказа!"""

        metadata = {
            "category": "timing",
            "confidence": 0.85,
            "has_upselling": True,
            "urgency": "normal",
        }

    else:
        # Общий ответ
        response = """👋 Спасибо за обращение!

🎨 Мы поможем вам с:
• Дизайном и версткой макетов
• Выбором подходящих материалов
• Расчетом оптимального тиража
• Быстрым изготовлением

💬 Расскажите подробнее о ваших потребностях, и наши менеджеры подготовят персональное предложение!"""

        metadata = {
            "category": "general",
            "confidence": 0.7,
            "has_upselling": False,
            "urgency": "normal",
        }

    return response, metadata


def analyze_uploaded_file(document: types.Document) -> Dict:
    """Анализирует загруженный файл"""

    file_name = document.file_name or "unknown"
    file_size = document.file_size or 0
    file_ext = file_name.split(".")[-1].lower() if "." in file_name else ""

    # Определяем тип файла
    vector_formats = ["ai", "eps", "pdf", "svg"]
    raster_formats = ["psd", "tiff", "tif", "png", "jpg", "jpeg"]

    if file_ext in vector_formats:
        file_type = "vector"
        quality = "excellent"
    elif file_ext in raster_formats:
        file_type = "raster"
        quality = "good" if file_size > 5 * 1024 * 1024 else "medium"
    else:
        file_type = "unknown"
        quality = "needs_check"

    return {
        "file_name": file_name,
        "file_size": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "file_extension": file_ext,
        "file_type": file_type,
        "quality_assessment": quality,
        "suitable_for_print": file_type in ["vector", "raster"],
    }


def generate_file_response(file_analysis: Dict) -> str:
    """Генерирует ответ на загрузку файла"""

    if not file_analysis["suitable_for_print"]:
        return f"""❌ Формат {file_analysis['file_extension'].upper()} не подходит для полиграфии.

📋 Поддерживаемые форматы:
• Векторные: AI, EPS, PDF, SVG
• Растровые: PSD, TIFF, PNG, JPG

💡 Наши менеджеры свяжутся с вами для уточнений!"""

    quality_emoji = {"excellent": "🌟", "good": "✅", "medium": "⚠️", "needs_check": "🔍"}

    emoji = quality_emoji.get(file_analysis["quality_assessment"], "❓")

    return f"""✅ Файл "{file_analysis['file_name']}" получен!

📋 Анализ файла:
• Формат: {file_analysis['file_extension'].upper()}
• Размер: {file_analysis['file_size_mb']} МБ
• Качество для печати: {emoji} {file_analysis['quality_assessment']}

🔍 Наши менеджеры проверят макет и свяжутся с вами с детальным расчетом в течение 30 минут!

💡 Нужна дополнительная информация? Напишите ваши пожелания!"""


# Команды для проверки системы
@main_router.message(Command("system_health"))
async def cmd_system_health(message: types.Message):
    """Проверка состояния системы (только для админов)"""

    if message.from_user.id not in getattr(Config, "ADMIN_USER_IDS", []):
        return

    try:
        health_status = await health_check()

        status_text = f"""🏥 **Состояние системы**

🔋 **Статус:** {health_status.get('status', 'unknown')}
💾 **База данных:** {'✅' if health_status.get('database_connected') else '❌'}
🤖 **Уведомления:** {'✅' if health_status.get('notification_system') else '❌'}

👥 **Менеджеры:**
• Всего: {health_status.get('total_managers', 0)}
• Активных: {health_status.get('active_managers', 0)}
• Доступных: {health_status.get('available_managers', 0)}

💬 **Активных чатов:** {health_status.get('active_chats', 0)}"""

        await message.answer(status_text, parse_mode="Markdown")

    except Exception as e:
        await message.answer(f"❌ Ошибка проверки: {e}")
