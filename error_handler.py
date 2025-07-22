"""
Система обработки ошибок для бота
"""

import traceback
from functools import wraps

import json
from aiogram import types
from aiogram.exceptions import TelegramAPIError as AiogramTelegramAPIError
from aiogram.types import CallbackQuery, Message
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from config import ADMIN_USER_IDS, logger
from exceptions import *


class ErrorHandler:
    """Обработчик ошибок бота"""

    def __init__(self) -> None:
        self.error_stats = {}
        self.error_log_file = "error_log.json"

    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Логирование ошибки

        Args:
            error: Исключение
            context: Контекст ошибки
        """
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
        }

        # Логируем в файл
        try:
            with open(self.error_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Не удалось записать в лог ошибок: {e}")

        # Логируем в консоль
        logger.error(f"Error: {error_data}")

        # Обновляем статистику
        error_type = type(error).__name__
        if error_type not in self.error_stats:
            self.error_stats[error_type] = 0
        self.error_stats[error_type] += 1

    async def handle_error(self, error: Exception, update: Optional[types.Update] = None) -> None:
        """
        Обработка ошибки с отправкой уведомления пользователю

        Args:
            error: Исключение
            update: Обновление Telegram
        """
        context = {}
        user_id = None

        # Извлекаем контекст из update
        if update:
            if update.message:
                user_id = update.message.from_user.id
                context["message_text"] = update.message.text
                context["chat_id"] = update.message.chat.id
            elif update.callback_query:
                user_id = update.callback_query.from_user.id
                context["callback_data"] = update.callback_query.data
                context["chat_id"] = update.callback_query.message.chat.id

        context["user_id"] = user_id

        # Логируем ошибку
        self.log_error(error, context)

        # Отправляем уведомление пользователю
        await self._send_user_notification(error, update, user_id)

        # Отправляем уведомление админам о критических ошибках
        if isinstance(error, (DatabaseError, ConfigurationError, ExternalAPIError)):
            await self._send_admin_notification(error, context)

    async def _send_user_notification(
        self, error: Exception, update: Optional[types.Update], user_id: Optional[int]
    ) -> None:
        """Отправка уведомления пользователю"""
        if not update:
            return

        # Определяем тип ошибки и сообщение
        if isinstance(error, ValidationError):
            message = "❌ Некорректные данные. Попробуйте еще раз."
        elif isinstance(error, TemplateNotFoundError):
            message = "❌ Шаблон не найден. Обратитесь к администратору."
        elif isinstance(error, RateLimitExceededError):
            message = "⏰ Слишком много запросов. Подождите немного."
        elif isinstance(error, AdminOnlyError):
            message = "🔒 Доступ только для администраторов."
        elif isinstance(error, SecurityError):
            message = "🛡️ Обнаружена подозрительная активность."
        elif isinstance(error, (DatabaseError, FileNotFoundError)):
            message = "📂 Ошибка доступа к данным. Попробуйте позже."
        elif isinstance(error, ExternalAPIError):
            message = "🌐 Проблема с внешним сервисом. Попробуйте позже."
        elif isinstance(error, TelegramAPIError):
            message = "📱 Ошибка Telegram API. Попробуйте позже."
        else:
            message = "❌ Произошла ошибка. Попробуйте еще раз."

        try:
            if update.message:
                await update.message.answer(message)
            elif update.callback_query:
                await update.callback_query.answer(message)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление пользователю: {e}")

    async def _send_admin_notification(self, error: Exception, context: Dict[str, Any]) -> None:
        """Отправка уведомления админам о критических ошибках"""
        if not ADMIN_USER_IDS:
            return

        error_message = (
            f"🚨 Критическая ошибка бота:\n\n"
            f"**Тип:** {type(error).__name__}\n"
            f"**Сообщение:** {str(error)}\n"
            f"**Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**Пользователь:** {context.get('user_id', 'Неизвестно')}\n"
            f"**Контекст:** {json.dumps(context, ensure_ascii=False, indent=2)}"
        )

        # Здесь можно добавить отправку уведомления админам
        # Например, через отдельный бот или webhook
        logger.critical(f"Admin notification: {error_message}")

    def get_error_stats(self) -> Dict[str, int]:
        """Получить статистику ошибок"""
        return self.error_stats.copy()

    def clear_error_stats(self) -> None:
        """Очистить статистику ошибок"""
        self.error_stats.clear()


# Глобальный обработчик ошибок
error_handler = ErrorHandler()


def handle_exceptions(func: Callable) -> Callable:
    """
    Декоратор для автоматической обработки исключений
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BotException as e:
            # Обрабатываем наши кастомные исключения
            update = None
            for arg in args:
                if isinstance(arg, (Message, CallbackQuery)):
                    update = (
                        types.Update(message=arg)
                        if isinstance(arg, Message)
                        else types.Update(callback_query=arg)
                    )
                    break

            await error_handler.handle_error(e, update)

        except AiogramTelegramAPIError as e:
            # Обрабатываем ошибки Telegram API
            telegram_error = TelegramAPIError(
                f"Telegram API Error: {str(e)}", details={"original_error": str(e)}
            )

            update = None
            for arg in args:
                if isinstance(arg, (Message, CallbackQuery)):
                    update = (
                        types.Update(message=arg)
                        if isinstance(arg, Message)
                        else types.Update(callback_query=arg)
                    )
                    break

            await error_handler.handle_error(telegram_error, update)

        except Exception as e:
            # Обрабатываем все остальные исключения
            generic_error = BotException(
                f"Unexpected error: {str(e)}",
                details={"original_error": str(e), "traceback": traceback.format_exc()},
            )

            update = None
            for arg in args:
                if isinstance(arg, (Message, CallbackQuery)):
                    update = (
                        types.Update(message=arg)
                        if isinstance(arg, Message)
                        else types.Update(callback_query=arg)
                    )
                    break

            await error_handler.handle_error(generic_error, update)

    return wrapper


def safe_execute(func: Callable, *args, **kwargs) -> Any:
    """
    Безопасное выполнение функции с логированием ошибок
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_handler.log_error(
            e, {"function": func.__name__, "args": str(args), "kwargs": str(kwargs)}
        )
        return None


class CircuitBreaker:
    """
    Паттерн Circuit Breaker для защиты от каскадных ошибок
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs):
        """Вызов функции через Circuit Breaker"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise ExternalAPIError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Проверка, стоит ли попытаться сбросить состояние"""
        if self.last_failure_time is None:
            return True

        return (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout

    def _on_success(self) -> None:
        """Обработка успешного вызова"""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self) -> None:
        """Обработка неудачного вызова"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# Глобальный Circuit Breaker для внешних API
external_api_circuit_breaker = CircuitBreaker()


def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """Декоратор для использования Circuit Breaker"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator
