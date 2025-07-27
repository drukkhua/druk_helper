"""
Сервис синхронизации базы знаний с Google Sheets
Интегрирует существующий Google Sheets updater с системой аналитики и ChromaDB
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Импортируем существующий Google Sheets updater
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from google_sheets_updater import sheets_updater

from src.ai.knowledge_base import knowledge_base
from src.analytics.analytics_service import analytics_service

logger = logging.getLogger(__name__)


class KnowledgeSyncService:
    """Сервис для синхронизации базы знаний с Google Sheets"""

    def __init__(self):
        self.sheets_updater = sheets_updater
        self.knowledge_base = knowledge_base
        self.analytics = analytics_service

        # URL нашей Google Таблицы (можно вынести в .env)
        self.default_spreadsheet_url = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit?usp=sharing"

        # Статистика последней синхронизации
        self.last_sync_time: Optional[datetime] = None
        self.last_sync_success: bool = False
        self.last_sync_changes: int = 0

        logger.info("Knowledge Sync Service инициализирован")

    async def full_sync_knowledge_base(
        self, spreadsheet_url: Optional[str] = None, force_reload: bool = False
    ) -> Dict:
        """
        Полная синхронизация базы знаний

        Args:
            spreadsheet_url: URL Google Таблицы (если None - используется по умолчанию)
            force_reload: Принудительно перезагрузить ChromaDB

        Returns:
            Результат синхронизации с метриками
        """
        start_time = time.time()
        result = {
            "success": False,
            "changes": 0,
            "errors": [],
            "duration_ms": 0,
            "csv_files_updated": 0,
            "chromadb_updated": False,
            "analytics_recorded": False,
        }

        try:
            logger.info("🔄 Начинаем полную синхронизацию базы знаний...")

            # 1. Обновляем CSV файлы из Google Sheets
            csv_update_result = await self._update_csv_files(spreadsheet_url)
            result["csv_files_updated"] = csv_update_result["files_updated"]

            if not csv_update_result["success"]:
                result["errors"].append("Не удалось обновить CSV файлы")
                return result

            # 2. Перезагружаем ChromaDB если есть изменения или принудительно
            if csv_update_result["files_updated"] > 0 or force_reload:
                chromadb_result = await self._reload_chromadb()
                result["chromadb_updated"] = chromadb_result["success"]

                if not chromadb_result["success"]:
                    result["errors"].append("Не удалось обновить ChromaDB")
                    return result
            else:
                logger.info("📋 ChromaDB не требует обновления")
                result["chromadb_updated"] = True

            # 3. Записываем в аналитику
            analytics_result = self._record_sync_analytics(result)
            result["analytics_recorded"] = analytics_result

            # Обновляем статистику
            self.last_sync_time = datetime.now()
            self.last_sync_success = True
            self.last_sync_changes = result["csv_files_updated"]

            result["success"] = True
            result["changes"] = csv_update_result["files_updated"]

            duration_ms = int((time.time() - start_time) * 1000)
            result["duration_ms"] = duration_ms

            logger.info(
                f"✅ Синхронизация завершена за {duration_ms}ms. Обновлено файлов: {result['changes']}"
            )

        except Exception as e:
            logger.error(f"❌ Ошибка при синхронизации базы знаний: {e}")
            result["errors"].append(str(e))
            self.last_sync_success = False

        return result

    async def _update_csv_files(self, spreadsheet_url: Optional[str] = None) -> Dict:
        """Обновляет CSV файлы из Google Sheets"""
        result = {"success": False, "files_updated": 0}

        try:
            url = spreadsheet_url or self.default_spreadsheet_url
            logger.info(f"📊 Обновляем CSV файлы из Google Sheets: {url[:50]}...")

            # Запоминаем время последней модификации файлов
            original_mtimes = self._get_csv_file_mtimes()

            # Обновляем файлы через существующий сервис
            success = await self.sheets_updater.update_templates_from_google_sheets(url)

            if success:
                # Подсчитываем количество изменившихся файлов
                new_mtimes = self._get_csv_file_mtimes()
                files_updated = sum(
                    1
                    for filename, mtime in new_mtimes.items()
                    if filename not in original_mtimes or original_mtimes[filename] != mtime
                )

                result["success"] = True
                result["files_updated"] = files_updated
                logger.info(f"📊 Обновлено CSV файлов: {files_updated}")
            else:
                logger.warning("⚠️ Обновление CSV файлов завершилось неуспешно")

        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении CSV файлов: {e}")

        return result

    async def _reload_chromadb(self) -> Dict:
        """Перезагружает ChromaDB с новыми данными"""
        result = {"success": False, "documents_loaded": 0}

        try:
            logger.info("🔄 Перезагружаем ChromaDB...")

            # Принудительно перезагружаем векторную базу знаний
            success = await asyncio.to_thread(
                self.knowledge_base.populate_vector_store, force_reload=True
            )

            if success:
                # Получаем статистику
                stats = self.knowledge_base.get_statistics()
                result["success"] = True
                result["documents_loaded"] = stats.get("total_documents", 0)
                logger.info(f"🔄 ChromaDB перезагружена: {result['documents_loaded']} документов")
            else:
                logger.warning("⚠️ Не удалось перезагрузить ChromaDB")

        except Exception as e:
            logger.error(f"❌ Ошибка при перезагрузке ChromaDB: {e}")

        return result

    def _get_csv_file_mtimes(self) -> Dict[str, float]:
        """Получает время последней модификации CSV файлов"""
        mtimes = {}
        data_dir = "./data"

        for file_path in self.sheets_updater.csv_paths.values():
            filename = os.path.basename(file_path)
            try:
                if os.path.exists(file_path):
                    mtimes[filename] = os.path.getmtime(file_path)
            except OSError:
                pass

        return mtimes

    def _record_sync_analytics(self, sync_result: Dict) -> bool:
        """Записывает результат синхронизации в аналитику"""
        try:
            # Это можно расширить для более детальной аналитики синхронизации
            # Пока просто логируем успешное обновление
            if sync_result["success"] and sync_result["changes"] > 0:
                logger.info(f"📈 Аналитика: обновлена база знаний ({sync_result['changes']} файлов)")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка записи аналитики синхронизации: {e}")
            return False

    async def check_sync_needed(self) -> Tuple[bool, str]:
        """
        Проверяет, нужна ли синхронизация

        Returns:
            (нужна_синхронизация, причина)
        """
        try:
            # Проверяем, были ли неотвеченные запросы
            summary = self.analytics.get_analytics_summary(days=1)

            if summary["period_stats"]["total_queries"] > 0:
                answer_rate = summary["period_stats"]["answer_rate"]

                # Если процент ответов низкий - рекомендуем синхронизацию
                if answer_rate < 70:
                    return True, f"Низкий процент ответов: {answer_rate:.1f}%"

                # Если есть много неотвеченных запросов
                if len(summary["top_unanswered"]) >= 5:
                    return (
                        True,
                        f"Найдено {len(summary['top_unanswered'])} типов неотвеченных запросов",
                    )

            # Проверяем время последней синхронизации
            if self.last_sync_time:
                hours_since_sync = (datetime.now() - self.last_sync_time).total_seconds() / 3600
                if hours_since_sync > 24:
                    return True, f"Прошло {hours_since_sync:.1f} часов с последней синхронизации"
            else:
                return True, "Синхронизация еще не выполнялась"

            return False, "Синхронизация не требуется"

        except Exception as e:
            logger.error(f"❌ Ошибка при проверке необходимости синхронизации: {e}")
            return False, f"Ошибка проверки: {e}"

    def get_sync_status(self) -> Dict:
        """Получает статус последней синхронизации"""
        return {
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "last_sync_success": self.last_sync_success,
            "last_sync_changes": self.last_sync_changes,
            "spreadsheet_url": self.default_spreadsheet_url,
            "available_sheets": list(self.sheets_updater.csv_paths.keys()),
        }

    async def smart_sync(self) -> Dict:
        """
        Умная синхронизация - выполняется только при необходимости
        """
        try:
            # Проверяем, нужна ли синхронизация
            sync_needed, reason = await self.check_sync_needed()

            if sync_needed:
                logger.info(f"🤖 Умная синхронизация: {reason}")
                return await self.full_sync_knowledge_base()
            else:
                logger.info(f"✅ Умная синхронизация: {reason}")
                return {
                    "success": True,
                    "changes": 0,
                    "skipped": True,
                    "reason": reason,
                    "duration_ms": 0,
                }

        except Exception as e:
            logger.error(f"❌ Ошибка умной синхронизации: {e}")
            return {"success": False, "error": str(e), "changes": 0, "duration_ms": 0}


# Глобальный экземпляр сервиса
knowledge_sync_service = KnowledgeSyncService()
