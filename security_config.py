"""
Конфигурация безопасности
"""

from dataclasses import dataclass

from typing import Any, Dict, List


@dataclass
class SecurityConfig:
    """Настройки безопасности"""

    # Лимиты валидации
    MIN_SEARCH_LENGTH: int = 2
    MAX_SEARCH_LENGTH: int = 100
    MAX_MESSAGE_LENGTH: int = 4000
    MAX_CALLBACK_DATA_LENGTH: int = 64

    # Rate limiting
    DEFAULT_RATE_LIMIT: int = 30  # запросов в минуту
    SEARCH_RATE_LIMIT: int = 15  # поисковых запросов в минуту
    ADMIN_RATE_LIMIT: int = 5  # запросов админов в минуту

    # Блокировка подозрительных паттернов
    ENABLE_XSS_PROTECTION: bool = True
    ENABLE_SQL_INJECTION_PROTECTION: bool = True
    ENABLE_PATH_TRAVERSAL_PROTECTION: bool = True

    # Логирование безопасности
    LOG_FAILED_VALIDATIONS: bool = True
    LOG_RATE_LIMIT_VIOLATIONS: bool = True
    LOG_SECURITY_INCIDENTS: bool = True

    # Автоматическая блокировка
    ENABLE_AUTO_BLOCK: bool = False
    AUTO_BLOCK_THRESHOLD: int = 10  # нарушений до блокировки
    AUTO_BLOCK_DURATION: int = 3600  # секунд

    # Разрешенные домены для ссылок (если потребуется)
    ALLOWED_DOMAINS: List[str] = None  # type: ignore

    # Максимальные значения для защиты от DoS
    MAX_CONCURRENT_REQUESTS: int = 100
    MAX_MEMORY_USAGE_MB: int = 256

    def __post_init__(self) -> None:
        if self.ALLOWED_DOMAINS is None:
            self.ALLOWED_DOMAINS = ["t.me", "telegram.org", "docs.google.com"]


# Глобальная конфигурация безопасности
security_config = SecurityConfig()


def get_security_config() -> SecurityConfig:
    """Получить конфигурацию безопасности"""
    return security_config


def update_security_config(**kwargs: Any) -> None:
    """Обновить конфигурацию безопасности"""
    for key, value in kwargs.items():
        if hasattr(security_config, key):
            setattr(security_config, key, value)
        else:
            raise ValueError(f"Неизвестная настройка безопасности: {key}")


# Настройки для разработки (менее строгие)
def enable_dev_mode() -> None:
    """Включить режим разработки с менее строгими настройками"""
    update_security_config(
        DEFAULT_RATE_LIMIT=100,
        SEARCH_RATE_LIMIT=50,
        ADMIN_RATE_LIMIT=20,
        ENABLE_AUTO_BLOCK=False,
        LOG_FAILED_VALIDATIONS=False,
    )


# Настройки для продакшена (более строгие)
def enable_production_mode() -> None:
    """Включить продакшн режим с более строгими настройками"""
    update_security_config(
        DEFAULT_RATE_LIMIT=20,
        SEARCH_RATE_LIMIT=10,
        ADMIN_RATE_LIMIT=3,
        ENABLE_AUTO_BLOCK=True,
        LOG_FAILED_VALIDATIONS=True,
        LOG_RATE_LIMIT_VIOLATIONS=True,
        LOG_SECURITY_INCIDENTS=True,
    )
