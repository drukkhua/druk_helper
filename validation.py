"""
Модуль валидации пользовательского ввода
Обеспечивает безопасность и корректность обработки данных от пользователей
"""

import re
import html
from typing import Optional, Tuple, List
from dataclasses import dataclass

from config import logger


@dataclass
class ValidationResult:
    """Результат валидации"""
    is_valid: bool
    cleaned_value: str
    error_message: Optional[str] = None


class InputValidator:
    """Валидатор пользовательского ввода"""
    
    # Константы для валидации
    MIN_SEARCH_LENGTH = 2
    MAX_SEARCH_LENGTH = 100
    MAX_MESSAGE_LENGTH = 4000
    
    # Подозрительные паттерны
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # JavaScript
        r'javascript:',                # JavaScript протокол
        r'on\w+\s*=',                 # Event handlers
        r'<iframe[^>]*>',             # iframes
        r'<object[^>]*>',             # objects
        r'<embed[^>]*>',              # embeds
        r'<link[^>]*>',               # links
        r'<meta[^>]*>',               # meta tags
        r'<style[^>]*>.*?</style>',   # CSS
        r'vbscript:',                 # VBScript
        r'expression\s*\(',           # CSS expressions
        r'@import',                   # CSS imports
        r'&#x[0-9a-fA-F]+;',         # Hex entities
        r'&#[0-9]+;',                 # Decimal entities
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'union\s+select',
        r'drop\s+table',
        r'delete\s+from',
        r'insert\s+into',
        r'update\s+.*set',
        r'alter\s+table',
        r'create\s+table',
        r'exec\s*\(',
        r'script\s*\(',
        r'--\s*$',
        r'/\*.*\*/',
        r';\s*--',
        r'0x[0-9a-fA-F]+',
    ]
    
    # Разрешенные символы для поиска
    ALLOWED_SEARCH_CHARS = re.compile(r'^[a-zA-Zа-яА-ЯёЁії\s\d\-_.,!?()]+$')
    
    def __init__(self):
        self.logger = logger
    
    def validate_search_query(self, query: str) -> ValidationResult:
        """
        Валидация поискового запроса
        
        Args:
            query: Строка поискового запроса
            
        Returns:
            ValidationResult: Результат валидации
        """
        if not query:
            return ValidationResult(
                is_valid=False,
                cleaned_value="",
                error_message="Поисковый запрос не может быть пустым"
            )
        
        # Базовая очистка
        cleaned_query = self._clean_basic_input(query)
        
        # Проверка длины
        if len(cleaned_query) < self.MIN_SEARCH_LENGTH:
            return ValidationResult(
                is_valid=False,
                cleaned_value=cleaned_query,
                error_message=f"Запрос слишком короткий. Минимум {self.MIN_SEARCH_LENGTH} символа"
            )
        
        if len(cleaned_query) > self.MAX_SEARCH_LENGTH:
            return ValidationResult(
                is_valid=False,
                cleaned_value=cleaned_query,
                error_message=f"Запрос слишком длинный. Максимум {self.MAX_SEARCH_LENGTH} символов"
            )
        
        # Проверка на подозрительные паттерны
        security_check = self._check_security_patterns(cleaned_query)
        if not security_check.is_valid:
            return security_check
        
        # Проверка разрешенных символов
        if not self.ALLOWED_SEARCH_CHARS.match(cleaned_query):
            return ValidationResult(
                is_valid=False,
                cleaned_value=cleaned_query,
                error_message="Запрос содержит недопустимые символы"
            )
        
        return ValidationResult(
            is_valid=True,
            cleaned_value=cleaned_query
        )
    
    def validate_callback_data(self, callback_data: str) -> ValidationResult:
        """
        Валидация данных callback-кнопок
        
        Args:
            callback_data: Данные callback
            
        Returns:
            ValidationResult: Результат валидации
        """
        if not callback_data:
            return ValidationResult(
                is_valid=False,
                cleaned_value="",
                error_message="Callback data не может быть пустым"
            )
        
        # Базовая очистка
        cleaned_data = self._clean_basic_input(callback_data)
        
        # Проверка длины (Telegram ограничивает callback_data до 64 байт)
        if len(cleaned_data.encode('utf-8')) > 64:
            return ValidationResult(
                is_valid=False,
                cleaned_value=cleaned_data,
                error_message="Callback data слишком длинный"
            )
        
        # Проверка на подозрительные паттерны
        security_check = self._check_security_patterns(cleaned_data)
        if not security_check.is_valid:
            return security_check
        
        # Проверка формата callback_data (должен содержать только безопасные символы)
        if not re.match(r'^[a-zA-Z0-9_\-]+$', cleaned_data):
            return ValidationResult(
                is_valid=False,
                cleaned_value=cleaned_data,
                error_message="Callback data содержит недопустимые символы"
            )
        
        return ValidationResult(
            is_valid=True,
            cleaned_value=cleaned_data
        )
    
    def validate_user_message(self, message: str) -> ValidationResult:
        """
        Валидация текстовых сообщений от пользователей
        
        Args:
            message: Текст сообщения
            
        Returns:
            ValidationResult: Результат валидации
        """
        if not message:
            return ValidationResult(
                is_valid=False,
                cleaned_value="",
                error_message="Сообщение не может быть пустым"
            )
        
        # Базовая очистка
        cleaned_message = self._clean_basic_input(message)
        
        # Проверка длины
        if len(cleaned_message) > self.MAX_MESSAGE_LENGTH:
            return ValidationResult(
                is_valid=False,
                cleaned_value=cleaned_message,
                error_message=f"Сообщение слишком длинное. Максимум {self.MAX_MESSAGE_LENGTH} символов"
            )
        
        # Проверка на подозрительные паттерны
        security_check = self._check_security_patterns(cleaned_message)
        if not security_check.is_valid:
            return security_check
        
        return ValidationResult(
            is_valid=True,
            cleaned_value=cleaned_message
        )
    
    def validate_user_id(self, user_id: int) -> ValidationResult:
        """
        Валидация ID пользователя
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            ValidationResult: Результат валидации
        """
        if not isinstance(user_id, int):
            return ValidationResult(
                is_valid=False,
                cleaned_value=str(user_id),
                error_message="User ID должен быть числом"
            )
        
        if user_id <= 0:
            return ValidationResult(
                is_valid=False,
                cleaned_value=str(user_id),
                error_message="User ID должен быть положительным числом"
            )
        
        # Telegram user ID не может быть больше 2^53
        if user_id > 9007199254740992:
            return ValidationResult(
                is_valid=False,
                cleaned_value=str(user_id),
                error_message="User ID слишком большой"
            )
        
        return ValidationResult(
            is_valid=True,
            cleaned_value=str(user_id)
        )
    
    def _clean_basic_input(self, text: str) -> str:
        """
        Базовая очистка пользовательского ввода
        
        Args:
            text: Исходный текст
            
        Returns:
            str: Очищенный текст
        """
        if not text:
            return ""
        
        # Удаляем ведущие и завершающие пробелы
        cleaned = text.strip()
        
        # Экранируем HTML
        cleaned = html.escape(cleaned)
        
        # Удаляем множественные пробелы
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Удаляем управляющие символы кроме обычных пробелов и переносов
        cleaned = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned)
        
        return cleaned
    
    def _check_security_patterns(self, text: str) -> ValidationResult:
        """
        Проверка текста на подозрительные паттерны
        
        Args:
            text: Текст для проверки
            
        Returns:
            ValidationResult: Результат проверки
        """
        text_lower = text.lower()
        
        # Проверка XSS паттернов
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                self.logger.warning(f"Обнаружен подозрительный паттерн: {pattern} в тексте: {text[:50]}...")
                return ValidationResult(
                    is_valid=False,
                    cleaned_value=text,
                    error_message="Обнаружен подозрительный контент"
                )
        
        # Проверка SQL injection паттернов
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                self.logger.warning(f"Обнаружен SQL injection паттерн: {pattern} в тексте: {text[:50]}...")
                return ValidationResult(
                    is_valid=False,
                    cleaned_value=text,
                    error_message="Обнаружен подозрительный контент"
                )
        
        return ValidationResult(
            is_valid=True,
            cleaned_value=text
        )
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Очистка имени файла от небезопасных символов
        
        Args:
            filename: Исходное имя файла
            
        Returns:
            str: Безопасное имя файла
        """
        if not filename:
            return "default"
        
        # Удаляем небезопасные символы
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Удаляем точки в начале и конце
        safe_filename = safe_filename.strip('.')
        
        # Ограничиваем длину
        if len(safe_filename) > 100:
            safe_filename = safe_filename[:100]
        
        # Если имя стало пустым, возвращаем default
        if not safe_filename:
            return "default"
        
        return safe_filename


# Глобальный экземпляр валидатора
validator = InputValidator()