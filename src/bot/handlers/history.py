"""
Обработчики для просмотра истории диалогов пользователей
Интеграция с объединенной SQLite базой данных
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from typing import List, Dict

from src.managers.models import unified_db, ConversationMessage, MessageType
import logging

logger = logging.getLogger(__name__)
router = Router()


class HistoryStates(StatesGroup):
    browsing = State()
    filtering = State()
    searching = State()


@router.message(Command("history"))
async def cmd_history(message: types.Message, state: FSMContext):
    """Команда просмотра истории запросов"""

    user_id = message.from_user.id

    try:
        # Получаем последние сообщения пользователя
        recent_messages = unified_db.get_user_history(user_id, limit=10)

        if not recent_messages:
            await message.answer("📭 У вас пока нет истории диалогов")
            return

        # Формируем сообщение с историей
        history_text = await _format_history_message(recent_messages, user_id)
        keyboard = _create_history_keyboard()

        await message.answer(history_text, reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(HistoryStates.browsing)

    except Exception as e:
        logger.error(f"Ошибка получения истории для пользователя {user_id}: {e}")
        await message.answer("❌ Ошибка при загрузке истории. Попробуйте позже.")


async def _format_history_message(messages: List[ConversationMessage], user_id: int) -> str:
    """Форматирует сообщение с историей"""

    # Получаем статистику пользователя
    stats = unified_db.get_user_stats_summary(user_id)

    text = f"📋 **Ваша история диалогов**\n\n"
    text += f"📊 **Статистика:**\n"
    text += f"• Всего сообщений: {stats['total_messages']}\n"
    text += f"• Ваших вопросов: {stats['user_messages']}\n"
    text += f"• Получено ответов: {stats['assistant_messages']}\n"
    text += f"• Предложений с upselling: {stats['upselling_messages']}\n\n"

    text += f"📝 **Последние сообщения:**\n\n"

    # Группируем сообщения по парам (вопрос-ответ)
    grouped_messages = _group_messages_by_pairs(messages)

    for i, group in enumerate(grouped_messages[:5], 1):
        user_msg = group.get("user")
        assistant_msg = group.get("assistant")

        if user_msg:
            date_str = user_msg.timestamp.strftime("%d.%m %H:%M")
            query_preview = _truncate_text(user_msg.content, 50)

            text += f"**{i}. {date_str}**\n"
            text += f"❓ _{query_preview}_\n"

            if assistant_msg:
                response_preview = _truncate_text(assistant_msg.content, 60)
                text += f"✅ {response_preview}\n"

                # Показываем дополнительную информацию
                if assistant_msg.has_upselling:
                    text += "💰 _С предложениями_\n"
                if assistant_msg.is_auto_response:
                    text += "🤖 _Автоответ_\n"
                if assistant_msg.manager_id:
                    text += f"👤 _Менеджер ID: {assistant_msg.manager_id}_\n"
            else:
                text += "❌ Без ответа\n"

            text += "\n"

    return text


def _group_messages_by_pairs(messages: List[ConversationMessage]) -> List[Dict]:
    """Группирует сообщения по парам вопрос-ответ"""
    grouped = []
    current_group = {}

    for msg in reversed(messages):  # Обрабатываем от старых к новым
        if msg.message_type == MessageType.USER:
            # Сохраняем предыдущую группу если есть
            if current_group:
                grouped.append(current_group.copy())
            current_group = {"user": msg}
        elif msg.message_type == MessageType.ASSISTANT and current_group:
            current_group["assistant"] = msg

    # Добавляем последнюю группу
    if current_group:
        grouped.append(current_group)

    return list(reversed(grouped))  # Возвращаем в обратном порядке (новые первыми)


def _truncate_text(text: str, max_length: int) -> str:
    """Обрезает текст до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def _create_history_keyboard() -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для истории"""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🔍 Фильтры", callback_data="history:filters"),
                types.InlineKeyboardButton(text="🔎 Поиск", callback_data="history:search"),
            ],
            [
                types.InlineKeyboardButton(
                    text="📊 Подробная статистика", callback_data="history:detailed_stats"
                ),
                types.InlineKeyboardButton(text="📄 Больше записей", callback_data="history:more"),
            ],
            [types.InlineKeyboardButton(text="🗑️ Очистить историю", callback_data="history:clear")],
        ]
    )


@router.callback_query(F.data.startswith("history:"))
async def process_history_action(callback: types.CallbackQuery, state: FSMContext):
    """Обработка действий с историей"""

    action = callback.data.split(":")[1]
    user_id = callback.from_user.id

    try:
        if action == "filters":
            await show_history_filters(callback, state)
        elif action == "search":
            await start_history_search(callback, state)
        elif action == "detailed_stats":
            await show_detailed_user_stats(callback, user_id)
        elif action == "more":
            await show_more_history(callback, user_id)
        elif action == "clear":
            await confirm_clear_history(callback, state)
        elif action == "back":
            await cmd_history(callback.message, state)

    except Exception as e:
        logger.error(f"Ошибка обработки действия {action}: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def show_history_filters(callback: types.CallbackQuery, state: FSMContext):
    """Показывает фильтры для истории"""

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="📅 За сегодня", callback_data="filter:today"),
                types.InlineKeyboardButton(text="📅 За неделю", callback_data="filter:week"),
            ],
            [
                types.InlineKeyboardButton(text="📅 За месяц", callback_data="filter:month"),
                types.InlineKeyboardButton(text="📅 За все время", callback_data="filter:all"),
            ],
            [
                types.InlineKeyboardButton(
                    text="❓ Только мои вопросы", callback_data="filter:user_messages"
                ),
                types.InlineKeyboardButton(
                    text="✅ Только ответы", callback_data="filter:assistant_messages"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="💰 С предложениями", callback_data="filter:upselling"
                ),
                types.InlineKeyboardButton(
                    text="🤖 Автоответы", callback_data="filter:auto_responses"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="👤 Ответы менеджеров", callback_data="filter:manager_responses"
                ),
                types.InlineKeyboardButton(text="📁 С файлами", callback_data="filter:with_files"),
            ],
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="history:back")],
        ]
    )

    await callback.message.edit_text(
        "🔍 **Выберите фильтр для истории:**\n\n"
        "Вы можете посмотреть сообщения за определенный период или по типу контента.",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("filter:"))
async def apply_history_filter(callback: types.CallbackQuery, state: FSMContext):
    """Применяет фильтр к истории"""

    filter_type = callback.data.split(":")[1]
    user_id = callback.from_user.id

    try:
        # Получаем отфильтрованные сообщения
        filtered_messages = await _get_filtered_messages(user_id, filter_type)

        if not filtered_messages:
            await callback.answer("📭 По выбранному фильтру ничего не найдено", show_alert=True)
            return

        # Показываем отфильтрованные результаты
        await show_filtered_history(callback, filtered_messages, filter_type)

    except Exception as e:
        logger.error(f"Ошибка применения фильтра {filter_type}: {e}")
        await callback.answer("❌ Ошибка фильтрации", show_alert=True)


async def _get_filtered_messages(user_id: int, filter_type: str) -> List[ConversationMessage]:
    """Получает отфильтрованные сообщения"""

    if filter_type == "today":
        return unified_db.get_user_history_by_date(user_id, days=1)
    elif filter_type == "week":
        return unified_db.get_user_history_by_date(user_id, days=7)
    elif filter_type == "month":
        return unified_db.get_user_history_by_date(user_id, days=30)
    elif filter_type == "all":
        return unified_db.get_user_history(user_id, limit=100)
    elif filter_type == "user_messages":
        return unified_db.get_user_history_by_type(user_id, MessageType.USER)
    elif filter_type == "assistant_messages":
        return unified_db.get_user_history_by_type(user_id, MessageType.ASSISTANT)
    elif filter_type == "upselling":
        return unified_db.get_user_history_with_upselling(user_id)
    elif filter_type == "auto_responses":
        return _get_auto_responses(user_id)
    elif filter_type == "manager_responses":
        return _get_manager_responses(user_id)
    elif filter_type == "with_files":
        return _get_messages_with_files(user_id)
    else:
        return []


def _get_auto_responses(user_id: int) -> List[ConversationMessage]:
    """Получает автоответы"""
    with unified_db._get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM conversation_history
            WHERE user_id = ? AND is_auto_response = TRUE
            ORDER BY timestamp DESC
        """,
            (user_id,),
        ).fetchall()

        return [unified_db._row_to_message(row) for row in rows]


def _get_manager_responses(user_id: int) -> List[ConversationMessage]:
    """Получает ответы менеджеров"""
    with unified_db._get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM conversation_history
            WHERE user_id = ? AND manager_id IS NOT NULL
            ORDER BY timestamp DESC
        """,
            (user_id,),
        ).fetchall()

        return [unified_db._row_to_message(row) for row in rows]


def _get_messages_with_files(user_id: int) -> List[ConversationMessage]:
    """Получает сообщения с файлами"""
    with unified_db._get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM conversation_history
            WHERE user_id = ? AND file_info IS NOT NULL
            ORDER BY timestamp DESC
        """,
            (user_id,),
        ).fetchall()

        return [unified_db._row_to_message(row) for row in rows]


async def show_filtered_history(
    callback: types.CallbackQuery, messages: List[ConversationMessage], filter_type: str
):
    """Показывает отфильтрованную историю"""

    filter_names = {
        "today": "за сегодня",
        "week": "за неделю",
        "month": "за месяц",
        "all": "за все время",
        "user_messages": "ваши вопросы",
        "assistant_messages": "полученные ответы",
        "upselling": "с предложениями",
        "auto_responses": "автоответы",
        "manager_responses": "ответы менеджеров",
        "with_files": "с файлами",
    }

    filter_name = filter_names.get(filter_type, filter_type)

    text = f"🔍 **Фильтр: {filter_name}**\n"
    text += f"📊 Найдено сообщений: {len(messages)}\n\n"

    # Показываем первые 8 сообщений
    for i, msg in enumerate(messages[:8], 1):
        date_str = msg.timestamp.strftime("%d.%m %H:%M")
        content_preview = _truncate_text(msg.content, 40)

        msg_type_emoji = {
            MessageType.USER: "❓",
            MessageType.ASSISTANT: "✅",
            MessageType.SYSTEM: "ℹ️",
        }

        emoji = msg_type_emoji.get(msg.message_type, "💬")
        text += f"{emoji} **{date_str}** - _{content_preview}_\n"

        # Дополнительная информация
        details = []
        if msg.has_upselling:
            details.append("💰")
        if msg.is_auto_response:
            details.append("🤖")
        if msg.manager_id:
            details.append(f"👤{msg.manager_id}")
        if msg.file_info:
            details.append("📁")

        if details:
            text += f"   {' '.join(details)}\n"

        text += "\n"

    if len(messages) > 8:
        text += f"... и еще {len(messages) - 8} сообщений\n"

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🔍 Другие фильтры", callback_data="history:filters"
                ),
                types.InlineKeyboardButton(
                    text="📄 Все записи", callback_data=f"show_all:{filter_type}"
                ),
            ],
            [types.InlineKeyboardButton(text="🔙 К истории", callback_data="history:back")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def start_history_search(callback: types.CallbackQuery, state: FSMContext):
    """Начинает поиск по истории"""

    await callback.message.edit_text(
        "🔎 **Поиск по истории диалогов**\n\n"
        "Отправьте слово или фразу для поиска в ваших сообщениях.\n"
        'Например: _"визитки"_, _"цена"_, _"макет"_\n\n'
        "Для отмены отправьте /cancel",
        parse_mode="Markdown",
    )

    await state.set_state(HistoryStates.searching)


@router.message(HistoryStates.searching)
async def process_history_search(message: types.Message, state: FSMContext):
    """Обрабатывает поиск по истории"""

    search_text = message.text.strip()
    user_id = message.from_user.id

    if search_text.lower() in ["/cancel", "отмена"]:
        await message.answer("🔍 Поиск отменен")
        await state.clear()
        return

    try:
        # Выполняем поиск
        found_messages = unified_db.search_user_history(user_id, search_text, limit=20)

        if not found_messages:
            await message.answer(
                f'🔍 По запросу "_{search_text}_" ничего не найдено.\n\n'
                f"Попробуйте другие ключевые слова или используйте фильтры.",
                parse_mode="Markdown",
            )
            await state.clear()
            return

        # Формируем результаты поиска
        text = f'🔍 **Результаты поиска: "_{search_text}_"**\n'
        text += f"📊 Найдено: {len(found_messages)} сообщений\n\n"

        for i, msg in enumerate(found_messages[:10], 1):
            date_str = msg.timestamp.strftime("%d.%m %H:%M")

            # Выделяем найденное слово в тексте
            highlighted_content = _highlight_search_term(msg.content, search_text)
            content_preview = _truncate_text(highlighted_content, 60)

            msg_type = "❓" if msg.message_type == MessageType.USER else "✅"
            text += f"{msg_type} **{date_str}**\n{content_preview}\n\n"

        if len(found_messages) > 10:
            text += f"... и еще {len(found_messages) - 10} результатов\n"

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🔎 Новый поиск", callback_data="history:search"
                    ),
                    types.InlineKeyboardButton(text="🔙 К истории", callback_data="history:back"),
                ]
            ]
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка поиска по истории: {e}")
        await message.answer("❌ Ошибка поиска. Попробуйте еще раз.")
        await state.clear()


def _highlight_search_term(text: str, search_term: str) -> str:
    """Выделяет найденный термин в тексте"""
    # Простое выделение курсивом
    return text.replace(search_term, f"*{search_term}*")


async def show_detailed_user_stats(callback: types.CallbackQuery, user_id: int):
    """Показывает подробную статистику пользователя"""

    try:
        stats = unified_db.get_user_stats_summary(user_id)

        text = f"📊 **Детальная статистика**\n\n"

        text += f"📈 **Общие показатели:**\n"
        text += f"• Всего сообщений: {stats['total_messages']}\n"
        text += f"• Ваших вопросов: {stats['user_messages']}\n"
        text += f"• Получено ответов: {stats['assistant_messages']}\n"
        text += f"• Автоответов: {stats['auto_responses']}\n"
        text += f"• С предложениями: {stats['upselling_messages']}\n\n"

        # Временная статистика
        if stats["first_message"]:
            first_date = datetime.fromisoformat(stats["first_message"]).strftime("%d.%m.%Y %H:%M")
            text += f"📅 **Временные рамки:**\n"
            text += f"• Первое сообщение: {first_date}\n"

            if stats["last_message"]:
                last_date = datetime.fromisoformat(stats["last_message"]).strftime("%d.%m.%Y %H:%M")
                text += f"• Последнее сообщение: {last_date}\n"

            # Вычисляем период активности
            first_dt = datetime.fromisoformat(stats["first_message"])
            last_dt = (
                datetime.fromisoformat(stats["last_message"])
                if stats["last_message"]
                else datetime.now()
            )
            period_days = (last_dt - first_dt).days
            text += f"• Период активности: {period_days} дней\n\n"

        text += f"🎯 **Предпочтения:**\n"
        text += f"• Любимая категория: {stats['top_category']}\n"

        if stats["avg_response_time_ms"] > 0:
            text += f"• Среднее время ответа: {stats['avg_response_time_ms']} мс\n"

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 К истории", callback_data="history:back")]
            ]
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка получения детальной статистики: {e}")
        await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)


async def show_more_history(callback: types.CallbackQuery, user_id: int):
    """Показывает больше записей истории"""

    try:
        # Получаем больше сообщений (следующие 20)
        more_messages = unified_db.get_user_history(user_id, limit=20, offset=10)

        if not more_messages:
            await callback.answer("📭 Больше записей нет", show_alert=True)
            return

        # Формируем расширенную историю
        text = f"📋 **Расширенная история** (записи 11-30)\n\n"

        grouped_messages = _group_messages_by_pairs(more_messages)

        for i, group in enumerate(grouped_messages, 11):
            user_msg = group.get("user")
            assistant_msg = group.get("assistant")

            if user_msg:
                date_str = user_msg.timestamp.strftime("%d.%m %H:%M")
                query_preview = _truncate_text(user_msg.content, 45)

                text += f"**{i}. {date_str}**\n❓ _{query_preview}_\n"

                if assistant_msg:
                    response_preview = _truncate_text(assistant_msg.content, 50)
                    text += f"✅ {response_preview}\n"
                else:
                    text += "❌ Без ответа\n"

                text += "\n"

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🔙 К основной истории", callback_data="history:back"
                    )
                ]
            ]
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка загрузки расширенной истории: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)


async def confirm_clear_history(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение очистки истории"""

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="❌ Да, очистить", callback_data="history:clear_confirmed"
                ),
                types.InlineKeyboardButton(text="✅ Отмена", callback_data="history:back"),
            ]
        ]
    )

    await callback.message.edit_text(
        "⚠️ **Подтверждение очистки**\n\n"
        "Вы действительно хотите удалить всю историю диалогов?\n"
        "Это действие нельзя отменить.\n\n"
        "🔒 История используется для улучшения обслуживания и будет удалена безвозвратно.",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "history:clear_confirmed")
async def clear_user_history(callback: types.CallbackQuery):
    """Очищает историю пользователя"""

    user_id = callback.from_user.id

    try:
        # Удаляем историю пользователя
        with unified_db._get_connection() as conn:
            deleted_count = conn.execute(
                """
                DELETE FROM conversation_history WHERE user_id = ?
            """,
                (user_id,),
            ).rowcount

            # Удаляем статистику
            conn.execute("DELETE FROM user_stats WHERE user_id = ?", (user_id,))
            conn.commit()

        await callback.message.edit_text(
            f"✅ **История очищена**\n\n"
            f"Удалено {deleted_count} записей из вашей истории диалогов.\n"
            f"Новые сообщения будут сохраняться как обычно."
        )

        logger.info(f"Очищена история пользователя {user_id}: {deleted_count} записей")

    except Exception as e:
        logger.error(f"Ошибка очистки истории пользователя {user_id}: {e}")
        await callback.message.edit_text(
            "❌ **Ошибка очистки**\n\n"
            "Не удалось очистить историю. Попробуйте позже или обратитесь к администратору."
        )
