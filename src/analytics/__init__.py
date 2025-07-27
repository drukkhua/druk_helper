"""
Модуль аналитики для AI бота
Собирает данные о запросах пользователей и эффективности ответов
"""

from .analytics_service import analytics_service
from .models import analytics_db, UserQuery, FeedbackEntry, KnowledgeGap
from .dashboard import dashboard, create_simple_report

__all__ = [
    "analytics_service",
    "analytics_db",
    "UserQuery",
    "FeedbackEntry",
    "KnowledgeGap",
    "dashboard",
    "create_simple_report",
]
