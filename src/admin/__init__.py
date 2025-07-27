"""
Модуль административных функций
Содержит инструменты для управления ботом администраторами
"""

from .quick_corrections import quick_corrections_service
from .knowledge_base_manager import knowledge_base_manager

__all__ = ["quick_corrections_service", "knowledge_base_manager"]
