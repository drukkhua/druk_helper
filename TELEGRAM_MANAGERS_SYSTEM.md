# Система управления Telegram менеджерами и уведомлений

## Концепция системы

### 🎯 **Цель:**
Создать систему активных менеджеров с уведомлениями и прямыми ссылками на диалоги клиентов.

### 📋 **Логика работы:**

```
📞 КЛИЕНТ ПИШЕТ
    ↓
🕐 ПРОВЕРКА ВРЕМЕНИ
    ├── Рабочее время → Уведомление активных менеджеров
    └── Внерабочее время → Автоответ + уведомление на утро
    ↓
👥 МЕНЕДЖЕРЫ ПОЛУЧАЮТ:
    ├── Push уведомление
    ├── Прямую ссылку tg://user?id=123456
    ├── Краткую информацию о клиенте
    └── Кнопки быстрых действий
```

## Техническая реализация

### 🗄️ **База данных менеджеров**

```python
# src/managers/models.py

import sqlite3
from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional, Dict
from enum import Enum

class ManagerStatus(Enum):
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"
    VACATION = "vacation"

@dataclass
class Manager:
    """Модель менеджера"""
    id: Optional[int] = None
    telegram_id: int = 0
    name: str = ""
    username: Optional[str] = None
    status: ManagerStatus = ManagerStatus.OFFLINE

    # Рабочее время
    work_days: str = "monday,tuesday,wednesday,thursday,friday"  # JSON список дней
    work_start: time = time(9, 0)
    work_end: time = time(18, 0)

    # Статистика
    total_clients: int = 0
    active_chats: int = 0
    last_activity: Optional[datetime] = None

    # Настройки уведомлений
    notifications_enabled: bool = True
    notification_sound: bool = True
    max_active_chats: int = 10

class ManagerDatabase:
    """База данных менеджеров"""

    def __init__(self, db_path: str = "./data/managers.db"):
        self.db_path = db_path
        self._create_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        with self._get_connection() as conn:
            # Таблица менеджеров
            conn.execute("""
                CREATE TABLE IF NOT EXISTS managers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    username TEXT,
                    status TEXT DEFAULT 'offline',

                    work_days TEXT DEFAULT 'monday,tuesday,wednesday,thursday,friday',
                    work_start TEXT DEFAULT '09:00',
                    work_end TEXT DEFAULT '18:00',

                    total_clients INTEGER DEFAULT 0,
                    active_chats INTEGER DEFAULT 0,
                    last_activity DATETIME,

                    notifications_enabled BOOLEAN DEFAULT TRUE,
                    notification_sound BOOLEAN DEFAULT TRUE,
                    max_active_chats INTEGER DEFAULT 10,

                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица активных диалогов
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_telegram_id INTEGER NOT NULL,
                    manager_telegram_id INTEGER NOT NULL,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active', -- active, completed, transferred

                    client_name TEXT,
                    client_username TEXT,
                    initial_query TEXT,

                    FOREIGN KEY (manager_telegram_id) REFERENCES managers (telegram_id)
                )
            """)

            # Индексы
            conn.execute("CREATE INDEX IF NOT EXISTS idx_managers_status ON managers(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chats_manager ON active_chats(manager_telegram_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chats_client ON active_chats(client_telegram_id)")

    def add_manager(self, manager: Manager) -> int:
        """Добавляет нового менеджера"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO managers (
                    telegram_id, name, username, status,
                    work_days, work_start, work_end,
                    notifications_enabled, notification_sound, max_active_chats
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                manager.telegram_id, manager.name, manager.username, manager.status.value,
                manager.work_days, manager.work_start.strftime('%H:%M'), manager.work_end.strftime('%H:%M'),
                manager.notifications_enabled, manager.notification_sound, manager.max_active_chats
            ))
            return cursor.lastrowid

    def get_active_managers(self) -> List[Manager]:
        """Получает список активных менеджеров"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM managers
                WHERE status IN ('active', 'busy')
                AND notifications_enabled = TRUE
                ORDER BY active_chats ASC, last_activity DESC
            """).fetchall()

            return [self._row_to_manager(row) for row in rows]

    def get_available_managers_now(self) -> List[Manager]:
        """Получает менеджеров, доступных прямо сейчас"""
        from datetime import datetime

        now = datetime.now()
        current_day = now.strftime('%A').lower()
        current_time = now.time()

        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM managers
                WHERE status IN ('active')
                AND notifications_enabled = TRUE
                AND active_chats < max_active_chats
            """).fetchall()

            available = []
            for row in rows:
                manager = self._row_to_manager(row)
                work_days = manager.work_days.split(',')

                # Проверяем рабочий день и время
                if (current_day in work_days and
                    manager.work_start <= current_time <= manager.work_end):
                    available.append(manager)

            return sorted(available, key=lambda m: m.active_chats)

    def update_manager_status(self, telegram_id: int, status: ManagerStatus):
        """Обновляет статус менеджера"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE managers
                SET status = ?, last_activity = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (status.value, telegram_id))

    def assign_chat_to_manager(self, client_id: int, manager_id: int, client_info: Dict) -> int:
        """Назначает чат менеджеру"""
        with self._get_connection() as conn:
            # Добавляем активный чат
            cursor = conn.execute("""
                INSERT INTO active_chats (
                    client_telegram_id, manager_telegram_id,
                    client_name, client_username, initial_query
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                client_id, manager_id,
                client_info.get('name', ''),
                client_info.get('username', ''),
                client_info.get('query', '')
            ))

            # Увеличиваем счетчик активных чатов
            conn.execute("""
                UPDATE managers
                SET active_chats = active_chats + 1, total_clients = total_clients + 1
                WHERE telegram_id = ?
            """, (manager_id,))

            return cursor.lastrowid

    def complete_chat(self, client_id: int, manager_id: int):
        """Завершает чат"""
        with self._get_connection() as conn:
            # Помечаем чат как завершенный
            conn.execute("""
                UPDATE active_chats
                SET status = 'completed'
                WHERE client_telegram_id = ? AND manager_telegram_id = ?
            """, (client_id, manager_id))

            # Уменьшаем счетчик активных чатов
            conn.execute("""
                UPDATE managers
                SET active_chats = active_chats - 1
                WHERE telegram_id = ? AND active_chats > 0
            """, (manager_id,))

    def get_manager_stats(self, telegram_id: int) -> Dict:
        """Получает статистику менеджера"""
        with self._get_connection() as conn:
            manager = conn.execute("""
                SELECT * FROM managers WHERE telegram_id = ?
            """, (telegram_id,)).fetchone()

            if not manager:
                return {}

            # Статистика чатов
            today_chats = conn.execute("""
                SELECT COUNT(*) as count FROM active_chats
                WHERE manager_telegram_id = ?
                AND DATE(started_at) = DATE('now')
            """, (telegram_id,)).fetchone()

            return {
                'name': manager['name'],
                'status': manager['status'],
                'active_chats': manager['active_chats'],
                'total_clients': manager['total_clients'],
                'today_chats': today_chats['count'],
                'last_activity': manager['last_activity']
            }

    def _row_to_manager(self, row) -> Manager:
        """Конвертирует строку БД в объект Manager"""
        return Manager(
            id=row['id'],
            telegram_id=row['telegram_id'],
            name=row['name'],
            username=row['username'],
            status=ManagerStatus(row['status']),
            work_days=row['work_days'],
            work_start=datetime.strptime(row['work_start'], '%H:%M').time(),
            work_end=datetime.strptime(row['work_end'], '%H:%M').time(),
            total_clients=row['total_clients'],
            active_chats=row['active_chats'],
            last_activity=datetime.fromisoformat(row['last_activity']) if row['last_activity'] else None,
            notifications_enabled=bool(row['notifications_enabled']),
            notification_sound=bool(row['notification_sound']),
            max_active_chats=row['max_active_chats']
        )

# Глобальный экземпляр
manager_db = ManagerDatabase()
```

### 🔔 **Система уведомлений менеджеров**

```python
# src/managers/notification_system.py

from aiogram import Bot, types
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from typing import List, Dict, Optional
import logging
from datetime import datetime

from src.managers.models import manager_db, Manager
from config import Config

logger = logging.getLogger(__name__)

class ManagerNotificationSystem:
    """Система уведомлений для менеджеров"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.manager_db = manager_db

    async def notify_new_client(self, client_message: types.Message,
                              urgency: str = "normal") -> List[int]:
        """Уведомляет доступных менеджеров о новом клиенте"""

        # Получаем доступных менеджеров
        available_managers = self.manager_db.get_available_managers_now()

        if not available_managers:
            # Никого нет - уведомляем всех активных
            available_managers = self.manager_db.get_active_managers()

        if not available_managers:
            logger.warning("Нет доступных менеджеров для уведомления")
            return []

        # Информация о клиенте
        client_info = self._extract_client_info(client_message)

        # Формируем уведомление
        notification = self._create_notification_message(client_info, urgency)
        keyboard = self._create_manager_keyboard(client_info['telegram_id'])

        notified_managers = []

        # Отправляем уведомления
        for manager in available_managers:
            try:
                await self.bot.send_message(
                    chat_id=manager.telegram_id,
                    text=notification,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                notified_managers.append(manager.telegram_id)
                logger.info(f"Уведомлен менеджер {manager.name} ({manager.telegram_id})")

            except (TelegramBadRequest, TelegramForbiddenError) as e:
                logger.error(f"Ошибка отправки уведомления менеджеру {manager.telegram_id}: {e}")
                # Возможно, менеджер заблокировал бота - помечаем как неактивного
                self.manager_db.update_manager_status(manager.telegram_id, ManagerStatus.OFFLINE)

        return notified_managers

    async def notify_file_upload(self, client_message: types.Message,
                                file_analysis: Dict) -> List[int]:
        """Уведомляет менеджеров о загрузке файла"""

        available_managers = self.manager_db.get_available_managers_now()
        client_info = self._extract_client_info(client_message)

        # Специальное уведомление для файлов
        notification = self._create_file_notification(client_info, file_analysis)
        keyboard = self._create_manager_keyboard(client_info['telegram_id'])

        notified_managers = []

        for manager in available_managers:
            try:
                await self.bot.send_message(
                    chat_id=manager.telegram_id,
                    text=notification,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                notified_managers.append(manager.telegram_id)

            except Exception as e:
                logger.error(f"Ошибка отправки уведомления о файле: {e}")

        return notified_managers

    async def notify_high_priority(self, client_message: types.Message,
                                 reason: str) -> List[int]:
        """Уведомляет всех активных менеджеров о высокоприоритетном клиенте"""

        all_active = self.manager_db.get_active_managers()
        client_info = self._extract_client_info(client_message)

        notification = f"""🚨 **ПРИОРИТЕТНЫЙ КЛИЕНТ**

{self._create_notification_message(client_info, "high")}

⚠️ **Причина приоритета:** {reason}
"""

        keyboard = self._create_manager_keyboard(client_info['telegram_id'])

        notified_managers = []

        for manager in all_active:
            try:
                await self.bot.send_message(
                    chat_id=manager.telegram_id,
                    text=notification,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                notified_managers.append(manager.telegram_id)

            except Exception as e:
                logger.error(f"Ошибка приоритетного уведомления: {e}")

        return notified_managers

    def _extract_client_info(self, message: types.Message) -> Dict:
        """Извлекает информацию о клиенте"""
        user = message.from_user

        return {
            'telegram_id': user.id,
            'name': user.full_name or "Без имени",
            'username': f"@{user.username}" if user.username else "Без username",
            'query': message.text or message.caption or "[файл/медиа]",
            'message_time': message.date.strftime("%H:%M"),
            'language_code': user.language_code or "uk"
        }

    def _create_notification_message(self, client_info: Dict, urgency: str = "normal") -> str:
        """Создает текст уведомления"""

        urgency_emoji = {
            "low": "📝",
            "normal": "📞",
            "high": "🚨",
            "urgent": "🔥"
        }

        emoji = urgency_emoji.get(urgency, "📞")

        # Обрезаем длинный запрос
        query = client_info['query']
        if len(query) > 100:
            query = query[:97] + "..."

        return f"""{emoji} **Новый клиент ждет ответ!**

👤 **Клиент:** {client_info['name']}
📱 **Username:** {client_info['username']}
🆔 **ID:** `{client_info['telegram_id']}`

💬 **Сообщение:**
_{query}_

🕐 **Время:** {client_info['message_time']}

⚡ **Нажмите "Ответить" для быстрого перехода к диалогу**"""

    def _create_file_notification(self, client_info: Dict, file_analysis: Dict) -> str:
        """Создает уведомление о загрузке файла"""

        return f"""📁 **Клиент загрузил макет!**

👤 **Клиент:** {client_info['name']}
📱 **Username:** {client_info['username']}
🆔 **ID:** `{client_info['telegram_id']}`

📋 **Файл:** {file_analysis.get('file_name', 'unknown')}
📏 **Размер:** {file_analysis.get('file_size_mb', 0)} МБ
🔧 **Формат:** {file_analysis.get('file_extension', 'unknown')}
⭐ **Качество:** {file_analysis.get('quality_assessment', 'unknown')}

🕐 **Время:** {client_info['message_time']}

✅ **Клиенту отправлен автоответ о проверке**"""

    def _create_manager_keyboard(self, client_telegram_id: int) -> types.InlineKeyboardMarkup:
        """Создает клавиатуру для менеджера"""

        return types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="💬 Ответить клиенту",
                    url=f"tg://user?id={client_telegram_id}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="✅ Взял в работу",
                    callback_data=f"manager:take:{client_telegram_id}"
                ),
                types.InlineKeyboardButton(
                    text="📊 Профиль клиента",
                    callback_data=f"manager:profile:{client_telegram_id}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🔇 Отключить уведомления на час",
                    callback_data="manager:mute:60"
                )
            ]
        ])

    async def handle_manager_callback(self, callback: types.CallbackQuery):
        """Обрабатывает callback от менеджеров"""

        data_parts = callback.data.split(":")
        action = data_parts[1]

        if action == "take":
            client_id = int(data_parts[2])
            await self._handle_take_client(callback, client_id)

        elif action == "profile":
            client_id = int(data_parts[2])
            await self._show_client_profile(callback, client_id)

        elif action == "mute":
            minutes = int(data_parts[2])
            await self._mute_notifications(callback, minutes)

    async def _handle_take_client(self, callback: types.CallbackQuery, client_id: int):
        """Обрабатывает взятие клиента в работу"""

        manager_id = callback.from_user.id

        # Назначаем чат менеджеру
        chat_id = self.manager_db.assign_chat_to_manager(
            client_id, manager_id,
            {'name': callback.from_user.full_name}
        )

        # Уведомляем менеджера
        await callback.message.edit_text(
            f"✅ Клиент взят в работу!\n\n"
            f"🆔 Чат ID: {chat_id}\n"
            f"👤 Менеджер: {callback.from_user.full_name}\n"
            f"🕐 Время: {datetime.now().strftime('%H:%M')}\n\n"
            f"💬 Переходите к диалогу и отвечайте клиенту.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(
                    text="💬 Перейти к диалогу",
                    url=f"tg://user?id={client_id}"
                )]
            ])
        )

        # Уведомляем других менеджеров
        await self._notify_client_taken(client_id, callback.from_user.full_name)

    async def _show_client_profile(self, callback: types.CallbackQuery, client_id: int):
        """Показывает профиль клиента"""

        # Получаем историю клиента из аналитики
        from src.analytics.models import analytics_db

        try:
            client_history = analytics_db.get_user_history(client_id, limit=5)
            stats = analytics_db.get_user_stats(client_id)

            profile_text = f"""📊 **Профиль клиента ID: {client_id}**

📈 **Статистика:**
• Всего запросов: {stats.get('total_queries', 0)}
• Получено ответов: {stats.get('answered_queries', 0)}
• Первое обращение: {stats.get('first_query_date', 'Неизвестно')}

📝 **Последние запросы:**"""

            for i, query in enumerate(client_history[:3], 1):
                date_str = query.timestamp.strftime("%d.%m %H:%M")
                query_preview = query.query_text[:50] + "..." if len(query.query_text) > 50 else query.query_text
                profile_text += f"\n{i}. {date_str}: _{query_preview}_"

        except Exception as e:
            profile_text = f"❌ Ошибка загрузки профиля клиента: {e}"

        await callback.answer(profile_text, show_alert=True)

    async def _mute_notifications(self, callback: types.CallbackQuery, minutes: int):
        """Отключает уведомления для менеджера"""

        # Здесь можно реализовать временное отключение уведомлений
        await callback.answer(f"🔇 Уведомления отключены на {minutes} минут", show_alert=True)

    async def _notify_client_taken(self, client_id: int, manager_name: str):
        """Уведомляет других менеджеров, что клиент взят в работу"""

        active_managers = self.manager_db.get_active_managers()

        for manager in active_managers:
            try:
                await self.bot.send_message(
                    manager.telegram_id,
                    f"ℹ️ Клиент {client_id} взят в работу менеджером {manager_name}"
                )
            except:
                pass  # Игнорируем ошибки массовых уведомлений

# Функция для создания глобального экземпляра
def create_notification_system(bot: Bot) -> ManagerNotificationSystem:
    return ManagerNotificationSystem(bot)
```

### 🎛️ **Панель управления менеджерами**

```python
# src/managers/admin_panel.py

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.managers.models import manager_db, Manager, ManagerStatus
from config import Config

router = Router()

class ManagerStates(StatesGroup):
    waiting_for_manager_info = State()

@router.message(Command("manager_panel"))
async def cmd_manager_panel(message: types.Message):
    """Панель управления менеджерами (только для админов)"""

    if message.from_user.id not in Config.ADMIN_USER_IDS:
        await message.answer("❌ Доступ запрещен")
        return

    # Статистика менеджеров
    all_managers = manager_db.get_active_managers()

    if not all_managers:
        text = "👥 **Панель менеджеров**\n\n❌ Нет зарегистрированных менеджеров"
    else:
        text = "👥 **Панель менеджеров**\n\n"

        for manager in all_managers:
            status_emoji = {
                "active": "🟢",
                "busy": "🟡",
                "offline": "🔴",
                "vacation": "🏖️"
            }

            emoji = status_emoji.get(manager.status.value, "❓")
            text += f"{emoji} **{manager.name}**\n"
            text += f"   • ID: `{manager.telegram_id}`\n"
            text += f"   • Активных чатов: {manager.active_chats}/{manager.max_active_chats}\n"
            text += f"   • Всего клиентов: {manager.total_clients}\n\n"

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="➕ Добавить менеджера", callback_data="admin:add_manager"),
            types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")
        ],
        [
            types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:refresh_managers")
        ]
    ])

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data.startswith("admin:"))
async def handle_admin_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка админских callback'ов"""

    if callback.from_user.id not in Config.ADMIN_USER_IDS:
        await callback.answer("❌ Доступ запрещен")
        return

    action = callback.data.split(":")[1]

    if action == "add_manager":
        await callback.message.edit_text(
            "➕ **Добавление нового менеджера**\n\n"
            "Отправьте информацию в формате:\n"
            "`ID:Имя:Username`\n\n"
            "Пример: `123456789:Иван Петров:ivan_manager`\n"
            "Username можно не указывать.",
            parse_mode="Markdown"
        )
        await state.set_state(ManagerStates.waiting_for_manager_info)

    elif action == "stats":
        await show_detailed_stats(callback)

    elif action == "refresh_managers":
        # Обновляем информацию
        await cmd_manager_panel(callback.message)

@router.message(ManagerStates.waiting_for_manager_info)
async def process_new_manager(message: types.Message, state: FSMContext):
    """Обрабатывает добавление нового менеджера"""

    try:
        parts = message.text.split(":")
        if len(parts) < 2:
            await message.answer("❌ Неверный формат. Используйте: `ID:Имя:Username`", parse_mode="Markdown")
            return

        telegram_id = int(parts[0])
        name = parts[1]
        username = parts[2] if len(parts) > 2 else None

        # Создаем менеджера
        manager = Manager(
            telegram_id=telegram_id,
            name=name,
            username=username,
            status=ManagerStatus.ACTIVE
        )

        manager_db.add_manager(manager)

        await message.answer(
            f"✅ Менеджер добавлен!\n\n"
            f"👤 **{name}**\n"
            f"🆔 ID: `{telegram_id}`\n"
            f"📱 Username: {f'@{username}' if username else 'Не указан'}\n\n"
            f"Менеджер будет получать уведомления о новых клиентах.",
            parse_mode="Markdown"
        )

    except ValueError:
        await message.answer("❌ ID должен быть числом")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

    await state.clear()

async def show_detailed_stats(callback: types.CallbackQuery):
    """Показывает детальную статистику менеджеров"""

    all_managers = manager_db.get_active_managers()

    if not all_managers:
        await callback.answer("📊 Нет данных для статистики")
        return

    stats_text = "📊 **Детальная статистика менеджеров**\n\n"

    total_chats = sum(m.active_chats for m in all_managers)
    total_clients = sum(m.total_clients for m in all_managers)

    stats_text += f"📈 **Общая статистика:**\n"
    stats_text += f"• Всего менеджеров: {len(all_managers)}\n"
    stats_text += f"• Активных чатов: {total_chats}\n"
    stats_text += f"• Обслужено клиентов: {total_clients}\n\n"

    stats_text += f"👥 **По менеджерам:**\n"

    for manager in sorted(all_managers, key=lambda m: m.active_chats, reverse=True):
        stats = manager_db.get_manager_stats(manager.telegram_id)

        stats_text += f"• **{manager.name}**\n"
        stats_text += f"  Активных: {stats['active_chats']}, "
        stats_text += f"Сегодня: {stats['today_chats']}, "
        stats_text += f"Всего: {stats['total_clients']}\n"

    await callback.message.edit_text(stats_text, parse_mode="Markdown")
```

### 🔧 **Интеграция с основной системой**

```python
# Модификация src/bot/handlers/main.py

from src.managers.notification_system import create_notification_system
from src.managers.models import manager_db

# Создаем систему уведомлений
notification_system = None

async def setup_notification_system(bot):
    """Инициализирует систему уведомлений"""
    global notification_system
    notification_system = create_notification_system(bot)

@router.message()
async def handle_all_messages(message: types.Message, state: FSMContext):
    """Универсальный обработчик с уведомлениями менеджеров"""

    # Проверяем автоматический режим
    auto_result = await auto_mode_controller.should_handle_automatically(message)

    if auto_result['auto_handle']:
        # Автоматический ответ
        await message.answer(auto_result['response'])

        # Уведомляем менеджеров в зависимости от типа
        if auto_result['reason'] == 'file_upload':
            await notification_system.notify_file_upload(
                message, auto_result.get('file_analysis', {})
            )
        elif auto_result['reason'] == 'low_confidence_fallback':
            await notification_system.notify_new_client(message, urgency="high")

        return

    # Рабочее время - уведомляем доступных менеджеров
    if auto_result['action'] == 'forward_to_manager':
        notified = await notification_system.notify_new_client(message)

        if not notified:
            # Никого нет - отправляем резервный ответ
            await message.answer(
                "📞 Спасибо за обращение! Все менеджеры сейчас заняты.\n"
                "Мы обязательно свяжемся с вами в ближайшее время."
            )

        return

    # Остальная логика...

# Добавляем команды для менеджеров
@router.message(Command("manager_status"))
async def cmd_manager_status(message: types.Message):
    """Команда для изменения статуса менеджера"""

    # Проверяем, зарегистрирован ли как менеджер
    stats = manager_db.get_manager_stats(message.from_user.id)

    if not stats:
        await message.answer(
            "❌ Вы не зарегистрированы как менеджер.\n"
            "Обратитесь к администратору для регистрации."
        )
        return

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🟢 Активен", callback_data="status:active"),
            types.InlineKeyboardButton(text="🟡 Занят", callback_data="status:busy")
        ],
        [
            types.InlineKeyboardButton(text="🔴 Недоступен", callback_data="status:offline"),
            types.InlineKeyboardButton(text="🏖️ Отпуск", callback_data="status:vacation")
        ]
    ])

    await message.answer(
        f"👤 **{stats['name']}**\n"
        f"📊 Текущий статус: {stats['status']}\n"
        f"💬 Активных чатов: {stats['active_chats']}\n"
        f"📈 Клиентов сегодня: {stats['today_chats']}\n\n"
        f"Выберите новый статус:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("status:"))
async def change_manager_status(callback: types.CallbackQuery):
    """Изменяет статус менеджера"""

    new_status = ManagerStatus(callback.data.split(":")[1])
    manager_id = callback.from_user.id

    manager_db.update_manager_status(manager_id, new_status)

    status_names = {
        "active": "🟢 Активен",
        "busy": "🟡 Занят",
        "offline": "🔴 Недоступен",
        "vacation": "🏖️ В отпуске"
    }

    await callback.message.edit_text(
        f"✅ Статус изменен на: {status_names[new_status.value]}"
    )
```

## Практические возможности системы

### 📱 **Что получают менеджеры:**

1. **Мгновенные уведомления** о новых клиентах
2. **Прямые ссылки** `tg://user?id=123456` для перехода к диалогу
3. **Профиль клиента** с историей обращений
4. **Быстрые действия** - "Взял в работу", "Профиль", "Отключить уведомления"
5. **Статистику работы** - активные чаты, клиенты за день
6. **Управление статусом** - Активен/Занят/Недоступен

### 🎯 **Умные функции:**

- **Балансировка нагрузки** - менеджеры с меньшим количеством чатов получают уведомления первыми
- **Рабочее время** - каждый менеджер настраивает свои часы работы
- **Приоритизация** - файлы и сложные запросы помечаются как приоритетные
- **Автоматическое отключение** - если менеджер заблокировал бота, он помечается как недоступный

## Оценка реализации

### ⏱️ **Временные затраты:**

| Модуль | Время | Сложность |
|--------|-------|-----------|
| **База данных менеджеров** | 6-8 часов | Средняя |
| **Система уведомлений** | 10-12 часов | Высокая |
| **Панель управления** | 6-8 часов | Средняя |
| **Интеграция** | 4-6 часов | Средняя |
| **Тестирование** | 6-8 часов | Средняя |
| **ИТОГО** | **32-42 часа** | **4-5 дней** |

### ✅ **Да, это полностью возможно!**

**Telegram API поддерживает:**
- ✅ Deep links `tg://user?id=123456` - работают идеально
- ✅ Inline кнопки с callback данными
- ✅ Отправка уведомлений конкретным пользователям
- ✅ Обработка файлов и медиа

**Система будет работать так:**
1. Клиент пишет → Бот определяет нужна ли помощь менеджера
2. Уведомление отправляется всем доступным менеджерам
3. Менеджер нажимает "Ответить клиенту" → переходит напрямую в личный чат
4. Менеджер нажимает "Взял в работу" → другие менеджеры видят, что клиент обслуживается

**Это значительно улучшит скорость реакции и организацию работы менеджеров!**
