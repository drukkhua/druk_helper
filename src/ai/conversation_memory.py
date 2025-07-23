"""
Система памяти разговора для AI бота
Хранит историю диалогов пользователей и поддерживает контекст
"""

import json
import logging
import os
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Структура сообщения в разговоре"""

    role: str  # "user" или "assistant"
    content: str
    timestamp: float
    metadata: Optional[Dict] = None


@dataclass
class ConversationSession:
    """Сессия разговора пользователя"""

    user_id: int
    messages: List[Message]
    created_at: float
    last_activity: float
    language: str = "ukr"
    metadata: Optional[Dict] = None

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Добавляет сообщение в сессию"""
        message = Message(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_activity = time.time()

    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Возвращает последние N сообщений"""
        return self.messages[-limit:] if self.messages else []

    def get_context_for_ai(self, max_messages: int = 6) -> List[Dict]:
        """Формирует контекст для OpenAI API"""
        recent_messages = self.get_recent_messages(max_messages)

        # Конвертируем в формат OpenAI
        context = []
        for msg in recent_messages:
            context.append({
                "role": msg.role,
                "content": msg.content
            })

        return context

    def is_expired(self, timeout_hours: int = 24) -> bool:
        """Проверяет, истекла ли сессия"""
        timeout_seconds = timeout_hours * 3600
        return (time.time() - self.last_activity) > timeout_seconds


class ConversationMemory:
    """Менеджер памяти разговоров"""

    def __init__(self, storage_path: str = "./data/conversations"):
        self.storage_path = storage_path
        self.sessions: Dict[int, ConversationSession] = {}
        self.max_session_age_hours = 24
        self.max_messages_per_session = 100

        # Создаем директорию для хранения
        os.makedirs(storage_path, exist_ok=True)

        # Загружаем существующие сессии
        self._load_sessions()

        logger.info(f"Инициализирован ConversationMemory с {len(self.sessions)} активными сессиями")

    def get_session(self, user_id: int, language: str = "ukr") -> ConversationSession:
        """Получает или создает сессию для пользователя"""
        if user_id not in self.sessions:
            # Создаем новую сессию
            self.sessions[user_id] = ConversationSession(
                user_id=user_id,
                messages=[],
                created_at=time.time(),
                last_activity=time.time(),
                language=language
            )
            logger.info(f"Создана новая сессия для пользователя {user_id}")
        else:
            # Проверяем, не истекла ли сессия
            session = self.sessions[user_id]
            if session.is_expired(self.max_session_age_hours):
                logger.info(f"Сессия пользователя {user_id} истекла, создаем новую")
                self.sessions[user_id] = ConversationSession(
                    user_id=user_id,
                    messages=[],
                    created_at=time.time(),
                    last_activity=time.time(),
                    language=language
                )

        return self.sessions[user_id]

    def add_user_message(self, user_id: int, message: str, language: str = "ukr", metadata: Optional[Dict] = None):
        """Добавляет сообщение пользователя"""
        session = self.get_session(user_id, language)
        session.add_message("user", message, metadata)
        self._save_session(session)
        logger.debug(f"Добавлено сообщение пользователя {user_id}: {message[:50]}...")

    def add_assistant_message(self, user_id: int, message: str, metadata: Optional[Dict] = None):
        """Добавляет ответ ассистента"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            session.add_message("assistant", message, metadata)
            self._save_session(session)
            logger.debug(f"Добавлен ответ ассистента для пользователя {user_id}: {message[:50]}...")

    def get_conversation_context(self, user_id: int, max_messages: int = 6) -> List[Dict]:
        """Получает контекст разговора для AI"""
        if user_id not in self.sessions:
            return []

        session = self.sessions[user_id]
        return session.get_context_for_ai(max_messages)

    def clear_session(self, user_id: int):
        """Очищает сессию пользователя"""
        if user_id in self.sessions:
            del self.sessions[user_id]
            # Удаляем файл сессии
            session_file = os.path.join(self.storage_path, f"session_{user_id}.json")
            if os.path.exists(session_file):
                os.remove(session_file)
            logger.info(f"Очищена сессия пользователя {user_id}")

    def get_session_stats(self, user_id: int) -> Dict:
        """Получает статистику сессии"""
        if user_id not in self.sessions:
            return {"exists": False}

        session = self.sessions[user_id]
        return {
            "exists": True,
            "message_count": len(session.messages),
            "created_at": datetime.fromtimestamp(session.created_at).isoformat(),
            "last_activity": datetime.fromtimestamp(session.last_activity).isoformat(),
            "language": session.language,
            "age_hours": (time.time() - session.created_at) / 3600
        }

    def cleanup_expired_sessions(self):
        """Очищает истекшие сессии"""
        expired_users = []
        for user_id, session in self.sessions.items():
            if session.is_expired(self.max_session_age_hours):
                expired_users.append(user_id)

        for user_id in expired_users:
            self.clear_session(user_id)

        if expired_users:
            logger.info(f"Очищено {len(expired_users)} истекших сессий")

    def _save_session(self, session: ConversationSession):
        """Сохраняет сессию в файл"""
        try:
            session_file = os.path.join(self.storage_path, f"session_{session.user_id}.json")

            # Конвертируем в словарь для JSON
            session_data = {
                "user_id": session.user_id,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "language": session.language,
                "metadata": session.metadata,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                        "metadata": msg.metadata
                    }
                    for msg in session.messages
                ][-self.max_messages_per_session:]  # Ограничиваем количество сообщений
            }

            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Ошибка сохранения сессии {session.user_id}: {e}")

    def _load_sessions(self):
        """Загружает сессии из файлов"""
        try:
            if not os.path.exists(self.storage_path):
                return

            for filename in os.listdir(self.storage_path):
                if filename.startswith("session_") and filename.endswith(".json"):
                    try:
                        session_file = os.path.join(self.storage_path, filename)
                        with open(session_file, 'r', encoding='utf-8') as f:
                            session_data = json.load(f)

                        # Восстанавливаем сессию
                        user_id = session_data["user_id"]
                        messages = []

                        for msg_data in session_data.get("messages", []):
                            message = Message(
                                role=msg_data["role"],
                                content=msg_data["content"],
                                timestamp=msg_data["timestamp"],
                                metadata=msg_data.get("metadata", {})
                            )
                            messages.append(message)

                        session = ConversationSession(
                            user_id=user_id,
                            messages=messages,
                            created_at=session_data["created_at"],
                            last_activity=session_data["last_activity"],
                            language=session_data.get("language", "ukr"),
                            metadata=session_data.get("metadata")
                        )

                        # Проверяем, не истекла ли сессия
                        if not session.is_expired(self.max_session_age_hours):
                            self.sessions[user_id] = session
                        else:
                            # Удаляем истекший файл
                            os.remove(session_file)

                    except Exception as e:
                        logger.error(f"Ошибка загрузки сессии из {filename}: {e}")

            logger.info(f"Загружено {len(self.sessions)} активных сессий")

        except Exception as e:
            logger.error(f"Ошибка загрузки сессий: {e}")


# Глобальный экземпляр памяти разговоров
conversation_memory = ConversationMemory()
