"""
Менеджер синхронизации с Google Sheets и умного обновления базы знаний
Интегрирует smart_updater с Google Sheets синхронизацией
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from src.ai.smart_knowledge_updater import smart_updater
from src.ai.knowledge_base import knowledge_base

logger = logging.getLogger(__name__)


class KnowledgeSyncManager:
    """Менеджер синхронизации базы знаний с внешними источниками"""

    def __init__(self):
        self.smart_updater = smart_updater
        self.knowledge_base = knowledge_base
        self.is_syncing = False
        self.last_sync_time = None
        self.sync_history = []

    async def sync_with_google_sheets(self, force_full_reload: bool = False) -> Dict:
        """
        Синхронизация с Google Sheets с умным обновлением

        Args:
            force_full_reload: Принудительная полная перезагрузка
        """
        if self.is_syncing:
            return {"success": False, "error": "Синхронизация уже выполняется"}

        try:
            self.is_syncing = True
            logger.info("Начинается синхронизация с Google Sheets...")

            # 1. Получаем рекомендацию по стратегии обновления
            strategy_recommendation = self.smart_updater.get_update_strategy_recommendation()
            logger.info(f"Рекомендуемая стратегия: {strategy_recommendation.get('strategy')}")

            # 2. Определяем стратегию обновления
            update_strategy = self._determine_update_strategy(
                strategy_recommendation, force_full_reload
            )

            # 3. Выполняем обновление согласно выбранной стратегии
            if update_strategy == "full_reload":
                result = await self._perform_full_sync()
            elif update_strategy == "incremental_update":
                result = await self._perform_incremental_sync()
            elif update_strategy == "no_update":
                result = {
                    "success": True,
                    "message": "Синхронизация не требуется - изменений не обнаружено",
                    "strategy": "no_update",
                }
            else:
                result = {
                    "success": False,
                    "error": f"Неизвестная стратегия обновления: {update_strategy}",
                }

            # 4. Обновляем историю синхронизации
            self._update_sync_history(result, update_strategy)

            self.last_sync_time = datetime.now()
            logger.info(f"Синхронизация завершена: {result.get('message', 'без сообщения')}")

            return result

        except Exception as e:
            logger.error(f"Ошибка синхронизации с Google Sheets: {e}")
            return {"success": False, "error": str(e)}
        finally:
            self.is_syncing = False

    def _determine_update_strategy(self, recommendation: Dict, force_full_reload: bool) -> str:
        """Определяет стратегию обновления на основе рекомендации"""
        if force_full_reload:
            return "full_reload"

        strategy = recommendation.get("strategy", "incremental_update")

        # Дополнительная логика определения стратегии
        if strategy == "error":
            logger.warning("Ошибка анализа - используем инкрементальное обновление")
            return "incremental_update"

        return strategy

    async def _perform_full_sync(self) -> Dict:
        """Выполняет полную синхронизацию"""
        logger.info("Выполняется полная синхронизация...")

        # Выполняем полную перезагрузку через smart_updater
        result = self.smart_updater.smart_update_knowledge_base(force_full_reload=True)

        result["strategy"] = "full_reload"
        return result

    async def _perform_incremental_sync(self) -> Dict:
        """Выполняет инкрементальную синхронизацию"""
        logger.info("Выполняется инкрементальная синхронизация...")

        # Выполняем умное обновление через smart_updater
        result = self.smart_updater.smart_update_knowledge_base()

        result["strategy"] = "incremental_update"
        return result

    def _update_sync_history(self, result: Dict, strategy: str) -> None:
        """Обновляет историю синхронизации"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy,
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "stats": result.get("stats", {}),
            "error": result.get("error"),
        }

        self.sync_history.append(history_entry)

        # Ограничиваем историю последними 50 записями
        if len(self.sync_history) > 50:
            self.sync_history = self.sync_history[-50:]

    def get_sync_status(self) -> Dict:
        """Получает текущий статус синхронизации"""
        return {
            "is_syncing": self.is_syncing,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "sync_history_count": len(self.sync_history),
            "last_sync_result": self.sync_history[-1] if self.sync_history else None,
        }

    def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """Получает историю синхронизации"""
        return self.sync_history[-limit:] if self.sync_history else []

    async def check_sync_needed(self) -> Dict:
        """Проверяет, нужна ли синхронизация"""
        try:
            # Получаем рекомендации по обновлению
            recommendations = self.smart_updater.get_update_recommendations()

            # Анализируем рекомендации
            high_priority_count = len([r for r in recommendations if r.get("priority") == "high"])
            medium_priority_count = len(
                [r for r in recommendations if r.get("priority") == "medium"]
            )

            sync_needed = high_priority_count > 0 or medium_priority_count > 2

            return {
                "sync_needed": sync_needed,
                "priority": (
                    "high"
                    if high_priority_count > 0
                    else ("medium" if medium_priority_count > 0 else "low")
                ),
                "recommendations": recommendations,
                "reasons": [r.get("description") for r in recommendations],
            }

        except Exception as e:
            logger.error(f"Ошибка проверки необходимости синхронизации: {e}")
            return {
                "sync_needed": True,  # В случае ошибки лучше синхронизировать
                "priority": "unknown",
                "error": str(e),
            }

    async def auto_sync_if_needed(self, threshold_hours: int = 24) -> Dict:
        """Автоматическая синхронизация при необходимости"""
        try:
            # Проверяем, прошло ли достаточно времени с последней синхронизации
            if self.last_sync_time:
                hours_since_sync = (datetime.now() - self.last_sync_time).total_seconds() / 3600
                if hours_since_sync < threshold_hours:
                    return {
                        "success": True,
                        "message": f"Автосинхронизация не требуется (прошло {hours_since_sync:.1f} часов)",
                        "action": "skipped",
                    }

            # Проверяем, нужна ли синхронизация
            sync_check = await self.check_sync_needed()

            if not sync_check.get("sync_needed", False):
                return {
                    "success": True,
                    "message": "Автосинхронизация не требуется - изменений не обнаружено",
                    "action": "skipped",
                }

            # Выполняем синхронизацию
            result = await self.sync_with_google_sheets()
            result["action"] = "performed"

            return result

        except Exception as e:
            logger.error(f"Ошибка автосинхронизации: {e}")
            return {"success": False, "error": str(e), "action": "error"}


# Глобальный экземпляр менеджера синхронизации
knowledge_sync_manager = KnowledgeSyncManager()
