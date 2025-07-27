"""
Система уведомлений для менеджеров
Интегрирована с объединенной SQLite базой данных
"""

from aiogram import Bot, types
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from typing import List, Dict, Optional
import logging
import json
from datetime import datetime

from src.managers.models import unified_db, Manager, ManagerStatus, ConversationMessage, MessageType
from config import Config

logger = logging.getLogger(__name__)


class ManagerNotificationSystem:
    """Система уведомлений для менеджеров"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = unified_db

    async def notify_new_client(
        self, client_message: types.Message, urgency: str = "normal"
    ) -> List[int]:
        """Уведомляет доступных менеджеров о новом клиенте"""

        # Получаем доступных менеджеров
        available_managers = self.db.get_available_managers_now()

        if not available_managers:
            # Никого нет в рабочее время - уведомляем всех активных
            available_managers = self.db.get_active_managers()
            urgency = "after_hours"  # Помечаем как внерабочее время

        if not available_managers:
            logger.warning("Нет доступных менеджеров для уведомления")
            return []

        # Информация о клиенте
        client_info = self._extract_client_info(client_message)

        # Сохраняем сообщение клиента в историю
        await self._save_client_message(client_info, client_message)

        # Формируем уведомление
        notification = self._create_notification_message(client_info, urgency)
        keyboard = self._create_manager_keyboard(client_info["telegram_id"])

        notified_managers = []

        # Отправляем уведомления
        for manager in available_managers:
            try:
                await self.bot.send_message(
                    chat_id=manager.telegram_id,
                    text=notification,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                notified_managers.append(manager.telegram_id)
                logger.info(f"Уведомлен менеджер {manager.name} ({manager.telegram_id})")

            except (TelegramBadRequest, TelegramForbiddenError) as e:
                logger.error(f"Ошибка отправки уведомления менеджеру {manager.telegram_id}: {e}")
                # Менеджер заблокировал бота - помечаем как неактивного
                self.db.update_manager_status(manager.telegram_id, ManagerStatus.OFFLINE)

        return notified_managers

    async def notify_file_upload(
        self, client_message: types.Message, file_analysis: Dict
    ) -> List[int]:
        """Уведомляет менеджеров о загрузке файла"""

        available_managers = self.db.get_available_managers_now()
        client_info = self._extract_client_info(client_message)

        # Сохраняем информацию о файле
        await self._save_file_message(client_info, client_message, file_analysis)

        # Специальное уведомление для файлов
        notification = self._create_file_notification(client_info, file_analysis)
        keyboard = self._create_manager_keyboard(client_info["telegram_id"])

        notified_managers = []

        for manager in available_managers:
            try:
                await self.bot.send_message(
                    chat_id=manager.telegram_id,
                    text=notification,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                notified_managers.append(manager.telegram_id)

            except Exception as e:
                logger.error(f"Ошибка отправки уведомления о файле: {e}")

        return notified_managers

    async def notify_high_priority(self, client_message: types.Message, reason: str) -> List[int]:
        """Уведомляет всех активных менеджеров о высокоприоритетном клиенте"""

        all_active = self.db.get_active_managers()
        client_info = self._extract_client_info(client_message)

        # Сохраняем приоритетное сообщение
        await self._save_priority_message(client_info, client_message, reason)

        notification = f"""🚨 **ПРИОРИТЕТНЫЙ КЛИЕНТ**

{self._create_notification_message(client_info, "high")}

⚠️ **Причина приоритета:** {reason}
"""

        keyboard = self._create_manager_keyboard(client_info["telegram_id"])

        notified_managers = []

        for manager in all_active:
            try:
                await self.bot.send_message(
                    chat_id=manager.telegram_id,
                    text=notification,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                notified_managers.append(manager.telegram_id)

            except Exception as e:
                logger.error(f"Ошибка приоритетного уведомления: {e}")

        return notified_managers

    async def notify_client_taken(self, client_id: int, manager_name: str, manager_id: int):
        """Уведомляет других менеджеров, что клиент взят в работу"""

        active_managers = self.db.get_active_managers()

        for manager in active_managers:
            if manager.telegram_id == manager_id:
                continue  # Не уведомляем самого менеджера

            try:
                await self.bot.send_message(
                    manager.telegram_id,
                    f"ℹ️ **Клиент взят в работу**\n\n"
                    f"👤 Клиент ID: `{client_id}`\n"
                    f"👨‍💼 Менеджер: {manager_name}\n"
                    f"🕐 Время: {datetime.now().strftime('%H:%M')}",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning(f"Ошибка отправки массового уведомления: {e}")
                # Игнорируем ошибки массовых уведомлений, но логируем их

    def _extract_client_info(self, message: types.Message) -> Dict:
        """Извлекает информацию о клиенте"""
        user = message.from_user

        return {
            "telegram_id": user.id,
            "name": user.full_name or "Без имени",
            "username": f"@{user.username}" if user.username else "Без username",
            "query": message.text or message.caption or "[файл/медиа]",
            "message_time": message.date.strftime("%H:%M"),
            "message_date": message.date.strftime("%d.%m.%Y"),
            "language_code": user.language_code or "uk",
            "message_id": message.message_id,
        }

    async def _save_client_message(self, client_info: Dict, message: types.Message):
        """Сохраняет сообщение клиента в историю"""
        try:
            conv_message = ConversationMessage(
                user_id=client_info["telegram_id"],
                message_type=MessageType.USER,
                content=client_info["query"],
                timestamp=message.date,
                category=self._detect_message_category(client_info["query"]),
                file_info=(
                    self._extract_file_info(message) if message.document or message.photo else None
                ),
            )

            self.db.save_message(conv_message)
            logger.info(f"Сохранено сообщение пользователя {client_info['telegram_id']}")

        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения клиента: {e}")

    async def _save_file_message(
        self, client_info: Dict, message: types.Message, file_analysis: Dict
    ):
        """Сохраняет информацию о загруженном файле"""
        try:
            file_info = {
                "file_name": file_analysis.get("file_name", "unknown"),
                "file_size": file_analysis.get("file_size", 0),
                "file_extension": file_analysis.get("file_extension", ""),
                "file_type": file_analysis.get("file_type", "unknown"),
                "quality_assessment": file_analysis.get("quality_assessment", "unknown"),
                "suitable_for_print": file_analysis.get("suitable_for_print", False),
            }

            conv_message = ConversationMessage(
                user_id=client_info["telegram_id"],
                message_type=MessageType.USER,
                content=f"Загружен файл: {file_info['file_name']}",
                timestamp=message.date,
                category="файлы",
                file_info=json.dumps(file_info, ensure_ascii=False),
            )

            self.db.save_message(conv_message)
            logger.info(
                f"Сохранена информация о файле от пользователя {client_info['telegram_id']}"
            )

        except Exception as e:
            logger.error(f"Ошибка сохранения информации о файле: {e}")

    async def _save_priority_message(self, client_info: Dict, message: types.Message, reason: str):
        """Сохраняет приоритетное сообщение"""
        try:
            conv_message = ConversationMessage(
                user_id=client_info["telegram_id"],
                message_type=MessageType.USER,
                content=client_info["query"],
                timestamp=message.date,
                category="приоритет",
                file_info=json.dumps({"priority_reason": reason}, ensure_ascii=False),
            )

            self.db.save_message(conv_message)

        except Exception as e:
            logger.error(f"Ошибка сохранения приоритетного сообщения: {e}")

    def _detect_message_category(self, message_text: str) -> Optional[str]:
        """Определяет категорию сообщения по содержимому"""
        if not message_text:
            return None

        text_lower = message_text.lower()

        # Простая категоризация по ключевым словам
        if any(word in text_lower for word in ["цена", "стоимость", "сколько стоит", "прайс"]):
            return "цены"
        elif any(word in text_lower for word in ["срок", "когда готово", "быстро", "срочно"]):
            return "сроки"
        elif any(word in text_lower for word in ["макет", "дизайн", "файл"]):
            return "макеты"
        elif any(word in text_lower for word in ["материал", "бумага", "качество"]):
            return "материалы"
        elif any(word in text_lower for word in ["визитки", "визитка"]):
            return "визитки"
        elif any(word in text_lower for word in ["листовки", "листовка"]):
            return "листовки"
        elif any(word in text_lower for word in ["наклейки", "наклейка"]):
            return "наклейки"
        else:
            return "общие"

    def _extract_file_info(self, message: types.Message) -> Optional[str]:
        """Извлекает информацию о файлах из сообщения"""
        if message.document:
            return json.dumps(
                {
                    "type": "document",
                    "file_name": message.document.file_name,
                    "file_size": message.document.file_size,
                    "mime_type": message.document.mime_type,
                },
                ensure_ascii=False,
            )
        elif message.photo:
            photo = message.photo[-1]  # Берем самое большое фото
            return json.dumps(
                {
                    "type": "photo",
                    "file_size": photo.file_size,
                    "width": photo.width,
                    "height": photo.height,
                },
                ensure_ascii=False,
            )

        return None

    def _create_notification_message(self, client_info: Dict, urgency: str = "normal") -> str:
        """Создает текст уведомления"""

        urgency_config = {
            "low": {"emoji": "📝", "title": "Новое сообщение"},
            "normal": {"emoji": "📞", "title": "Новый клиент ждет ответ!"},
            "high": {"emoji": "🚨", "title": "СРОЧНО! Клиент ждет ответ!"},
            "urgent": {"emoji": "🔥", "title": "КРИТИЧЕСКИ ВАЖНО!"},
            "after_hours": {"emoji": "🌙", "title": "Сообщение во внерабочее время"},
        }

        config = urgency_config.get(urgency, urgency_config["normal"])
        emoji = config["emoji"]
        title = config["title"]

        # Обрезаем длинный запрос
        query = client_info["query"]
        if len(query) > 100:
            query = query[:97] + "..."

        # Получаем краткую статистику клиента
        client_stats = self._get_client_brief_stats(client_info["telegram_id"])

        base_message = f"""{emoji} **{title}**

👤 **Клиент:** {client_info['name']}
📱 **Username:** {client_info['username']}
🆔 **ID:** `{client_info['telegram_id']}`

💬 **Сообщение:**
_{query}_

🕐 **Время:** {client_info['message_time']}"""

        # Добавляем статистику клиента если есть история
        if client_stats["total_messages"] > 1:
            base_message += f"\n\n📊 **Статистика клиента:**"
            base_message += f"\n• Всего сообщений: {client_stats['total_messages']}"
            if client_stats["last_interaction"]:
                base_message += f"\n• Последнее обращение: {client_stats['last_interaction']}"
            if client_stats["favorite_category"]:
                base_message += f"\n• Чаще спрашивает о: {client_stats['favorite_category']}"

        if urgency == "after_hours":
            base_message += f"\n\n🌙 _Сообщение получено во внерабочее время_"

        base_message += f'\n\n⚡ **Нажмите "Ответить" для перехода к диалогу**'

        return base_message

    def _get_client_brief_stats(self, client_id: int) -> Dict:
        """Получает краткую статистику клиента"""
        try:
            stats = self.db.get_user_stats_summary(client_id)

            last_interaction = None
            if stats.get("last_message"):
                last_dt = datetime.fromisoformat(stats["last_message"])
                # Если последнее сообщение не сегодняшнее
                if last_dt.date() != datetime.now().date():
                    last_interaction = last_dt.strftime("%d.%m")

            return {
                "total_messages": stats.get("total_messages", 0),
                "last_interaction": last_interaction,
                "favorite_category": stats.get("top_category", None),
            }
        except:
            return {"total_messages": 0, "last_interaction": None, "favorite_category": None}

    def _create_file_notification(self, client_info: Dict, file_analysis: Dict) -> str:
        """Создает уведомление о загрузке файла"""

        quality_emoji = {"excellent": "🌟", "good": "✅", "medium": "⚠️", "needs_check": "🔍"}

        quality = file_analysis.get("quality_assessment", "unknown")
        quality_icon = quality_emoji.get(quality, "❓")

        return f"""📁 **Клиент загрузил макет!**

👤 **Клиент:** {client_info['name']}
📱 **Username:** {client_info['username']}
🆔 **ID:** `{client_info['telegram_id']}`

📋 **Анализ файла:**
• **Название:** {file_analysis.get('file_name', 'unknown')}
• **Размер:** {file_analysis.get('file_size_mb', 0)} МБ
• **Формат:** {file_analysis.get('file_extension', 'unknown')} ({file_analysis.get('file_type', 'unknown')})
• **Качество для печати:** {quality_icon} {quality}
• **Подходит для полиграфии:** {'✅ Да' if file_analysis.get('suitable_for_print', False) else '❌ Нет'}

🕐 **Время:** {client_info['message_time']}

✅ **Клиенту уже отправлен автоответ о проверке файла**"""

    def _create_manager_keyboard(self, client_telegram_id: int) -> types.InlineKeyboardMarkup:
        """Создает клавиатуру для менеджера"""

        return types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="💬 Ответить клиенту", url=f"tg://user?id={client_telegram_id}"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="✅ Взял в работу", callback_data=f"manager:take:{client_telegram_id}"
                    ),
                    types.InlineKeyboardButton(
                        text="📊 История клиента",
                        callback_data=f"manager:history:{client_telegram_id}",
                    ),
                ],
                [
                    types.InlineKeyboardButton(
                        text="📈 Статистика клиента",
                        callback_data=f"manager:stats:{client_telegram_id}",
                    ),
                    types.InlineKeyboardButton(text="🔇 Пауза 1ч", callback_data="manager:mute:60"),
                ],
            ]
        )

    async def handle_manager_callback(self, callback: types.CallbackQuery):
        """Обрабатывает callback от менеджеров"""

        data_parts = callback.data.split(":")
        action = data_parts[1]

        if action == "take":
            client_id = int(data_parts[2])
            await self._handle_take_client(callback, client_id)

        elif action == "history":
            client_id = int(data_parts[2])
            await self._show_client_history(callback, client_id)

        elif action == "stats":
            client_id = int(data_parts[2])
            await self._show_client_stats(callback, client_id)

        elif action == "mute":
            minutes = int(data_parts[2])
            await self._mute_notifications(callback, minutes)

    async def _handle_take_client(self, callback: types.CallbackQuery, client_id: int):
        """Обрабатывает взятие клиента в работу"""

        manager_id = callback.from_user.id
        manager_name = callback.from_user.full_name

        try:
            # Проверяем, есть ли уже активный чат
            existing_chat = self.db.get_active_chat(client_id)
            if existing_chat and existing_chat.status == "active":
                await callback.answer(
                    f"⚠️ Клиент уже обслуживается менеджером ID {existing_chat.manager_telegram_id}",
                    show_alert=True,
                )
                return

            # Назначаем чат менеджеру
            chat_id = self.db.assign_chat_to_manager(
                client_id, manager_id, {"name": manager_name, "query": "Взят из уведомления"}
            )

            # Обновляем сообщение менеджера
            await callback.message.edit_text(
                f"✅ **Клиент взят в работу!**\n\n"
                f"🆔 Чат ID: {chat_id}\n"
                f"👨‍💼 Менеджер: {manager_name}\n"
                f"👤 Клиент ID: `{client_id}`\n"
                f"🕐 Время: {datetime.now().strftime('%H:%M')}\n\n"
                f"💬 Переходите к диалогу и отвечайте клиенту.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text="💬 Перейти к диалогу", url=f"tg://user?id={client_id}"
                            )
                        ],
                        [
                            types.InlineKeyboardButton(
                                text="✅ Завершить чат",
                                callback_data=f"manager:complete:{client_id}",
                            )
                        ],
                    ]
                ),
                parse_mode="Markdown",
            )

            # Уведомляем других менеджеров
            await self.notify_client_taken(client_id, manager_name, manager_id)

            logger.info(
                f"Клиент {client_id} взят в работу менеджером {manager_name} ({manager_id})"
            )

        except Exception as e:
            logger.error(f"Ошибка при взятии клиента в работу: {e}")
            await callback.answer("❌ Ошибка. Попробуйте еще раз.", show_alert=True)

    async def _show_client_history(self, callback: types.CallbackQuery, client_id: int):
        """Показывает историю клиента"""

        try:
            # Получаем последние сообщения клиента
            history = self.db.get_user_history(client_id, limit=10)

            if not history:
                await callback.answer("📭 У клиента нет истории сообщений", show_alert=True)
                return

            history_text = f"📋 **История клиента ID: {client_id}**\n\n"

            for i, msg in enumerate(history[:5], 1):
                date_str = msg.timestamp.strftime("%d.%m %H:%M")
                content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content

                msg_type = "❓" if msg.message_type == MessageType.USER else "✅"
                history_text += f"{msg_type} **{date_str}**\n_{content_preview}_\n\n"

            if len(history) > 5:
                history_text += f"... и еще {len(history) - 5} сообщений"

            await callback.answer(history_text, show_alert=True)

        except Exception as e:
            logger.error(f"Ошибка получения истории клиента {client_id}: {e}")
            await callback.answer("❌ Ошибка загрузки истории клиента", show_alert=True)

    async def _show_client_stats(self, callback: types.CallbackQuery, client_id: int):
        """Показывает статистику клиента"""

        try:
            stats = self.db.get_user_stats_summary(client_id)

            stats_text = f"📊 **Статистика клиента ID: {client_id}**\n\n"
            stats_text += f"📈 Всего сообщений: {stats['total_messages']}\n"
            stats_text += f"❓ Вопросов: {stats['user_messages']}\n"
            stats_text += f"✅ Ответов: {stats['assistant_messages']}\n"
            stats_text += f"💰 С upselling: {stats['upselling_messages']}\n"
            stats_text += f"🤖 Автоответов: {stats['auto_responses']}\n"

            if stats["first_message"]:
                first_date = datetime.fromisoformat(stats["first_message"]).strftime("%d.%m.%Y")
                stats_text += f"\n📅 Первое обращение: {first_date}\n"

            stats_text += f"🎯 Интересуется: {stats['top_category']}"

            await callback.answer(stats_text, show_alert=True)

        except Exception as e:
            logger.error(f"Ошибка получения статистики клиента {client_id}: {e}")
            await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)

    async def _mute_notifications(self, callback: types.CallbackQuery, minutes: int):
        """Отключает уведомления для менеджера"""

        manager_id = callback.from_user.id

        try:
            # Временно помечаем менеджера как занятого
            self.db.update_manager_status(manager_id, ManagerStatus.BUSY)

            # Здесь можно добавить логику автоматического восстановления статуса через N минут
            # Например, через задачи в фоне или Redis с TTL

            await callback.answer(
                f"🔇 Уведомления приостановлены на {minutes} минут.\n"
                f"Используйте /manager_status для возобновления.",
                show_alert=True,
            )

        except Exception as e:
            logger.error(f"Ошибка отключения уведомлений: {e}")
            await callback.answer("❌ Ошибка", show_alert=True)

    async def save_assistant_response(
        self, user_id: int, response_text: str, metadata: Optional[Dict] = None
    ) -> int:
        """Сохраняет ответ ассистента в историю"""
        try:
            if metadata is None:
                metadata = {}

            conv_message = ConversationMessage(
                user_id=user_id,
                message_type=MessageType.ASSISTANT,
                content=response_text,
                category=metadata.get("category"),
                has_upselling=metadata.get("has_upselling", False),
                search_type=metadata.get("search_type"),
                relevance_score=metadata.get("relevance_score"),
                response_time_ms=metadata.get("response_time_ms"),
                manager_id=metadata.get("manager_id"),
                is_auto_response=metadata.get("is_auto_response", False),
            )

            message_id = self.db.save_message(conv_message)
            logger.info(f"Сохранен ответ ассистента для пользователя {user_id}")
            return message_id

        except Exception as e:
            logger.error(f"Ошибка сохранения ответа ассистента: {e}")
            return 0


# Функция для создания глобального экземпляра
def create_notification_system(bot: Bot) -> ManagerNotificationSystem:
    return ManagerNotificationSystem(bot)
