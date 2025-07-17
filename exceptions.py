"""
Кастомные исключения для бота
"""

from typing import Optional, Dict, Any


class BotException(Exception):
    """Базовое исключение для всех ошибок бота"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None):
        super().__init__(message)
        self.details = details or {}
        self.user_id = user_id
        self.timestamp = __import__('datetime').datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для логирования"""
        return {
            'exception_type': self.__class__.__name__,
            'message': str(self),
            'details': self.details,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat()
        }


class ValidationError(BotException):
    """Ошибка валидации пользовательского ввода"""
    pass


class TemplateError(BotException):
    """Ошибки работы с шаблонами"""
    pass


class TemplateNotFoundError(TemplateError):
    """Шаблон не найден"""
    pass


class TemplateLoadError(TemplateError):
    """Ошибка загрузки шаблонов"""
    pass


class DatabaseError(BotException):
    """Ошибки работы с базой данных/файлами"""
    pass


class FileNotFoundError(DatabaseError):
    """Файл не найден"""
    pass


class FilePermissionError(DatabaseError):
    """Нет прав на файл"""
    pass


class ConfigurationError(BotException):
    """Ошибки конфигурации"""
    pass


class TelegramAPIError(BotException):
    """Ошибки Telegram API"""
    pass


class RateLimitExceededError(BotException):
    """Превышен лимит запросов"""
    pass


class SecurityError(BotException):
    """Ошибки безопасности"""
    pass


class ExternalAPIError(BotException):
    """Ошибки внешних API (Google Sheets и т.д.)"""
    pass


class StatisticsError(BotException):
    """Ошибки работы со статистикой"""
    pass


class StateError(BotException):
    """Ошибки состояния FSM"""
    pass


class UserNotFoundError(BotException):
    """Пользователь не найден"""
    pass


class AdminOnlyError(BotException):
    """Доступ только для администраторов"""
    pass