"""
Интеграция системы менеджеров с основным ботом
Обеспечивает связь между обработчиками сообщений и системой уведомлений
"""

from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from typing import Dict, Optional, List
import logging
import asyncio

from src.managers.models import unified_db, ConversationMessage, MessageType
from src.managers.notification_system import ManagerNotificationSystem
from src.managers.admin_panel import router as admin_router
from src.bot.handlers.history import router as history_router
from config import Config

logger = logging.getLogger(__name__)

# Главный роутер для всей системы менеджеров
manager_router = Router()

# Включаем подроутеры
manager_router.include_router(admin_router)
manager_router.include_router(history_router)

# Глобальная система уведомлений
notification_system: Optional[ManagerNotificationSystem] = None


def initialize_manager_system(bot: Bot):
    """Инициализация системы менеджеров"""
    global notification_system

    try:
        notification_system = ManagerNotificationSystem(bot)
        logger.info("Система менеджеров инициализирована успешно")
        return True
    except Exception as e:
        logger.error(f"Ошибка инициализации системы менеджеров: {e}")
        return False


async def process_client_message(
    message: types.Message, response_text: str, metadata: Optional[Dict] = None
) -> bool:
    """
    Обработка сообщения клиента и уведомление менеджеров

    Args:
        message: Сообщение от клиента
        response_text: Ответ ассистента
        metadata: Дополнительные метаданные

    Returns:
        bool: True если уведомления отправлены успешно
    """
    if not notification_system:
        logger.warning("Система уведомлений не инициализирована")
        return False

    try:
        # Определяем приоритет сообщения
        urgency = _determine_message_urgency(message, metadata or {})

        # Сохраняем ответ ассистента в историю
        await notification_system.save_assistant_response(
            user_id=message.from_user.id, response_text=response_text, metadata=metadata
        )

        # Уведомляем менеджеров в зависимости от типа сообщения
        if message.document:
            # Файл - особый случай
            file_analysis = metadata.get("file_analysis", {}) if metadata else {}
            notified_managers = await notification_system.notify_file_upload(message, file_analysis)
        elif urgency == "high":
            # Высокий приоритет
            reason = (
                metadata.get("priority_reason", "Сложный запрос") if metadata else "Сложный запрос"
            )
            notified_managers = await notification_system.notify_high_priority(message, reason)
        else:
            # Обычное уведомление
            notified_managers = await notification_system.notify_new_client(message, urgency)

        logger.info(
            f"Уведомлено {len(notified_managers)} менеджеров о сообщении от {message.from_user.id}"
        )
        return len(notified_managers) > 0

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения клиента: {e}")
        return False


def _determine_message_urgency(message: types.Message, metadata: Dict) -> str:
    """Определяет приоритет сообщения"""

    # Высокий приоритет для файлов
    if message.document or message.photo:
        return "high"

    # Проверяем метаданные
    if metadata.get("confidence", 0) < 0.7:
        return "high"  # Низкая уверенность = высокий приоритет

    # Проверяем ключевые слова в тексте
    if message.text:
        urgent_keywords = ["срочно", "быстро", "немедленно", "жду", "важно", "критично"]
        text_lower = message.text.lower()

        if any(keyword in text_lower for keyword in urgent_keywords):
            return "high"

        # Вопросы о цене и сроках - средний приоритет
        price_keywords = ["цена", "стоимость", "сколько", "прайс", "расценки"]
        if any(keyword in text_lower for keyword in price_keywords):
            return "normal"

    return "normal"


@manager_router.callback_query(F.data.startswith("manager:"))
async def handle_manager_callbacks(callback: types.CallbackQuery):
    """Обработка callback-ов от менеджеров"""

    if not notification_system:
        await callback.answer("❌ Система не готова", show_alert=True)
        return

    try:
        await notification_system.handle_manager_callback(callback)
    except Exception as e:
        logger.error(f"Ошибка обработки callback от менеджера: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def get_manager_statistics() -> Dict:
    """Получает общую статистику системы менеджеров"""

    try:
        stats = unified_db.get_database_stats()

        # Дополнительная статистика
        all_managers = unified_db._get_all_managers()
        active_managers = unified_db.get_active_managers()
        available_now = unified_db.get_available_managers_now()

        return {
            "total_managers": len(all_managers),
            "active_managers": len(active_managers),
            "available_now": len(available_now),
            "active_chats": stats["active_chats"],
            "total_messages": stats["total_messages"],
            "unique_users": stats["unique_users"],
            "database_path": stats["database_path"],
        }

    except Exception as e:
        logger.error(f"Ошибка получения статистики менеджеров: {e}")
        return {}


# Команды статистики для админов
@manager_router.message(Command("system_stats"))
async def cmd_system_stats(message: types.Message):
    """Показывает статистику системы (только для админов)"""

    if message.from_user.id not in getattr(Config, "ADMIN_USER_IDS", []):
        await message.answer("❌ У вас нет прав доступа к системной статистике")
        return

    try:
        stats = await get_manager_statistics()

        if not stats:
            await message.answer("❌ Ошибка получения статистики")
            return

        stats_text = f"""📊 **Системная статистика**

👥 **Менеджеры:**
• Всего: {stats['total_managers']}
• Активных: {stats['active_managers']}
• Доступных сейчас: {stats['available_now']}

💬 **Диалоги:**
• Активных чатов: {stats['active_chats']}
• Всего сообщений: {stats['total_messages']:,}
• Уникальных пользователей: {stats['unique_users']:,}

💾 **База данных:**
• Путь: `{stats['database_path']}`

🔄 Обновлено: {message.date.strftime('%d.%m.%Y %H:%M')}"""

        await message.answer(stats_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка отображения системной статистики: {e}")
        await message.answer("❌ Ошибка получения статистики")


# Служебные функции для интеграции
async def notify_managers_about_client(
    client_message: types.Message, context: Optional[Dict] = None
) -> List[int]:
    """
    Упрощенный интерфейс для уведомления менеджеров

    Args:
        client_message: Сообщение клиента
        context: Дополнительный контекст

    Returns:
        List[int]: Список ID уведомленных менеджеров
    """
    if not notification_system:
        return []

    try:
        urgency = "normal"
        if context:
            urgency = context.get("urgency", "normal")

        return await notification_system.notify_new_client(client_message, urgency)
    except Exception as e:
        logger.error(f"Ошибка уведомления менеджеров: {e}")
        return []


async def save_conversation_message(
    user_id: int, message_type: str, content: str, metadata: Optional[Dict] = None
) -> int:
    """
    Сохраняет сообщение в историю диалогов

    Args:
        user_id: ID пользователя
        message_type: Тип сообщения ('user', 'assistant', 'system')
        content: Содержимое сообщения
        metadata: Дополнительные метаданные

    Returns:
        int: ID сохраненного сообщения
    """
    try:
        # Создаем объект сообщения
        conv_message = ConversationMessage(
            user_id=user_id,
            message_type=MessageType(message_type),
            content=content,
            category=metadata.get("category") if metadata else None,
            has_upselling=metadata.get("has_upselling", False) if metadata else False,
            search_type=metadata.get("search_type") if metadata else None,
            relevance_score=metadata.get("relevance_score") if metadata else None,
            response_time_ms=metadata.get("response_time_ms") if metadata else None,
            manager_id=metadata.get("manager_id") if metadata else None,
            is_auto_response=metadata.get("is_auto_response", False) if metadata else False,
            file_info=metadata.get("file_info") if metadata else None,
        )

        return unified_db.save_message(conv_message)

    except Exception as e:
        logger.error(f"Ошибка сохранения сообщения в историю: {e}")
        return 0


# Функции для проверки статуса менеджеров
def is_manager_available() -> bool:
    """Проверяет, есть ли доступные менеджеры"""
    try:
        available_managers = unified_db.get_available_managers_now()
        return len(available_managers) > 0
    except:
        return False


def get_available_managers_count() -> int:
    """Возвращает количество доступных менеджеров"""
    try:
        available_managers = unified_db.get_available_managers_now()
        return len(available_managers)
    except:
        return 0


# Middleware для автоматического логирования
class ManagerIntegrationMiddleware:
    """Middleware для интеграции с системой менеджеров"""

    def __init__(self):
        self.enabled = True

    async def __call__(self, handler, event: types.Message, data: Dict):
        """Обрабатывает входящие сообщения"""

        if not self.enabled or not isinstance(event, types.Message):
            return await handler(event, data)

        # Сохраняем пользовательское сообщение
        if event.from_user and event.text:
            try:
                await save_conversation_message(
                    user_id=event.from_user.id,
                    message_type="user",
                    content=event.text,
                    metadata={
                        "message_id": event.message_id,
                        "chat_type": event.chat.type,
                        "has_entities": bool(event.entities),
                    },
                )
            except Exception as e:
                logger.error(f"Ошибка автоматического логирования: {e}")

        # Продолжаем обработку
        return await handler(event, data)


# Функция экспорта для основного бота
def get_manager_router() -> Router:
    """Возвращает роутер системы менеджеров для подключения к основному боту"""
    return manager_router


# Функции инициализации
async def setup_manager_system(bot: Bot) -> bool:
    """
    Полная настройка системы менеджеров

    Args:
        bot: Экземпляр бота

    Returns:
        bool: True если настройка прошла успешно
    """
    try:
        # Инициализация системы уведомлений
        if not initialize_manager_system(bot):
            return False

        logger.info("Система менеджеров полностью настроена")
        return True

    except Exception as e:
        logger.error(f"Ошибка настройки системы менеджеров: {e}")
        return False


# Функции для мониторинга
async def health_check() -> Dict:
    """Проверка состояния системы менеджеров"""

    try:
        # Проверяем базу данных
        db_stats = unified_db.get_database_stats()

        # Проверяем менеджеров
        active_managers = unified_db.get_active_managers()
        available_now = unified_db.get_available_managers_now()

        # Проверяем систему уведомлений
        notification_ready = notification_system is not None

        return {
            "status": "healthy",
            "database_connected": bool(db_stats),
            "total_managers": db_stats.get("managers_total", 0),
            "active_managers": len(active_managers),
            "available_managers": len(available_now),
            "notification_system": notification_ready,
            "active_chats": db_stats.get("active_chats", 0),
            "timestamp": message.date.isoformat() if "message" in locals() else None,
        }

    except Exception as e:
        logger.error(f"Ошибка проверки состояния системы: {e}")
        return {"status": "error", "error": str(e)}
