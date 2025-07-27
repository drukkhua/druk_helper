"""
Модели данных для системы менеджеров и истории диалогов
Объединяет управление менеджерами с SQLite для хранения истории
"""

import sqlite3
import logging
from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional, Dict
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ManagerStatus(Enum):
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"
    VACATION = "vacation"


class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Manager:
    """Модель менеджера"""

    id: Optional[int] = None
    telegram_id: int = 0
    name: str = ""
    username: Optional[str] = None
    status: ManagerStatus = ManagerStatus.OFFLINE

    # Рабочее время
    work_days: str = "monday,tuesday,wednesday,thursday,friday"
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


@dataclass
class ConversationMessage:
    """Модель сообщения в диалоге"""

    id: Optional[int] = None
    user_id: int = 0
    message_type: MessageType = MessageType.USER
    content: str = ""
    timestamp: datetime = None

    # Метаданные
    category: Optional[str] = None
    has_upselling: bool = False
    search_type: Optional[str] = None
    relevance_score: Optional[float] = None
    response_time_ms: Optional[int] = None

    # Контекст
    manager_id: Optional[int] = None
    is_auto_response: bool = False
    file_info: Optional[str] = None  # JSON для информации о файлах

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ActiveChat:
    """Модель активного чата"""

    id: Optional[int] = None
    client_telegram_id: int = 0
    manager_telegram_id: int = 0
    started_at: datetime = None
    last_message_at: datetime = None
    status: str = "active"  # active, completed, transferred

    client_name: Optional[str] = None
    client_username: Optional[str] = None
    initial_query: Optional[str] = None

    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()
        if self.last_message_at is None:
            self.last_message_at = datetime.now()


class UnifiedDatabase:
    """Объединенная база данных для менеджеров и истории диалогов"""

    def __init__(self, db_path: str = "./data/unified_system.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Создаем таблицы при инициализации
        self._create_tables()
        logger.info(f"Unified database инициализирована: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Получает подключение к базе данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Включаем поддержку внешних ключей
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _create_tables(self):
        """Создает все необходимые таблицы"""
        with self._get_connection() as conn:
            # Таблица менеджеров
            conn.execute(
                """
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
            """
            )

            # Таблица активных чатов
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS active_chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_telegram_id INTEGER NOT NULL,
                    manager_telegram_id INTEGER NOT NULL,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',

                    client_name TEXT,
                    client_username TEXT,
                    initial_query TEXT,

                    FOREIGN KEY (manager_telegram_id) REFERENCES managers (telegram_id)
                )
            """
            )

            # Таблица истории сообщений (расширенная)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message_type TEXT NOT NULL, -- 'user', 'assistant', 'system'
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

                    -- Метаданные для поиска и анализа
                    category TEXT,
                    has_upselling BOOLEAN DEFAULT FALSE,
                    search_type TEXT, -- 'keyword', 'vector', 'hybrid', 'auto'
                    relevance_score REAL,
                    response_time_ms INTEGER,

                    -- Контекст обработки
                    manager_id INTEGER,
                    is_auto_response BOOLEAN DEFAULT FALSE,
                    file_info TEXT, -- JSON с информацией о файлах

                    FOREIGN KEY (manager_id) REFERENCES managers (telegram_id)
                )
            """
            )

            # Таблица статистики пользователей (для быстрых запросов)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    first_message_date DATETIME,
                    last_message_date DATETIME,
                    total_messages INTEGER DEFAULT 0,
                    total_responses INTEGER DEFAULT 0,
                    avg_response_time_ms REAL,
                    favorite_category TEXT,
                    has_uploaded_files BOOLEAN DEFAULT FALSE,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Индексы для оптимизации
            self._create_indexes(conn)
            conn.commit()

    def _create_indexes(self, conn):
        """Создает индексы для оптимизации запросов"""
        indexes = [
            # Менеджеры
            "CREATE INDEX IF NOT EXISTS idx_managers_status ON managers(status)",
            "CREATE INDEX IF NOT EXISTS idx_managers_telegram_id ON managers(telegram_id)",
            # Активные чаты
            "CREATE INDEX IF NOT EXISTS idx_chats_manager ON active_chats(manager_telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_chats_client ON active_chats(client_telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_chats_status ON active_chats(status)",
            # История сообщений
            "CREATE INDEX IF NOT EXISTS idx_history_user_id ON conversation_history(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_history_timestamp ON conversation_history(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_history_message_type ON conversation_history(message_type)",
            "CREATE INDEX IF NOT EXISTS idx_history_category ON conversation_history(category)",
            "CREATE INDEX IF NOT EXISTS idx_history_manager ON conversation_history(manager_id)",
            "CREATE INDEX IF NOT EXISTS idx_history_auto_response ON conversation_history(is_auto_response)",
            # Составные индексы для сложных запросов
            "CREATE INDEX IF NOT EXISTS idx_history_user_time ON conversation_history(user_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_history_user_type ON conversation_history(user_id, message_type)",
        ]

        for index_sql in indexes:
            conn.execute(index_sql)

    # =================
    # МЕТОДЫ МЕНЕДЖЕРОВ
    # =================

    def add_manager(self, manager: Manager) -> int:
        """Добавляет нового менеджера"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO managers (
                    telegram_id, name, username, status,
                    work_days, work_start, work_end,
                    notifications_enabled, notification_sound, max_active_chats
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    manager.telegram_id,
                    manager.name,
                    manager.username,
                    manager.status.value,
                    manager.work_days,
                    manager.work_start.strftime("%H:%M"),
                    manager.work_end.strftime("%H:%M"),
                    manager.notifications_enabled,
                    manager.notification_sound,
                    manager.max_active_chats,
                ),
            )
            conn.commit()
            logger.info(f"Добавлен менеджер: {manager.name} (ID: {manager.telegram_id})")
            return cursor.lastrowid

    def get_active_managers(self) -> List[Manager]:
        """Получает список активных менеджеров"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM managers
                WHERE status IN ('active', 'busy')
                AND notifications_enabled = TRUE
                ORDER BY active_chats ASC, last_activity DESC
            """
            ).fetchall()

            return [self._row_to_manager(row) for row in rows]

    def get_available_managers_now(self) -> List[Manager]:
        """Получает менеджеров, доступных прямо сейчас"""
        now = datetime.now()
        current_day = now.strftime("%A").lower()
        current_time = now.time()

        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM managers
                WHERE status = 'active'
                AND notifications_enabled = TRUE
                AND active_chats < max_active_chats
            """
            ).fetchall()

            available = []
            for row in rows:
                manager = self._row_to_manager(row)
                work_days = manager.work_days.split(",")

                # Проверяем рабочий день и время
                if (
                    current_day in work_days
                    and manager.work_start <= current_time <= manager.work_end
                ):
                    available.append(manager)

            return sorted(available, key=lambda m: m.active_chats)

    def update_manager_status(self, telegram_id: int, status: ManagerStatus):
        """Обновляет статус менеджера"""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE managers
                SET status = ?, last_activity = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """,
                (status.value, telegram_id),
            )
            conn.commit()
            logger.info(f"Статус менеджера {telegram_id} изменен на {status.value}")

    def get_manager_stats(self, telegram_id: int) -> Dict:
        """Получает статистику менеджера"""
        with self._get_connection() as conn:
            manager = conn.execute(
                """
                SELECT * FROM managers WHERE telegram_id = ?
            """,
                (telegram_id,),
            ).fetchone()

            if not manager:
                return {}

            # Статистика чатов за сегодня
            today_chats = conn.execute(
                """
                SELECT COUNT(*) as count FROM active_chats
                WHERE manager_telegram_id = ?
                AND DATE(started_at) = DATE('now')
            """,
                (telegram_id,),
            ).fetchone()

            # Статистика сообщений за сегодня
            today_messages = conn.execute(
                """
                SELECT COUNT(*) as count FROM conversation_history
                WHERE manager_id = ?
                AND DATE(timestamp) = DATE('now')
                AND message_type = 'assistant'
            """,
                (telegram_id,),
            ).fetchone()

            return {
                "name": manager["name"],
                "status": manager["status"],
                "active_chats": manager["active_chats"],
                "total_clients": manager["total_clients"],
                "today_chats": today_chats["count"] if today_chats else 0,
                "today_messages": today_messages["count"] if today_messages else 0,
                "last_activity": manager["last_activity"],
            }

    def _get_all_managers(self) -> List[Manager]:
        """Получает всех менеджеров (для админки)"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM managers
                ORDER BY name ASC
            """
            ).fetchall()

            return [self._row_to_manager(row) for row in rows]

    # =====================
    # МЕТОДЫ АКТИВНЫХ ЧАТОВ
    # =====================

    def assign_chat_to_manager(self, client_id: int, manager_id: int, client_info: Dict) -> int:
        """Назначает чат менеджеру"""
        with self._get_connection() as conn:
            # Добавляем активный чат
            cursor = conn.execute(
                """
                INSERT INTO active_chats (
                    client_telegram_id, manager_telegram_id,
                    client_name, client_username, initial_query
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    client_id,
                    manager_id,
                    client_info.get("name", ""),
                    client_info.get("username", ""),
                    client_info.get("query", ""),
                ),
            )

            # Увеличиваем счетчик активных чатов
            conn.execute(
                """
                UPDATE managers
                SET active_chats = active_chats + 1, total_clients = total_clients + 1
                WHERE telegram_id = ?
            """,
                (manager_id,),
            )

            conn.commit()
            chat_id = cursor.lastrowid
            logger.info(f"Чат {chat_id} назначен менеджеру {manager_id}")
            return chat_id

    def complete_chat(self, client_id: int, manager_id: int):
        """Завершает чат"""
        with self._get_connection() as conn:
            # Помечаем чат как завершенный
            conn.execute(
                """
                UPDATE active_chats
                SET status = 'completed'
                WHERE client_telegram_id = ? AND manager_telegram_id = ? AND status = 'active'
            """,
                (client_id, manager_id),
            )

            # Уменьшаем счетчик активных чатов
            conn.execute(
                """
                UPDATE managers
                SET active_chats = active_chats - 1
                WHERE telegram_id = ? AND active_chats > 0
            """,
                (manager_id,),
            )

            conn.commit()
            logger.info(f"Чат между {client_id} и {manager_id} завершен")

    def get_active_chat(self, client_id: int) -> Optional[ActiveChat]:
        """Получает активный чат клиента"""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM active_chats
                WHERE client_telegram_id = ? AND status = 'active'
                ORDER BY started_at DESC LIMIT 1
            """,
                (client_id,),
            ).fetchone()

            return self._row_to_active_chat(row) if row else None

    # ==============================
    # МЕТОДЫ ИСТОРИИ СООБЩЕНИЙ
    # ==============================

    def save_message(self, message: ConversationMessage) -> int:
        """Сохраняет сообщение в историю"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversation_history (
                    user_id, message_type, content, timestamp,
                    category, has_upselling, search_type, relevance_score, response_time_ms,
                    manager_id, is_auto_response, file_info
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    message.user_id,
                    message.message_type.value,
                    message.content,
                    message.timestamp,
                    message.category,
                    message.has_upselling,
                    message.search_type,
                    message.relevance_score,
                    message.response_time_ms,
                    message.manager_id,
                    message.is_auto_response,
                    message.file_info,
                ),
            )

            # Обновляем статистику пользователя
            self._update_user_stats(conn, message)

            conn.commit()
            return cursor.lastrowid

    def get_user_history(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> List[ConversationMessage]:
        """Получает историю сообщений пользователя"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversation_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """,
                (user_id, limit, offset),
            ).fetchall()

            return [self._row_to_message(row) for row in rows]

    def get_user_history_by_date(self, user_id: int, days: int) -> List[ConversationMessage]:
        """Получает историю за последние N дней"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversation_history
                WHERE user_id = ?
                AND timestamp >= datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
            """,
                (user_id, days),
            ).fetchall()

            return [self._row_to_message(row) for row in rows]

    def get_user_history_by_type(
        self, user_id: int, message_type: MessageType
    ) -> List[ConversationMessage]:
        """Получает историю по типу сообщений"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversation_history
                WHERE user_id = ? AND message_type = ?
                ORDER BY timestamp DESC
            """,
                (user_id, message_type.value),
            ).fetchall()

            return [self._row_to_message(row) for row in rows]

    def get_user_history_with_upselling(self, user_id: int) -> List[ConversationMessage]:
        """Получает сообщения с upselling предложениями"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversation_history
                WHERE user_id = ? AND has_upselling = TRUE
                ORDER BY timestamp DESC
            """,
                (user_id,),
            ).fetchall()

            return [self._row_to_message(row) for row in rows]

    def search_user_history(
        self, user_id: int, search_text: str, limit: int = 20
    ) -> List[ConversationMessage]:
        """Поиск по истории пользователя"""
        with self._get_connection() as conn:
            search_pattern = f"%{search_text}%"
            rows = conn.execute(
                """
                SELECT * FROM conversation_history
                WHERE user_id = ? AND content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (user_id, search_pattern, limit),
            ).fetchall()

            return [self._row_to_message(row) for row in rows]

    def get_user_stats_summary(self, user_id: int) -> Dict:
        """Получает сводную статистику пользователя"""
        with self._get_connection() as conn:
            # Основная статистика
            stats = conn.execute(
                """
                SELECT
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN message_type = 'user' THEN 1 END) as user_messages,
                    COUNT(CASE WHEN message_type = 'assistant' THEN 1 END) as assistant_messages,
                    COUNT(CASE WHEN has_upselling = TRUE THEN 1 END) as upselling_messages,
                    COUNT(CASE WHEN is_auto_response = TRUE THEN 1 END) as auto_responses,
                    MIN(timestamp) as first_message,
                    MAX(timestamp) as last_message,
                    AVG(CASE WHEN response_time_ms IS NOT NULL THEN response_time_ms END) as avg_response_time
                FROM conversation_history
                WHERE user_id = ?
            """,
                (user_id,),
            ).fetchone()

            # Любимая категория
            top_category = conn.execute(
                """
                SELECT category, COUNT(*) as count
                FROM conversation_history
                WHERE user_id = ? AND category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
                LIMIT 1
            """,
                (user_id,),
            ).fetchone()

            # Активность по дням недели
            activity_by_day = conn.execute(
                """
                SELECT
                    strftime('%w', timestamp) as day_of_week,
                    COUNT(*) as message_count
                FROM conversation_history
                WHERE user_id = ?
                GROUP BY day_of_week
                ORDER BY message_count DESC
            """,
                (user_id,),
            ).fetchall()

            return {
                "total_messages": stats["total_messages"] if stats else 0,
                "user_messages": stats["user_messages"] if stats else 0,
                "assistant_messages": stats["assistant_messages"] if stats else 0,
                "upselling_messages": stats["upselling_messages"] if stats else 0,
                "auto_responses": stats["auto_responses"] if stats else 0,
                "first_message": stats["first_message"] if stats else None,
                "last_message": stats["last_message"] if stats else None,
                "avg_response_time_ms": round(stats["avg_response_time"] or 0, 2) if stats else 0,
                "top_category": top_category["category"] if top_category else "Общие",
                "activity_by_day": dict(activity_by_day) if activity_by_day else {},
            }

    def _update_user_stats(self, conn, message: ConversationMessage):
        """Обновляет статистику пользователя"""
        conn.execute(
            """
            INSERT OR REPLACE INTO user_stats (
                user_id, first_message_date, last_message_date,
                total_messages, total_responses, last_updated
            ) VALUES (
                ?,
                COALESCE((SELECT first_message_date FROM user_stats WHERE user_id = ?), ?),
                ?,
                COALESCE((SELECT total_messages FROM user_stats WHERE user_id = ?), 0) + 1,
                COALESCE((SELECT total_responses FROM user_stats WHERE user_id = ?), 0) +
                    CASE WHEN ? = 'assistant' THEN 1 ELSE 0 END,
                CURRENT_TIMESTAMP
            )
        """,
            (
                message.user_id,
                message.user_id,
                message.timestamp,
                message.timestamp,
                message.user_id,
                message.user_id,
                message.message_type.value,
            ),
        )

    # =================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =================

    def _row_to_manager(self, row) -> Manager:
        """Конвертирует строку БД в объект Manager"""
        return Manager(
            id=row["id"],
            telegram_id=row["telegram_id"],
            name=row["name"],
            username=row["username"],
            status=ManagerStatus(row["status"]),
            work_days=row["work_days"],
            work_start=datetime.strptime(row["work_start"], "%H:%M").time(),
            work_end=datetime.strptime(row["work_end"], "%H:%M").time(),
            total_clients=row["total_clients"],
            active_chats=row["active_chats"],
            last_activity=(
                datetime.fromisoformat(row["last_activity"]) if row["last_activity"] else None
            ),
            notifications_enabled=bool(row["notifications_enabled"]),
            notification_sound=bool(row["notification_sound"]),
            max_active_chats=row["max_active_chats"],
        )

    def _row_to_active_chat(self, row) -> ActiveChat:
        """Конвертирует строку БД в объект ActiveChat"""
        return ActiveChat(
            id=row["id"],
            client_telegram_id=row["client_telegram_id"],
            manager_telegram_id=row["manager_telegram_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            last_message_at=datetime.fromisoformat(row["last_message_at"]),
            status=row["status"],
            client_name=row["client_name"],
            client_username=row["client_username"],
            initial_query=row["initial_query"],
        )

    def _row_to_message(self, row) -> ConversationMessage:
        """Конвертирует строку БД в объект ConversationMessage"""
        return ConversationMessage(
            id=row["id"],
            user_id=row["user_id"],
            message_type=MessageType(row["message_type"]),
            content=row["content"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            category=row["category"],
            has_upselling=bool(row["has_upselling"]),
            search_type=row["search_type"],
            relevance_score=row["relevance_score"],
            response_time_ms=row["response_time_ms"],
            manager_id=row["manager_id"],
            is_auto_response=bool(row["is_auto_response"]),
            file_info=row["file_info"],
        )

    def get_database_stats(self) -> Dict:
        """Получает общую статистику базы данных"""
        with self._get_connection() as conn:
            managers_count = conn.execute("SELECT COUNT(*) as count FROM managers").fetchone()
            active_chats_count = conn.execute(
                "SELECT COUNT(*) as count FROM active_chats WHERE status = 'active'"
            ).fetchone()
            messages_count = conn.execute(
                "SELECT COUNT(*) as count FROM conversation_history"
            ).fetchone()
            users_count = conn.execute(
                "SELECT COUNT(DISTINCT user_id) as count FROM conversation_history"
            ).fetchone()

            return {
                "managers_total": managers_count["count"],
                "active_chats": active_chats_count["count"],
                "total_messages": messages_count["count"],
                "unique_users": users_count["count"],
                "database_path": str(self.db_path),
            }


# Глобальный экземпляр объединенной базы данных
unified_db = UnifiedDatabase()
