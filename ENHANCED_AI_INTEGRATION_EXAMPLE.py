"""
Пример интеграции улучшенного AI сервиса с основным ботом
Показывает, как подключить персонализированные ответы "Олены"
"""

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Optional
import asyncio
import logging

# Импорты улучшенного AI
from src.ai.enhanced_ai_service import enhanced_ai_service
from src.ai.service import ai_service  # Оригинальный сервис для сравнения
from config import Config

logger = logging.getLogger(__name__)
router = Router()


class EnhancedBotStates(StatesGroup):
    """Состояния для работы с улучшенным AI"""

    enhanced_ai_mode = State()
    comparison_mode = State()


@router.message(Command("enhanced"))
async def cmd_enhanced_mode(message: types.Message, state: FSMContext):
    """Включает режим персонализированного AI"""

    user_id = message.from_user.id

    # Проверяем доступность улучшенного AI
    if not enhanced_ai_service.is_available():
        await message.answer(
            "😔 Персонализированный AI сейчас недоступен.\n"
            "Используйте /ai для стандартного режима."
        )
        return

    # Получаем информацию о сервисе
    service_info = enhanced_ai_service.get_service_info()

    welcome_text = f"""🎭 **Добро пожаловать к {service_info['persona_name']}!**

Теперь вы общаетесь с нашим персонализированным AI-помощником.

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
    await state.set_state(EnhancedBotStates.enhanced_ai_mode)


@router.message(Command("compare"))
async def cmd_compare_mode(message: types.Message, state: FSMContext):
    """Режим сравнения обычного и улучшенного AI"""

    await message.answer(
        "🔍 **Режим сравнения AI**\n\n"
        "Отправьте вопрос, и я покажу ответы от обычного и персонализированного AI.\n\n"
        "Это поможет увидеть разницу в подходах к ответам.\n\n"
        "Команда /normal для выхода из режима сравнения.",
        parse_mode="Markdown",
    )
    await state.set_state(EnhancedBotStates.comparison_mode)


@router.message(Command("enhanced_stats"))
async def cmd_enhanced_stats(message: types.Message):
    """Показывает статистику персонализации"""

    user_id = message.from_user.id

    try:
        # Получаем статистику пользователя из базы данных
        from src.managers.models import unified_db

        stats = unified_db.get_user_stats_summary(user_id)

        if not stats or stats["total_messages"] == 0:
            await message.answer(
                "📊 **Статистика персонализации**\n\n"
                "У вас пока нет истории общения.\n"
                "Задайте несколько вопросов, и я смогу лучше адаптироваться под ваши потребности! 😊"
            )
            return

        stats_text = f"""📊 **Ваша статистика персонализации**

👤 **Общая активность:**
• Всего сообщений: {stats['total_messages']}
• Ваших вопросов: {stats['user_messages']}
• Получено ответов: {stats['assistant_messages']}
• С персональными советами: {stats['upselling_messages']}

🎯 **Персонализация:**
• Любимая тема: {stats['top_category'] or 'Определяется'}
• Первое обращение: {stats['first_message'] or 'Недавно'}

💡 **Как это используется:**
• Олена помнит ваши интересы и может давать более точные советы
• Адаптирует стиль общения под ваши предпочтения
• Предлагает релевантные дополнительные услуги
• Учитывает ваш опыт работы с типографией

🚀 **Чем больше общаетесь, тем точнее становятся ответы!**"""

        await message.answer(stats_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка получения статистики персонализации: {e}")
        await message.answer("❌ Ошибка получения статистики. Попробуйте позже.")


@router.message(EnhancedBotStates.enhanced_ai_mode)
async def handle_enhanced_ai_message(message: types.Message, state: FSMContext):
    """Обрабатывает сообщения в режиме персонализированного AI"""

    user_id = message.from_user.id
    user_text = message.text

    if not user_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение 😊")
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
        if user_id in getattr(Config, "ADMIN_USER_IDS", []):
            debug_info = f"""

🔧 **Debug info (только для админа):**
• Уверенность: {ai_result['confidence']:.1%}
• Источник: {ai_result['source']}
• Время ответа: {ai_result.get('response_time_ms', 0)}ms
• Персонаж: {ai_result.get('persona_name', 'Неизвестен')}
• Контекст: {'Использован' if ai_result.get('context_used') else 'Не найден'}"""
            response_text += debug_info

        await message.answer(response_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка обработки enhanced AI сообщения: {e}")
        await message.answer(
            "😔 Произошла ошибка при обработке сообщения.\n"
            "Попробуйте еще раз или используйте /normal для обычного режима."
        )


@router.message(EnhancedBotStates.comparison_mode)
async def handle_comparison_message(message: types.Message, state: FSMContext):
    """Обрабатывает сообщения в режиме сравнения AI"""

    user_id = message.from_user.id
    user_text = message.text

    if not user_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение для сравнения 😊")
        return

    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        lang = detect_user_language(message)

        # Получаем ответы от обоих AI одновременно
        tasks = [
            ai_service.process_query(user_text, user_id, lang),
            enhanced_ai_service.process_query(user_text, user_id, lang),
        ]

        await asyncio.sleep(1)  # Имитация обдумывания

        results = await asyncio.gather(*tasks, return_exceptions=True)
        normal_result, enhanced_result = results

        # Формируем сравнительный ответ
        comparison_text = "🔍 **Сравнение AI-помощников**\n\n"

        # Обычный AI
        comparison_text += "🤖 **Обычный AI:**\n"
        if isinstance(normal_result, Exception):
            comparison_text += f"❌ Ошибка: {normal_result}\n\n"
        else:
            comparison_text += f"{normal_result['answer'][:300]}{'...' if len(normal_result['answer']) > 300 else ''}\n"
            comparison_text += f"_Уверенность: {normal_result['confidence']:.1%}_\n\n"

        # Персонализированный AI
        comparison_text += "🎭 **Персонализированный AI (Олена):**\n"
        if isinstance(enhanced_result, Exception):
            comparison_text += f"❌ Ошибка: {enhanced_result}\n\n"
        else:
            comparison_text += f"{enhanced_result['answer'][:300]}{'...' if len(enhanced_result['answer']) > 300 else ''}\n"
            comparison_text += f"_Уверенность: {enhanced_result['confidence']:.1%}_\n\n"

        # Анализ различий
        comparison_text += "📋 **Основные различия:**\n"
        if not isinstance(enhanced_result, Exception) and not isinstance(normal_result, Exception):
            if enhanced_result["confidence"] > normal_result["confidence"]:
                comparison_text += "• Персонализированный AI более уверен в ответе\n"
            if len(enhanced_result["answer"]) > len(normal_result["answer"]):
                comparison_text += "• Персонализированный ответ более детальный\n"
            if any(
                word in enhanced_result["answer"].lower()
                for word in ["олена", "досвід", "пам'ятаю"]
            ):
                comparison_text += "• Персонализированный ответ содержит личные элементы\n"

        comparison_text += "\n💡 Попробуйте задать еще вопросы для сравнения!"

        await message.answer(comparison_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка сравнения AI: {e}")
        await message.answer("❌ Ошибка при сравнении AI. Попробуйте позже.")


@router.message(Command("normal"))
async def cmd_normal_mode(message: types.Message, state: FSMContext):
    """Возвращает к обычному режиму AI"""

    await state.clear()
    await message.answer(
        "✅ Переключились на обычный режим AI.\n\n"
        "Команды:\n"
        "• /ai - стандартный AI режим\n"
        "• /enhanced - персонализированный AI\n"
        "• /compare - режим сравнения"
    )


def detect_user_language(message: types.Message) -> str:
    """Определяет язык пользователя"""
    # Простая логика определения языка
    text = message.text.lower()

    ukrainian_words = ["що", "як", "де", "коли", "чому", "скільки", "візитки", "ціна"]
    russian_words = ["что", "как", "где", "когда", "почему", "сколько", "визитки", "цена"]

    ukr_count = sum(1 for word in ukrainian_words if word in text)
    rus_count = sum(1 for word in russian_words if word in text)

    return "ukr" if ukr_count >= rus_count else "rus"


# Функция для интеграции с основным диспетчером
def setup_enhanced_ai_handlers(dp: Dispatcher):
    """Подключает обработчики улучшенного AI к диспетчеру"""
    dp.include_router(router)
    logger.info("Enhanced AI handlers подключены к диспетчеру")


# Пример использования в main.py:
"""
from ENHANCED_AI_INTEGRATION_EXAMPLE import setup_enhanced_ai_handlers

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Подключаем обычные обработчики
    dp.include_router(main_router)

    # Подключаем улучшенные AI обработчики
    setup_enhanced_ai_handlers(dp)

    await dp.start_polling(bot)
"""


# Функция тестирования улучшений
async def test_enhancements():
    """Тестирует улучшения AI"""

    test_queries = [
        "Сколько стоят визитки?",
        "Мне нужны футболки для команды",
        "Не знаю что выбрать, помогите",
        "Срочно нужны листовки на завтра!",
        "Качество печати меня не устраивает",
    ]

    print("🧪 Тестирование улучшений AI...\n")

    for query in test_queries:
        print(f"❓ Вопрос: {query}")

        try:
            # Тестируем обычный AI
            normal_result = await ai_service.process_query(query, 12345, "rus")
            print(f"🤖 Обычный: {normal_result['answer'][:100]}...")

            # Тестируем улучшенный AI
            enhanced_result = await enhanced_ai_service.process_query(query, 12345, "rus")
            print(f"🎭 Улучшенный: {enhanced_result['answer'][:100]}...")

            print(
                f"📊 Уверенность: обычный {normal_result['confidence']:.1%} vs улучшенный {enhanced_result['confidence']:.1%}"
            )
            print("-" * 80)

        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
            print("-" * 80)

    print("✅ Тестирование завершено!")


if __name__ == "__main__":
    # Запуск тестирования
    asyncio.run(test_enhancements())
