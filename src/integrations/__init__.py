"""
Модуль интеграций для внешних сервисов
Содержит интеграции с Google Sheets, веб-хуками и другими системами
"""

from .knowledge_sync import knowledge_sync_service

__all__ = ["knowledge_sync_service"]
