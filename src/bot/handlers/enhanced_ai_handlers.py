"""
Обработчики для улучшенного AI с персонажем "Олена"
Интегрируется с основной системой бота для тестирования персонализированных ответов
"""

import asyncio
import logging
from typing import Dict

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_USER_IDS, logger
from src.utils.error_handler import handle_exceptions
from src.bot.models import UserStates
from src.ai.enhanced_ai_service import enhanced_ai_service
from src.ai.service import ai_service  # Оригинальный для сравнения
from src.core.validation import validator

router = Router()


class EnhancedAIStates(StatesGroup):
    """Дополнительные состояния для улучшенного AI"""

    enhanced_ai_mode = State()
    comparison_mode = State()


def detect_user_language(message: types.Message) -> str:
    """Определяет язык пользователя на основе текста сообщения"""
    if not message.text:
        return "ukr"

    text = message.text.lower()

    # Украинские слова-маркеры
    ukrainian_words = [
        "що",
        "як",
        "де",
        "коли",
        "чому",
        "скільки",
        "візитки",
        "ціна",
        "друк",
        "макет",
    ]
    russian_words = [
        "что",
        "как",
        "где",
        "когда",
        "почему",
        "сколько",
        "визитки",
        "цена",
        "печать",
        "макет",
    ]

    ukr_count = sum(1 for word in ukrainian_words if word in text)
    rus_count = sum(1 for word in russian_words if word in text)

    return "ukr" if ukr_count >= rus_count else "rus"


@router.message(Command("enhanced"))
@handle_exceptions
async def cmd_enhanced_mode(message: types.Message, state: FSMContext, template_manager) -> None:
    """Включает режим персонализированного AI с Оленой"""

    user_id = message.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {user_id}")
        return

    # Проверяем доступность улучшенного AI
    if not enhanced_ai_service.is_available():
        await message.answer(
            "😔 Персонализированный AI сейчас недоступен.\n"
            "Используйте /ai для стандартного режима."
        )
        return

    # Получаем информацию о сервисе
    service_info = enhanced_ai_service.get_service_info()
    lang = template_manager.get_user_language(user_id)

    if lang == "ukr":
        welcome_text = f"""🎭 **Вітаю в персоналізованому режимі з {service_info['persona_name']}!**

Тепер ви спілкуєтеся з нашим покращеним AI-помічником.

✨ **Що змінилося:**
• Більш живе та природне спілкування
• Пам'ять про ваші попередні звернення
• Уточнюючі запитання для кращого розуміння
• Персональні поради на основі досвіду
• Емоціональна адаптація до вашого настрою

🤖 **Технічна інформація:**
• Сервіс: {service_info['service_type']}
• AI режим: {'Реальний OpenAI' if service_info['real_ai'] else 'Mock режим'}
• База знань: {'Готова' if service_info['knowledge_ready'] else 'Недоступна'}
• Модель: {service_info.get('model', 'Unknown')}

Задавайте будь-які питання! 😊

Команди:
• /compare - порівняти з звичайним AI
• /normal - повернутися до звичайного режиму
• /enhanced_stats - статистика персоналізації"""
    else:
        welcome_text = f"""🎭 **Добро пожаловать в персонализированный режим с {service_info['persona_name']}!**

Теперь вы общаетесь с нашим улучшенным AI-помощником.

✨ **Что изменилось:**
• Более живое и естественное общение
• Память о ваших предыдущих обращениях
• Уточняющие вопросы для лучшего понимания
• Персональные советы на основе опыта
• Эмоциональная адаптация к вашему настрою

🤖 **Техническая информация:**
• Сервис: {service_info['service_type']}
• AI режим: {'Реальный OpenAI' if service_info['real_ai'] else 'Mock режим'}
• База знаний: {'Готова' if service_info['knowledge_ready'] else 'Недоступна'}
• Модель: {service_info.get('model', 'Unknown')}

Задавайте любые вопросы! 😊

Команды:
• /compare - сравнить с обычным AI
• /normal - вернуться к обычному режиму
• /enhanced_stats - статистика персонализации"""

    await message.answer(welcome_text, parse_mode="Markdown")
    await state.set_state(EnhancedAIStates.enhanced_ai_mode)


@router.message(Command("compare"))
@handle_exceptions
async def cmd_compare_mode(message: types.Message, state: FSMContext, template_manager) -> None:
    """Режим сравнения обычного и улучшенного AI"""

    user_id = message.from_user.id
    lang = template_manager.get_user_language(user_id)

    if lang == "ukr":
        text = (
            "🔍 **Режим порівняння AI**\n\n"
            "Надішліть питання, і я покажу відповіді від звичайного та персоналізованого AI.\n\n"
            "Це допоможе побачити різницю в підходах до відповідей.\n\n"
            "⚠️ **Увага:** Режим порівняння використовує вдвічі більше токенів OpenAI.\n\n"
            "Команда /normal для виходу з режиму порівняння."
        )
    else:
        text = (
            "🔍 **Режим сравнения AI**\n\n"
            "Отправьте вопрос, и я покажу ответы от обычного и персонализированного AI.\n\n"
            "Это поможет увидеть разницу в подходах к ответам.\n\n"
            "⚠️ **Внимание:** Режим сравнения использует в 2 раза больше токенов OpenAI.\n\n"
            "Команда /normal для выхода из режима сравнения."
        )

    await message.answer(text, parse_mode="Markdown")
    await state.set_state(EnhancedAIStates.comparison_mode)


@router.message(Command("enhanced_stats"))
@handle_exceptions
async def cmd_enhanced_stats(message: types.Message, template_manager) -> None:
    """Показывает статистику персонализации"""

    user_id = message.from_user.id
    lang = template_manager.get_user_language(user_id)

    try:
        # Получаем статистику пользователя из базы данных
        from src.managers.models import unified_db

        stats = unified_db.get_user_stats_summary(user_id)

        if not stats or stats.get("total_messages", 0) == 0:
            if lang == "ukr":
                text = (
                    "📊 **Статистика персоналізації**\n\n"
                    "У вас поки немає історії спілкування.\n"
                    "Поставте кілька питань, і я зможу краще адаптуватися під ваші потреби! 😊"
                )
            else:
                text = (
                    "📊 **Статистика персонализации**\n\n"
                    "У вас пока нет истории общения.\n"
                    "Задайте несколько вопросов, и я смогу лучше адаптироваться под ваши потребности! 😊"
                )
            await message.answer(text)
            return

        if lang == "ukr":
            stats_text = f"""📊 **Ваша статистика персоналізації**

👤 **Загальна активність:**
• Всього повідомлень: {stats.get('total_messages', 0)}
• Ваших запитань: {stats.get('user_messages', 0)}
• Отримано відповідей: {stats.get('assistant_messages', 0)}
• З персональними порадами: {stats.get('upselling_messages', 0)}

🎯 **Персоналізація:**
• Улюблена тема: {stats.get('top_category') or 'Визначається'}
• Перше звернення: {stats.get('first_message') or 'Нещодавно'}

💡 **Як це використовується:**
• Олена пам'ятає ваші інтереси та може давати більш точні поради
• Адаптує стиль спілкування під ваші уподобання
• Пропонує релевантні додаткові послуги
• Враховує ваш досвід роботи з типографією

🚀 **Чим більше спілкуєтеся, тим точнішими стають відповіді!**"""
        else:
            stats_text = f"""📊 **Ваша статистика персонализации**

👤 **Общая активность:**
• Всего сообщений: {stats.get('total_messages', 0)}
• Ваших вопросов: {stats.get('user_messages', 0)}
• Получено ответов: {stats.get('assistant_messages', 0)}
• С персональными советами: {stats.get('upselling_messages', 0)}

🎯 **Персонализация:**
• Любимая тема: {stats.get('top_category') or 'Определяется'}
• Первое обращение: {stats.get('first_message') or 'Недавно'}

💡 **Как это используется:**
• Олena помнит ваши интересы и может давать более точные советы
• Адаптирует стиль общения под ваши предпочтения
• Предлагает релевантные дополнительные услуги
• Учитывает ваш опыт работы с типографией

🚀 **Чем больше общаетесь, тем точнее становятся ответы!**"""

        await message.answer(stats_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка получения статистики персонализации: {e}")
        error_text = (
            "❌ Ошибка получения статистики. Попробуйте позже."
            if lang == "rus"
            else "❌ Помилка отримання статистики. Спробуйте пізніше."
        )
        await message.answer(error_text)


@router.message(EnhancedAIStates.enhanced_ai_mode)
@handle_exceptions
async def handle_enhanced_ai_message(
    message: types.Message, state: FSMContext, template_manager
) -> None:
    """Обрабатывает сообщения в режиме персонализированного AI"""

    user_id = message.from_user.id
    user_text = message.text

    # Валидация
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {user_id}")
        return

    if not user_text:
        lang = template_manager.get_user_language(user_id)
        error_text = (
            "Пожалуйста, отправьте текстовое сообщение 😊"
            if lang == "rus"
            else "Будь ласка, надішліть текстове повідомлення 😊"
        )
        await message.answer(error_text)
        return

    # Показываем индикатор печатания
    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        # Определяем язык пользователя
        lang = detect_user_language(message)

        # Добавляем небольшую задержку для имитации "обдумывания"
        await asyncio.sleep(1)

        # Обрабатываем через улучшенный AI
        ai_result = await enhanced_ai_service.process_query(user_text, user_id, lang)

        # Формируем ответ
        response_text = ai_result["answer"]

        # Добавляем информацию для отладки (только для админов)
        if user_id in ADMIN_USER_IDS:
            debug_info = f"""

🔧 **Debug info (только для админа):**
• Уверенность: {ai_result.get('confidence', 0):.1%}
• Источник: {ai_result.get('source', 'unknown')}
• Время ответа: {ai_result.get('response_time_ms', 0)}ms
• Персонаж: {ai_result.get('persona_name', 'Неизвестен')}
• Контекст: {'Использован' if ai_result.get('context_used') else 'Не найден'}"""
            response_text += debug_info

        # Создаем клавиатуру
        builder = InlineKeyboardBuilder()

        # Кнопка связи с менеджером
        if lang == "ukr":
            manager_text = "📞 Зв'язатися з менеджером"
            back_text = "⬅️ Головне меню"
        else:
            manager_text = "📞 Связаться с менеджером"
            back_text = "⬅️ Главное меню"

        builder.row(InlineKeyboardButton(text=manager_text, callback_data="contact_manager"))
        builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

        await message.answer(response_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка обработки enhanced AI сообщения: {e}")
        lang = template_manager.get_user_language(user_id)
        if lang == "ukr":
            error_text = (
                "😔 Сталася помилка при обробці повідомлення.\n"
                "Спробуйте ще раз або використовуйте /normal для звичайного режиму."
            )
        else:
            error_text = (
                "😔 Произошла ошибка при обработке сообщения.\n"
                "Попробуйте еще раз или используйте /normal для обычного режима."
            )
        await message.answer(error_text)


@router.message(EnhancedAIStates.comparison_mode)
@handle_exceptions
async def handle_comparison_message(
    message: types.Message, state: FSMContext, template_manager
) -> None:
    """Обрабатывает сообщения в режиме сравнения AI"""

    user_id = message.from_user.id
    user_text = message.text
    lang = template_manager.get_user_language(user_id)

    if not user_text:
        error_text = (
            "Пожалуйста, отправьте текстовое сообщение для сравнения 😊"
            if lang == "rus"
            else "Будь ласка, надішліть текстове повідомлення для порівняння 😊"
        )
        await message.answer(error_text)
        return

    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        # Получаем ответы от обоих AI одновременно
        tasks = [
            ai_service.process_query(user_text, user_id, lang),
            enhanced_ai_service.process_query(user_text, user_id, lang),
        ]

        await asyncio.sleep(1)  # Имитация обдумывания

        results = await asyncio.gather(*tasks, return_exceptions=True)
        normal_result, enhanced_result = results

        # Формируем сравнительный ответ
        if lang == "ukr":
            comparison_text = "🔍 **Порівняння AI-помічників**\n\n"

            # Обычный AI
            comparison_text += "🤖 **Звичайний AI:**\n"
        else:
            comparison_text = "🔍 **Сравнение AI-помощников**\n\n"

            # Обычный AI
            comparison_text += "🤖 **Обычный AI:**\n"

        if isinstance(normal_result, Exception):
            comparison_text += f"❌ Ошибка: {normal_result}\n\n"
        else:
            normal_answer = normal_result.get("answer", "Нет ответа")
            # Умная обрезка: ищем последнее предложение в пределах 600 символов
            if len(normal_answer) > 600:
                truncated = normal_answer[:600]
                last_sentence = truncated.rfind(".")
                if last_sentence > 400:  # Если есть предложение в разумных пределах
                    normal_answer = truncated[: last_sentence + 1] + "..."
                else:
                    normal_answer = truncated + "..."
            comparison_text += f"{normal_answer}\n"
            comparison_text += f"_Уверенность: {normal_result.get('confidence', 0):.1%}_\n\n"

        # Персонализированный AI
        if lang == "ukr":
            comparison_text += "🎭 **Персоналізований AI (Олена):**\n"
        else:
            comparison_text += "🎭 **Персонализированный AI (Олена):**\n"

        if isinstance(enhanced_result, Exception):
            comparison_text += f"❌ Ошибка: {enhanced_result}\n\n"
        else:
            enhanced_answer = enhanced_result.get("answer", "Нет ответа")
            # Умная обрезка: ищем последнее предложение в пределах 600 символов
            if len(enhanced_answer) > 600:
                truncated = enhanced_answer[:600]
                last_sentence = truncated.rfind(".")
                if last_sentence > 400:  # Если есть предложение в разумных пределах
                    enhanced_answer = truncated[: last_sentence + 1] + "..."
                else:
                    enhanced_answer = truncated + "..."
            comparison_text += f"{enhanced_answer}\n"
            comparison_text += f"_Уверенность: {enhanced_result.get('confidence', 0):.1%}_\n\n"

        # Анализ различий
        if lang == "ukr":
            comparison_text += "📋 **Основні відмінності:**\n"
        else:
            comparison_text += "📋 **Основные различия:**\n"

        if not isinstance(enhanced_result, Exception) and not isinstance(normal_result, Exception):
            enhanced_conf = enhanced_result.get("confidence", 0)
            normal_conf = normal_result.get("confidence", 0)
            enhanced_ans = enhanced_result.get("answer", "")
            normal_ans = normal_result.get("answer", "")

            differences_found = False

            if enhanced_conf > normal_conf:
                if lang == "ukr":
                    comparison_text += f"• Персоналізований AI більш впевнений у відповіді ({enhanced_conf:.1%} vs {normal_conf:.1%})\n"
                else:
                    comparison_text += f"• Персонализированный AI более уверен в ответе ({enhanced_conf:.1%} vs {normal_conf:.1%})\n"
                differences_found = True

            if len(enhanced_ans) > len(normal_ans) * 1.1:  # Значительно длиннее
                if lang == "ukr":
                    comparison_text += "• Персоналізована відповідь більш детальна\n"
                else:
                    comparison_text += "• Персонализированный ответ более детальный\n"
                differences_found = True

            if any(
                word in enhanced_ans.lower()
                for word in [
                    "олена",
                    "досвід",
                    "опыт",
                    "пам'ятаю",
                    "помню",
                    "з повагою",
                    "с уважением",
                ]
            ):
                if lang == "ukr":
                    comparison_text += "• Персоналізована відповідь містить особисті елементи\n"
                else:
                    comparison_text += "• Персонализированный ответ содержит личные элементы\n"
                differences_found = True

            # Проверяем структурные различия
            enhanced_emojis = len(
                [c for c in enhanced_ans if ord(c) > 127]
            )  # примерная оценка эмодзи
            normal_emojis = len([c for c in normal_ans if ord(c) > 127])

            if enhanced_emojis > normal_emojis * 1.5:
                if lang == "ukr":
                    comparison_text += (
                        "• Персоналізована відповідь більш емоційна (більше емодзі)\n"
                    )
                else:
                    comparison_text += (
                        "• Персонализированный ответ более эмоциональный (больше эмодзи)\n"
                    )
                differences_found = True

            if not differences_found:
                if lang == "ukr":
                    comparison_text += "• Відповіді схожі за структурою та змістом\n"
                else:
                    comparison_text += "• Ответы похожи по структуре и содержанию\n"

        if lang == "ukr":
            comparison_text += "\n💡 Спробуйте поставити ще питання для порівняння!"
        else:
            comparison_text += "\n💡 Попробуйте задать еще вопросы для сравнения!"

        # Создаем клавиатуру
        builder = InlineKeyboardBuilder()
        back_text = "⬅️ Головне меню" if lang == "ukr" else "⬅️ Главное меню"
        builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

        await message.answer(
            comparison_text, reply_markup=builder.as_markup(), parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Ошибка сравнения AI: {e}")
        error_text = (
            "❌ Ошибка при сравнении AI. Попробуйте позже."
            if lang == "rus"
            else "❌ Помилка при порівнянні AI. Спробуйте пізніше."
        )
        await message.answer(error_text)


@router.message(Command("normal"))
@handle_exceptions
async def cmd_normal_mode(message: types.Message, state: FSMContext, template_manager) -> None:
    """Возвращает к обычному режиму AI"""

    lang = template_manager.get_user_language(message.from_user.id)

    await state.clear()

    if lang == "ukr":
        text = (
            "✅ Переключилися на звичайний режим AI.\n\n"
            "Команди:\n"
            "• /ai - стандартний AI режим\n"
            "• /enhanced - персоналізований AI\n"
            "• /compare - режим порівняння"
        )
    else:
        text = (
            "✅ Переключились на обычный режим AI.\n\n"
            "Команды:\n"
            "• /ai - стандартный AI режим\n"
            "• /enhanced - персонализированный AI\n"
            "• /compare - режим сравнения"
        )

    await message.answer(text)


# Функция для тестирования улучшений
async def test_enhancements_function() -> str:
    """Тестирует улучшения AI и возвращает отчет"""

    test_queries = [
        "Сколько стоят визитки?",
        "Мне нужны футболки для команды",
        "Не знаю что выбрать, помогите",
        "Срочно нужны листовки на завтра!",
        "Качество печати меня не устраивает",
    ]

    report = "🧪 **Тестирование улучшений AI**\n\n"

    for i, query in enumerate(test_queries, 1):
        report += f"❓ **Вопрос {i}:** {query}\n"

        try:
            # Тестируем обычный AI
            normal_result = await ai_service.process_query(query, 12345, "rus")
            normal_answer = normal_result.get("answer", "Нет ответа")[:100]
            normal_conf = normal_result.get("confidence", 0)

            # Тестируем улучшенный AI
            enhanced_result = await enhanced_ai_service.process_query(query, 12345, "rus")
            enhanced_answer = enhanced_result.get("answer", "Нет ответа")[:100]
            enhanced_conf = enhanced_result.get("confidence", 0)

            report += f"🤖 **Обычный:** {normal_answer}...\n"
            report += f"🎭 **Улучшенный:** {enhanced_answer}...\n"
            report += (
                f"📊 **Уверенность:** обычный {normal_conf:.1%} vs улучшенный {enhanced_conf:.1%}\n"
            )
            report += "─" * 50 + "\n\n"

        except Exception as e:
            report += f"❌ **Ошибка тестирования:** {e}\n"
            report += "─" * 50 + "\n\n"

    report += "✅ **Тестирование завершено!**"
    return report


@router.message(Command("test_enhanced"))
@handle_exceptions
async def cmd_test_enhanced(message: types.Message, template_manager) -> None:
    """Команда для тестирования улучшений (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    await message.answer("🧪 Запускаю тестирование улучшений AI...")

    try:
        report = await test_enhancements_function()

        # Разбиваем длинный отчет на части
        if len(report) > 4000:
            parts = [report[i : i + 4000] for i in range(0, len(report), 4000)]
            for i, part in enumerate(parts, 1):
                await message.answer(
                    f"**Часть {i}/{len(parts)}:**\n\n{part}", parse_mode="Markdown"
                )
        else:
            await message.answer(report, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка тестирования улучшений: {e}")
        await message.answer(f"❌ Ошибка тестирования: {e}")


# Глобальная переменная для template_manager
_template_manager = None


# Функция для интеграции с основным диспетчером
def setup_enhanced_ai_handlers(dp, template_manager):
    """Подключает обработчики улучшенного AI к диспетчеру"""
    global _template_manager
    _template_manager = template_manager

    # Переопределяем обработчики с template_manager
    @dp.message(Command("enhanced"))
    async def cmd_enhanced_mode_wrapper(message, state):
        await cmd_enhanced_mode(message, state, _template_manager)

    @dp.message(Command("compare"))
    async def cmd_compare_mode_wrapper(message, state):
        await cmd_compare_mode(message, state, _template_manager)

    @dp.message(Command("enhanced_stats"))
    async def cmd_enhanced_stats_wrapper(message):
        await cmd_enhanced_stats(message, _template_manager)

    @dp.message(Command("normal"))
    async def cmd_normal_mode_wrapper(message, state):
        await cmd_normal_mode(message, state, _template_manager)

    @dp.message(Command("test_enhanced"))
    async def cmd_test_enhanced_wrapper(message):
        await cmd_test_enhanced(message, _template_manager)

    @dp.message(StateFilter(EnhancedAIStates.enhanced_ai_mode))
    async def handle_enhanced_ai_message_wrapper(message, state):
        await handle_enhanced_ai_message(message, state, _template_manager)

    @dp.message(StateFilter(EnhancedAIStates.comparison_mode))
    async def handle_comparison_message_wrapper(message, state):
        await handle_comparison_message(message, state, _template_manager)

    logger.info("Enhanced AI handlers подключены к диспетчеру")
