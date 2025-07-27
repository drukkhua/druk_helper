"""
Админская панель для управления менеджерами
Интегрирована с объединенной SQLite базой данных
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, time
from typing import List, Dict, Optional
import logging

from src.managers.models import unified_db, Manager, ManagerStatus
from config import Config

logger = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_manager_name = State()
    waiting_manager_username = State()
    waiting_work_hours = State()
    editing_manager = State()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in getattr(Config, "ADMIN_USER_IDS", [])


@router.message(Command("admin_managers"))
async def cmd_admin_managers(message: types.Message, state: FSMContext):
    """Главная команда админки менеджеров"""

    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа к админ-панели")
        return

    try:
        # Получаем статистику менеджеров
        active_managers = unified_db.get_active_managers()
        all_managers_count = len(unified_db.get_active_managers()) + len(
            [m for m in unified_db._get_all_managers() if m.status == ManagerStatus.OFFLINE]
        )

        # Статистика базы данных
        db_stats = unified_db.get_database_stats()

        admin_text = f"""🎛️ **Админ-панель менеджеров**

📊 **Статистика системы:**
• Всего менеджеров: {all_managers_count}
• Активных сейчас: {len(active_managers)}
• Активных чатов: {db_stats['active_chats']}
• Всего сообщений: {db_stats['total_messages']}
• Уникальных пользователей: {db_stats['unique_users']}

👥 **Активные менеджеры:**"""

        for manager in active_managers[:5]:  # Показываем первых 5
            status_emoji = {
                ManagerStatus.ACTIVE: "🟢",
                ManagerStatus.BUSY: "🟡",
                ManagerStatus.OFFLINE: "🔴",
                ManagerStatus.VACATION: "🏖️",
            }

            emoji = status_emoji.get(manager.status, "❓")
            admin_text += f"\n{emoji} {manager.name} ({manager.active_chats} чатов)"

        if len(active_managers) > 5:
            admin_text += f"\n... и еще {len(active_managers) - 5} менеджеров"

        keyboard = create_admin_main_keyboard()
        await message.answer(admin_text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка отображения админ-панели: {e}")
        await message.answer("❌ Ошибка загрузки админ-панели")


def create_admin_main_keyboard() -> types.InlineKeyboardMarkup:
    """Создает главную клавиатуру админки"""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="👥 Список менеджеров", callback_data="admin:managers_list"
                ),
                types.InlineKeyboardButton(
                    text="➕ Добавить менеджера", callback_data="admin:add_manager"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="📊 Детальная статистика", callback_data="admin:detailed_stats"
                ),
                types.InlineKeyboardButton(
                    text="🔄 Управление статусами", callback_data="admin:manage_statuses"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="⚙️ Настройки системы", callback_data="admin:system_settings"
                ),
                types.InlineKeyboardButton(
                    text="📋 Активные чаты", callback_data="admin:active_chats"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="🗂️ База данных", callback_data="admin:database_info"
                )
            ],
        ]
    )


@router.callback_query(F.data.startswith("admin:"))
async def process_admin_action(callback: types.CallbackQuery, state: FSMContext):
    """Обработка действий админки"""

    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав доступа", show_alert=True)
        return

    action = callback.data.split(":")[1]

    try:
        if action == "managers_list":
            await show_managers_list(callback)
        elif action == "add_manager":
            await start_add_manager(callback, state)
        elif action == "detailed_stats":
            await show_detailed_stats(callback)
        elif action == "manage_statuses":
            await show_status_management(callback)
        elif action == "system_settings":
            await show_system_settings(callback)
        elif action == "active_chats":
            await show_active_chats(callback)
        elif action == "database_info":
            await show_database_info(callback)
        elif action == "back":
            await cmd_admin_managers(callback.message, state)

    except Exception as e:
        logger.error(f"Ошибка обработки админ-действия {action}: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def show_managers_list(callback: types.CallbackQuery):
    """Показывает список всех менеджеров"""

    try:
        all_managers = unified_db._get_all_managers()

        if not all_managers:
            await callback.message.edit_text(
                "📭 **Менеджеры не найдены**\n\nДобавьте первого менеджера для начала работы.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text="➕ Добавить менеджера", callback_data="admin:add_manager"
                            )
                        ],
                        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back")],
                    ]
                ),
                parse_mode="Markdown",
            )
            return

        text = "👥 **Список всех менеджеров**\n\n"

        for i, manager in enumerate(all_managers, 1):
            status_emoji = {
                ManagerStatus.ACTIVE: "🟢",
                ManagerStatus.BUSY: "🟡",
                ManagerStatus.OFFLINE: "🔴",
                ManagerStatus.VACATION: "🏖️",
            }

            emoji = status_emoji.get(manager.status, "❓")
            username_text = f"@{manager.username}" if manager.username else "Без username"

            text += f"""**{i}. {manager.name}** {emoji}
• ID: `{manager.telegram_id}`
• Username: {username_text}
• Статус: {manager.status.value}
• Активных чатов: {manager.active_chats}/{manager.max_active_chats}
• Всего клиентов: {manager.total_clients}
• Уведомления: {'✅' if manager.notifications_enabled else '❌'}

"""

        # Создаем клавиатуру с менеджерами для редактирования
        keyboard_buttons = []
        for manager in all_managers[:10]:  # Показываем первых 10
            keyboard_buttons.append(
                [
                    types.InlineKeyboardButton(
                        text=f"✏️ {manager.name}",
                        callback_data=f"admin:edit_manager:{manager.telegram_id}",
                    )
                ]
            )

        keyboard_buttons.append(
            [
                types.InlineKeyboardButton(
                    text="➕ Добавить менеджера", callback_data="admin:add_manager"
                ),
                types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back"),
            ]
        )

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка отображения списка менеджеров: {e}")
        await callback.answer("❌ Ошибка загрузки списка", show_alert=True)


async def start_add_manager(callback: types.CallbackQuery, state: FSMContext):
    """Начинает процесс добавления менеджера"""

    await callback.message.edit_text(
        "➕ **Добавление нового менеджера**\n\n"
        "Отправьте имя нового менеджера:\n"
        "Например: _Иван Петров_\n\n"
        "Для отмены отправьте /cancel",
        parse_mode="Markdown",
    )

    await state.set_state(AdminStates.waiting_manager_name)


@router.message(AdminStates.waiting_manager_name)
async def process_manager_name(message: types.Message, state: FSMContext):
    """Обрабатывает ввод имени менеджера"""

    if not is_admin(message.from_user.id):
        return

    if message.text.lower() in ["/cancel", "отмена"]:
        await message.answer("❌ Добавление менеджера отменено")
        await state.clear()
        return

    manager_name = message.text.strip()

    if len(manager_name) < 2:
        await message.answer("❌ Имя слишком короткое. Попробуйте еще раз:")
        return

    # Сохраняем имя в состоянии
    await state.update_data(manager_name=manager_name)

    await message.answer(
        f"✅ **Имя менеджера:** {manager_name}\n\n"
        f"Теперь отправьте Telegram ID нового менеджера:\n"
        f"Например: _123456789_\n\n"
        f"💡 ID можно получить через @userinfobot\n\n"
        f"Для отмены отправьте /cancel"
    )

    await state.set_state(AdminStates.waiting_manager_username)


@router.message(AdminStates.waiting_manager_username)
async def process_manager_id(message: types.Message, state: FSMContext):
    """Обрабатывает ввод Telegram ID менеджера"""

    if not is_admin(message.from_user.id):
        return

    if message.text.lower() in ["/cancel", "отмена"]:
        await message.answer("❌ Добавление менеджера отменено")
        await state.clear()
        return

    try:
        manager_telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID. Введите числовой ID:")
        return

    # Проверяем, не существует ли уже такой менеджер
    existing_managers = unified_db._get_all_managers()
    if any(m.telegram_id == manager_telegram_id for m in existing_managers):
        await message.answer("❌ Менеджер с таким ID уже существует!")
        return

    # Получаем данные из состояния
    data = await state.get_data()
    manager_name = data.get("manager_name")

    # Создаем нового менеджера
    try:
        new_manager = Manager(
            telegram_id=manager_telegram_id,
            name=manager_name,
            status=ManagerStatus.OFFLINE,
            notifications_enabled=True,
            notification_sound=True,
            max_active_chats=10,
        )

        manager_id = unified_db.add_manager(new_manager)

        await message.answer(
            f"✅ **Менеджер успешно добавлен!**\n\n"
            f"👤 **Имя:** {manager_name}\n"
            f"🆔 **Telegram ID:** `{manager_telegram_id}`\n"
            f"📊 **ID в БД:** {manager_id}\n"
            f"📍 **Статус:** Оффлайн\n\n"
            f"💡 Менеджер может активироваться командой /manager_start",
            parse_mode="Markdown",
        )

        logger.info(
            f"Админ {message.from_user.id} добавил менеджера: {manager_name} ({manager_telegram_id})"
        )

    except Exception as e:
        logger.error(f"Ошибка добавления менеджера: {e}")
        await message.answer("❌ Ошибка при добавлении менеджера. Попробуйте еще раз.")

    await state.clear()


async def show_detailed_stats(callback: types.CallbackQuery):
    """Показывает детальную статистику системы"""

    try:
        db_stats = unified_db.get_database_stats()
        all_managers = unified_db._get_all_managers()

        # Статистика по статусам менеджеров
        status_counts = {}
        for manager in all_managers:
            status = manager.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Статистика активности
        active_today = 0
        total_chats_today = 0

        for manager in all_managers:
            if manager.last_activity and manager.last_activity.date() == datetime.now().date():
                active_today += 1
            total_chats_today += manager.active_chats

        text = f"""📊 **Детальная статистика системы**

🏢 **Общие показатели:**
• Всего менеджеров: {len(all_managers)}
• Активных чатов: {db_stats['active_chats']}
• Всего сообщений: {db_stats['total_messages']}
• Уникальных пользователей: {db_stats['unique_users']}

👥 **Менеджеры по статусам:**"""

        status_emoji = {"active": "🟢", "busy": "🟡", "offline": "🔴", "vacation": "🏖️"}

        for status, count in status_counts.items():
            emoji = status_emoji.get(status, "❓")
            text += f"\n{emoji} {status.title()}: {count}"

        text += f"""

📈 **Активность сегодня:**
• Работавших менеджеров: {active_today}
• Активных чатов сейчас: {total_chats_today}

💾 **База данных:**
• Путь: `{db_stats['database_path']}`"""

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🔄 Обновить", callback_data="admin:detailed_stats"
                    )
                ],
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back")],
            ]
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка отображения детальной статистики: {e}")
        await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)


async def show_active_chats(callback: types.CallbackQuery):
    """Показывает активные чаты"""

    try:
        # Получаем активные чаты
        with unified_db._get_connection() as conn:
            active_chats = conn.execute(
                """
                SELECT ac.*, m.name as manager_name
                FROM active_chats ac
                LEFT JOIN managers m ON ac.manager_telegram_id = m.telegram_id
                WHERE ac.status = 'active'
                ORDER BY ac.started_at DESC
                LIMIT 20
            """
            ).fetchall()

        if not active_chats:
            await callback.message.edit_text(
                "📭 **Активных чатов нет**\n\nВсе менеджеры свободны.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back")]
                    ]
                ),
                parse_mode="Markdown",
            )
            return

        text = f"📋 **Активные чаты** ({len(active_chats)})\n\n"

        for i, chat in enumerate(active_chats, 1):
            start_time = datetime.fromisoformat(chat["started_at"]).strftime("%d.%m %H:%M")
            duration = datetime.now() - datetime.fromisoformat(chat["started_at"])
            duration_mins = int(duration.total_seconds() / 60)

            text += f"""**{i}. {chat['client_name'] or 'Без имени'}**
• Клиент ID: `{chat['client_telegram_id']}`
• Менеджер: {chat['manager_name'] or 'Неизвестен'}
• Начат: {start_time} ({duration_mins} мин назад)
• Запрос: _{chat['initial_query'][:50] if chat['initial_query'] else 'Не указан'}_

"""

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:active_chats")],
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back")],
            ]
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка отображения активных чатов: {e}")
        await callback.answer("❌ Ошибка загрузки чатов", show_alert=True)


async def show_database_info(callback: types.CallbackQuery):
    """Показывает информацию о базе данных"""

    try:
        db_stats = unified_db.get_database_stats()

        # Получаем размер файла базы данных
        db_size = unified_db.db_path.stat().st_size if unified_db.db_path.exists() else 0
        db_size_mb = round(db_size / (1024 * 1024), 2)

        # Статистика таблиц
        with unified_db._get_connection() as conn:
            tables_info = conn.execute(
                """
                SELECT name FROM sqlite_master WHERE type='table'
            """
            ).fetchall()

            table_stats = {}
            for table in tables_info:
                table_name = table["name"]
                if not table_name.startswith("sqlite_"):
                    # Use explicit table queries to prevent SQL injection
                    if table_name == "user_queries":
                        count = conn.execute(
                            "SELECT COUNT(*) as count FROM user_queries"
                        ).fetchone()
                    elif table_name == "conversation_history":
                        count = conn.execute(
                            "SELECT COUNT(*) as count FROM conversation_history"
                        ).fetchone()
                    elif table_name == "user_states":
                        count = conn.execute("SELECT COUNT(*) as count FROM user_states").fetchone()
                    elif table_name == "system_stats":
                        count = conn.execute(
                            "SELECT COUNT(*) as count FROM system_stats"
                        ).fetchone()
                    else:
                        count = {"count": 0}
                    table_stats[table_name] = count["count"]

        text = f"""🗂️ **Информация о базе данных**

📊 **Общая информация:**
• Путь: `{db_stats['database_path']}`
• Размер файла: {db_size_mb} МБ
• Всего таблиц: {len(table_stats)}

📋 **Записей в таблицах:**"""

        for table_name, count in table_stats.items():
            text += f"\n• {table_name}: {count:,}"

        text += f"""

🔗 **Статистика:**
• Менеджеров: {db_stats['managers_total']}
• Активных чатов: {db_stats['active_chats']}
• Сообщений: {db_stats['total_messages']:,}
• Пользователей: {db_stats['unique_users']:,}"""

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🔄 Обновить", callback_data="admin:database_info"
                    ),
                    types.InlineKeyboardButton(
                        text="🗑️ Очистка", callback_data="admin:database_cleanup"
                    ),
                ],
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back")],
            ]
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка отображения информации о БД: {e}")
        await callback.answer("❌ Ошибка загрузки информации", show_alert=True)


# Команды для менеджеров
@router.message(Command("manager_start"))
async def cmd_manager_start(message: types.Message):
    """Команда активации менеджера"""

    user_id = message.from_user.id

    try:
        # Проверяем, есть ли менеджер в базе
        managers = unified_db._get_all_managers()
        manager = next((m for m in managers if m.telegram_id == user_id), None)

        if not manager:
            await message.answer(
                "❌ Вы не зарегистрированы как менеджер.\n\n"
                "Обратитесь к администратору для добавления в систему."
            )
            return

        # Активируем менеджера
        unified_db.update_manager_status(user_id, ManagerStatus.ACTIVE)

        await message.answer(
            f"✅ **{manager.name}, добро пожаловать!**\n\n"
            f"🟢 Статус изменен на: **Активен**\n"
            f"📞 Вы будете получать уведомления о новых клиентах\n\n"
            f"📋 Доступные команды:\n"
            f"• /manager_status - проверить статус\n"
            f"• /manager_busy - пометить как занят\n"
            f"• /manager_break - уйти в перерыв\n"
            f"• /manager_stats - моя статистика",
            parse_mode="Markdown",
        )

        logger.info(f"Менеджер {manager.name} ({user_id}) активирован")

    except Exception as e:
        logger.error(f"Ошибка активации менеджера {user_id}: {e}")
        await message.answer("❌ Ошибка активации. Обратитесь к администратору.")


@router.message(Command("manager_status"))
async def cmd_manager_status(message: types.Message):
    """Показывает статус менеджера"""

    user_id = message.from_user.id

    try:
        stats = unified_db.get_manager_stats(user_id)

        if not stats:
            await message.answer("❌ Вы не зарегистрированы как менеджер")
            return

        status_emoji = {"active": "🟢", "busy": "🟡", "offline": "🔴", "vacation": "🏖️"}

        emoji = status_emoji.get(stats["status"], "❓")

        status_text = f"""👤 **{stats['name']}**

{emoji} **Статус:** {stats['status'].title()}
📊 **Активных чатов:** {stats['active_chats']}
👥 **Всего клиентов:** {stats['total_clients']}

📈 **Сегодня:**
• Новых чатов: {stats['today_chats']}
• Отправлено ответов: {stats['today_messages']}

🕐 **Последняя активность:** {stats['last_activity'] or 'Не определена'}"""

        # Создаем клавиатуру управления статусом
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🟢 Активен", callback_data="manager:set_active"
                    ),
                    types.InlineKeyboardButton(text="🟡 Занят", callback_data="manager:set_busy"),
                ],
                [
                    types.InlineKeyboardButton(
                        text="🔴 Оффлайн", callback_data="manager:set_offline"
                    ),
                    types.InlineKeyboardButton(
                        text="📊 Моя статистика", callback_data="manager:my_stats"
                    ),
                ],
            ]
        )

        await message.answer(status_text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка получения статуса менеджера {user_id}: {e}")
        await message.answer("❌ Ошибка получения статуса")


@router.callback_query(F.data.startswith("manager:set_"))
async def handle_manager_status_change(callback: types.CallbackQuery):
    """Обрабатывает смену статуса менеджера"""

    user_id = callback.from_user.id
    new_status_str = callback.data.split("_")[1]

    status_map = {
        "active": ManagerStatus.ACTIVE,
        "busy": ManagerStatus.BUSY,
        "offline": ManagerStatus.OFFLINE,
    }

    new_status = status_map.get(new_status_str)
    if not new_status:
        await callback.answer("❌ Неизвестный статус", show_alert=True)
        return

    try:
        unified_db.update_manager_status(user_id, new_status)

        status_names = {
            ManagerStatus.ACTIVE: "🟢 Активен",
            ManagerStatus.BUSY: "🟡 Занят",
            ManagerStatus.OFFLINE: "🔴 Оффлайн",
        }

        await callback.answer(f"✅ Статус изменен на: {status_names[new_status]}")

        # Обновляем сообщение
        await cmd_manager_status(callback.message)

    except Exception as e:
        logger.error(f"Ошибка смены статуса менеджера {user_id}: {e}")
        await callback.answer("❌ Ошибка смены статуса", show_alert=True)
