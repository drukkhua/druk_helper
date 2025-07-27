"""
Модели данных для системы аналитики
Определяет структуры для хранения информации о запросах пользователей
"""

import sqlite3
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class UserQuery:
    """Модель пользовательского запроса"""

    id: Optional[int] = None
    user_id: int = 0
    query_text: str = ""
    language: str = "ukr"
    timestamp: datetime = None

    # AI ответ
    ai_response: str = ""
    confidence: float = 0.0
    source: str = ""  # "ai", "template", "fallback"
    should_contact_manager: bool = False

    # Контекст
    context_used: str = ""
    search_type: str = ""  # "keyword", "vector", "hybrid"
    relevance_scores: str = ""  # JSON строка со скорами

    # Результат
    is_answered: bool = False
    response_time_ms: int = 0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class FeedbackEntry:
    """Модель пользовательского фидбека"""

    id: Optional[int] = None
    user_id: int = 0
    query_id: Optional[int] = None
    feedback_type: str = ""  # "helpful", "not_helpful", "suggestion"
    feedback_text: str = ""
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class KnowledgeGap:
    """Модель пробела в знаниях"""

    id: Optional[int] = None
    query_pattern: str = ""
    frequency: int = 0
    category: str = ""
    language: str = "ukr"
    priority: str = "medium"  # "low", "medium", "high"
    status: str = "new"  # "new", "in_progress", "resolved"
    first_seen: datetime = None
    last_seen: datetime = None

    def __post_init__(self):
        if self.first_seen is None:
            self.first_seen = datetime.now()
        if self.last_seen is None:
            self.last_seen = datetime.now()


class AnalyticsDatabase:
    """Класс для работы с базой данных аналитики"""

    def __init__(self, db_path: str = "./data/analytics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Создаем таблицы при инициализации
        self._create_tables()
        logger.info(f"Analytics database инициализирована: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Получает подключение к базе данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        """Создает таблицы в базе данных"""
        with self._get_connection() as conn:
            # Таблица пользовательских запросов
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    query_text TEXT NOT NULL,
                    language VARCHAR(10) DEFAULT 'ukr',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

                    ai_response TEXT,
                    confidence REAL DEFAULT 0.0,
                    source VARCHAR(20),
                    should_contact_manager BOOLEAN DEFAULT FALSE,

                    context_used TEXT,
                    search_type VARCHAR(20),
                    relevance_scores TEXT,

                    is_answered BOOLEAN DEFAULT FALSE,
                    response_time_ms INTEGER DEFAULT 0
                )
            """
            )

            # Таблица пользовательского фидбека
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    query_id INTEGER,
                    feedback_type VARCHAR(20) NOT NULL,
                    feedback_text TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (query_id) REFERENCES user_queries (id)
                )
            """
            )

            # Таблица пробелов в знаниях
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_gaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_pattern TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    category VARCHAR(50),
                    language VARCHAR(10) DEFAULT 'ukr',
                    priority VARCHAR(10) DEFAULT 'medium',
                    status VARCHAR(20) DEFAULT 'new',
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Индексы для оптимизации
            conn.execute("CREATE INDEX IF NOT EXISTS idx_queries_user_id ON user_queries(user_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_queries_timestamp ON user_queries(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_queries_is_answered ON user_queries(is_answered)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_gaps_frequency ON knowledge_gaps(frequency)"
            )

            conn.commit()

    def save_user_query(self, query: UserQuery) -> int:
        """Сохраняет пользовательский запрос в базу данных"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO user_queries (
                    user_id, query_text, language, timestamp,
                    ai_response, confidence, source, should_contact_manager,
                    context_used, search_type, relevance_scores,
                    is_answered, response_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    query.user_id,
                    query.query_text,
                    query.language,
                    query.timestamp,
                    query.ai_response,
                    query.confidence,
                    query.source,
                    query.should_contact_manager,
                    query.context_used,
                    query.search_type,
                    query.relevance_scores,
                    query.is_answered,
                    query.response_time_ms,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def save_feedback(self, feedback: FeedbackEntry) -> int:
        """Сохраняет пользовательский фидбек"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO feedback_entries (
                    user_id, query_id, feedback_type, feedback_text, timestamp
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    feedback.user_id,
                    feedback.query_id,
                    feedback.feedback_type,
                    feedback.feedback_text,
                    feedback.timestamp,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def save_knowledge_gap(self, gap: KnowledgeGap) -> int:
        """Сохраняет или обновляет пробел в знаниях"""
        with self._get_connection() as conn:
            # Проверяем, есть ли уже такой паттерн
            existing = conn.execute(
                """
                SELECT id, frequency FROM knowledge_gaps
                WHERE query_pattern = ? AND language = ?
            """,
                (gap.query_pattern, gap.language),
            ).fetchone()

            if existing:
                # Обновляем существующий
                conn.execute(
                    """
                    UPDATE knowledge_gaps
                    SET frequency = frequency + 1, last_seen = ?, status = ?
                    WHERE id = ?
                """,
                    (gap.last_seen, gap.status, existing["id"]),
                )
                conn.commit()
                return existing["id"]
            else:
                # Создаем новый
                cursor = conn.execute(
                    """
                    INSERT INTO knowledge_gaps (
                        query_pattern, frequency, category, language,
                        priority, status, first_seen, last_seen
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        gap.query_pattern,
                        gap.frequency,
                        gap.category,
                        gap.language,
                        gap.priority,
                        gap.status,
                        gap.first_seen,
                        gap.last_seen,
                    ),
                )
                conn.commit()
                return cursor.lastrowid

    def get_recent_queries(self, limit: int = 100) -> List[UserQuery]:
        """Получает последние запросы"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM user_queries
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()

            return [self._row_to_user_query(row) for row in rows]

    def get_unanswered_queries(self, days: int = 7) -> List[UserQuery]:
        """Получает неотвеченные запросы за последние N дней"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM user_queries
                WHERE is_answered = FALSE
                AND timestamp >= datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
            """,
                (days,),
            ).fetchall()

            return [self._row_to_user_query(row) for row in rows]

    def get_knowledge_gaps(self, limit: int = 50) -> List[KnowledgeGap]:
        """Получает топ пробелов в знаниях по частоте"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM knowledge_gaps
                ORDER BY frequency DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()

            return [self._row_to_knowledge_gap(row) for row in rows]

    def get_stats(self) -> Dict:
        """Получает общую статистику"""
        with self._get_connection() as conn:
            total_queries = conn.execute("SELECT COUNT(*) as count FROM user_queries").fetchone()[
                "count"
            ]
            answered_queries = conn.execute(
                "SELECT COUNT(*) as count FROM user_queries WHERE is_answered = TRUE"
            ).fetchone()["count"]
            avg_confidence = conn.execute(
                "SELECT AVG(confidence) as avg FROM user_queries WHERE confidence > 0"
            ).fetchone()["avg"]
            total_gaps = conn.execute("SELECT COUNT(*) as count FROM knowledge_gaps").fetchone()[
                "count"
            ]

            return {
                "total_queries": total_queries,
                "answered_queries": answered_queries,
                "unanswered_queries": total_queries - answered_queries,
                "answer_rate": (answered_queries / total_queries * 100) if total_queries > 0 else 0,
                "avg_confidence": round(avg_confidence or 0, 3),
                "knowledge_gaps": total_gaps,
            }

    def _row_to_user_query(self, row) -> UserQuery:
        """Конвертирует строку БД в объект UserQuery"""
        return UserQuery(
            id=row["id"],
            user_id=row["user_id"],
            query_text=row["query_text"],
            language=row["language"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            ai_response=row["ai_response"] or "",
            confidence=row["confidence"],
            source=row["source"] or "",
            should_contact_manager=bool(row["should_contact_manager"]),
            context_used=row["context_used"] or "",
            search_type=row["search_type"] or "",
            relevance_scores=row["relevance_scores"] or "",
            is_answered=bool(row["is_answered"]),
            response_time_ms=row["response_time_ms"],
        )

    def _row_to_knowledge_gap(self, row) -> KnowledgeGap:
        """Конвертирует строку БД в объект KnowledgeGap"""
        return KnowledgeGap(
            id=row["id"],
            query_pattern=row["query_pattern"],
            frequency=row["frequency"],
            category=row["category"] or "",
            language=row["language"],
            priority=row["priority"],
            status=row["status"],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]),
        )


# Глобальный экземпляр базы данных
analytics_db = AnalyticsDatabase()
