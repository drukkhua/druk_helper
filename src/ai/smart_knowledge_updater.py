"""
Умная система обновления базы знаний
Отслеживает изменения и обновляет только измененные записи
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from src.ai.knowledge_base import knowledge_base
from src.admin.knowledge_base_manager import knowledge_base_manager

logger = logging.getLogger(__name__)


class SmartKnowledgeUpdater:
    """Умное обновление базы знаний с отслеживанием изменений"""

    def __init__(self):
        self.knowledge_base = knowledge_base
        self.knowledge_manager = knowledge_base_manager
        self.changes_cache_file = "./data/knowledge_changes_cache.json"
        logger.info("Smart Knowledge Updater инициализирован")

    def generate_content_hash(self, row: Dict) -> str:
        """Генерирует хеш контента для отслеживания изменений"""
        # Используем только значимые поля для хеша
        content_fields = [
            row.get("category", ""),
            row.get(
                "subcategory", ""
            ),  # Остается subcategory для совместимости (внутренне используется)
            row.get("button_text", ""),
            row.get("keywords", ""),
            row.get("answer_ukr", ""),
            row.get("answer_rus", ""),
            row.get("sort_order", "999"),
        ]
        content_string = "|".join(content_fields)
        return hashlib.md5(content_string.encode("utf-8"), usedforsecurity=False).hexdigest()

    def generate_stable_id(self, row: Dict, row_index: int) -> str:
        """Генерирует стабильный ID основанный на контенте, а не позиции"""
        # Используем первые слова button_text + category для стабильного ID
        button_words = row.get("button_text", "").strip()[:50]  # Первые 50 символов
        category = row.get("category", "unknown")

        # Очищаем от специальных символов
        clean_text = "".join(c for c in button_words if c.isalnum() or c.isspace())
        clean_text = "_".join(clean_text.split())[:30]  # Максимум 30 символов

        if not clean_text:
            # Fallback на index если button_text пустой
            clean_text = f"item_{row_index}"

        stable_id = f"{category}_{clean_text}"

        # Проверяем уникальность и добавляем суффикс если нужно
        return self._ensure_unique_id(stable_id, row)

    def _ensure_unique_id(self, base_id: str, row: Dict) -> str:
        """Обеспечивает уникальность ID"""
        # Добавляем хеш первых 8 символов для гарантии уникальности
        content_hash = self.generate_content_hash(row)[:8]
        return f"{base_id}_{content_hash}"

    def load_changes_cache(self) -> Dict:
        """Загружает кеш изменений"""
        if not os.path.exists(self.changes_cache_file):
            return {"hashes": {}, "last_update": None}

        try:
            with open(self.changes_cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки кеша изменений: {e}")
            return {"hashes": {}, "last_update": None}

    def save_changes_cache(self, cache: Dict) -> None:
        """Сохраняет кеш изменений"""
        try:
            os.makedirs(os.path.dirname(self.changes_cache_file), exist_ok=True)
            cache["last_update"] = datetime.now().isoformat()

            with open(self.changes_cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения кеша изменений: {e}")

    def detect_changes(self, new_data: List[Dict]) -> Dict:
        """Обнаруживает изменения в данных"""
        cache = self.load_changes_cache()
        old_hashes = cache.get("hashes", {})

        changes = {
            "added": [],  # Новые записи
            "modified": [],  # Измененные записи
            "deleted": [],  # Удаленные записи (остались в кеше, но нет в новых данных)
            "unchanged": [],  # Неизмененные записи
            "admin_kept": [],  # Админские записи, которые нужно сохранить
        }

        new_hashes = {}
        new_ids = set()

        # Анализируем новые данные
        for i, row in enumerate(new_data):
            stable_id = self.generate_stable_id(row, i)
            content_hash = self.generate_content_hash(row)

            new_hashes[stable_id] = content_hash
            new_ids.add(stable_id)

            if stable_id not in old_hashes:
                # Новая запись
                changes["added"].append({"id": stable_id, "data": row, "hash": content_hash})
            elif old_hashes[stable_id] != content_hash:
                # Измененная запись
                changes["modified"].append(
                    {
                        "id": stable_id,
                        "data": row,
                        "old_hash": old_hashes[stable_id],
                        "new_hash": content_hash,
                    }
                )
            else:
                # Неизмененная запись
                changes["unchanged"].append({"id": stable_id, "data": row, "hash": content_hash})

        # Находим удаленные записи (были в кеше, но нет в новых данных)
        deleted_ids = set(old_hashes.keys()) - new_ids
        for deleted_id in deleted_ids:
            # Проверяем, не админская ли это запись
            if self._is_admin_record(deleted_id):
                changes["admin_kept"].append(deleted_id)
            else:
                changes["deleted"].append(deleted_id)

        # Обновляем кеш
        cache["hashes"] = new_hashes
        self.save_changes_cache(cache)

        return changes

    def _is_admin_record(self, record_id: str) -> bool:
        """Проверяет, является ли запись админской"""
        try:
            if not self.knowledge_base.is_initialized:
                return False

            # Получаем запись из ChromaDB
            results = self.knowledge_base.collection.get(ids=[record_id], include=["metadatas"])

            if results["metadatas"]:
                metadata = results["metadatas"][0]
                source = metadata.get("source", "")
                return source in ["admin_correction", "admin_addition"]

            return False
        except Exception:
            return False

    def smart_update_knowledge_base(
        self, csv_data: List[Dict] = None, force_full_reload: bool = False
    ) -> Dict:
        """Умное обновление базы знаний с отслеживанием изменений

        Args:
            csv_data: Данные для обновления (если None - загружаются из источника)
            force_full_reload: Принудительная полная перезагрузка
        """
        try:
            logger.info("Начинаем умное обновление базы знаний...")

            # Если требуется полная перезагрузка
            if force_full_reload:
                logger.info("Выполняется принудительная полная перезагрузка...")
                return self._full_reload_knowledge_base(csv_data)

            # Загружаем новые данные
            if csv_data is None:
                csv_data = self.knowledge_base.load_csv_data()

            if not csv_data:
                return {"success": False, "error": "Нет данных для обновления"}

            # Обнаруживаем изменения
            changes = self.detect_changes(csv_data)

            # Статистика изменений
            stats = {
                "added": len(changes["added"]),
                "modified": len(changes["modified"]),
                "deleted": len(changes["deleted"]),
                "unchanged": len(changes["unchanged"]),
                "admin_kept": len(changes["admin_kept"]),
            }

            logger.info(f"Обнаружены изменения: {stats}")

            # Если нет изменений - не делаем ничего
            if stats["added"] == 0 and stats["modified"] == 0 and stats["deleted"] == 0:
                return {
                    "success": True,
                    "message": "Изменений не обнаружено",
                    "stats": stats,
                    "changes": changes,
                }

            # Применяем изменения
            update_result = self._apply_changes_to_chromadb(changes)

            if update_result["success"]:
                return {
                    "success": True,
                    "message": f"База знаний обновлена: +{stats['added']} ~{stats['modified']} -{stats['deleted']}",
                    "stats": stats,
                    "changes": changes,
                    "details": update_result,
                }
            else:
                return {"success": False, "error": update_result["error"], "stats": stats}

        except Exception as e:
            logger.error(f"Ошибка умного обновления: {e}")
            return {"success": False, "error": str(e)}

    def _apply_changes_to_chromadb(self, changes: Dict) -> Dict:
        """Применяет изменения к ChromaDB"""
        try:
            if not self.knowledge_base.is_initialized:
                return {"success": False, "error": "ChromaDB не инициализирован"}

            operations_count = 0

            # 1. Удаляем устаревшие записи
            if changes["deleted"]:
                try:
                    self.knowledge_base.collection.delete(ids=changes["deleted"])
                    operations_count += len(changes["deleted"])
                    logger.info(f"Удалено {len(changes['deleted'])} записей")
                except Exception as e:
                    logger.warning(f"Ошибка удаления записей: {e}")

            # 2. Добавляем новые записи
            if changes["added"]:
                new_docs = []
                for item in changes["added"]:
                    doc = self._create_chromadb_document(item["id"], item["data"])
                    new_docs.append(doc)

                if new_docs:
                    ids = [doc["id"] for doc in new_docs]
                    texts = [doc["text"] for doc in new_docs]
                    metadatas = [doc["metadata"] for doc in new_docs]

                    self.knowledge_base.collection.add(
                        ids=ids, documents=texts, metadatas=metadatas
                    )
                    operations_count += len(new_docs)
                    logger.info(f"Добавлено {len(new_docs)} новых записей")

            # 3. Обновляем измененные записи
            if changes["modified"]:
                # ChromaDB не поддерживает update, поэтому удаляем и добавляем заново
                modified_ids = [item["id"] for item in changes["modified"]]

                # Удаляем старые версии
                try:
                    self.knowledge_base.collection.delete(ids=modified_ids)
                except Exception as e:
                    logger.warning(f"Ошибка удаления старых версий: {e}")

                # Добавляем новые версии
                modified_docs = []
                for item in changes["modified"]:
                    doc = self._create_chromadb_document(item["id"], item["data"])
                    modified_docs.append(doc)

                if modified_docs:
                    ids = [doc["id"] for doc in modified_docs]
                    texts = [doc["text"] for doc in modified_docs]
                    metadatas = [doc["metadata"] for doc in modified_docs]

                    self.knowledge_base.collection.add(
                        ids=ids, documents=texts, metadatas=metadatas
                    )
                    operations_count += len(modified_docs)
                    logger.info(f"Обновлено {len(modified_docs)} записей")

            return {
                "success": True,
                "operations_count": operations_count,
                "message": f"Выполнено {operations_count} операций обновления",
            }

        except Exception as e:
            logger.error(f"Ошибка применения изменений к ChromaDB: {e}")
            return {"success": False, "error": str(e)}

    def _create_chromadb_document(self, doc_id: str, data: Dict) -> Dict:
        """Создает документ для ChromaDB"""
        keywords = data.get("keywords", "").strip()
        answer_ukr = data.get("answer_ukr", "")[:200].strip()
        answer_rus = data.get("answer_rus", "")[:200].strip()

        # Объединяем все в один поисковый документ
        search_text = f"""
        Категория: {data.get('category', '')}
        Ключевые слова: {keywords}
        Украинский ответ: {answer_ukr}
        Русский ответ: {answer_rus}
        """.strip()

        return {
            "id": doc_id,
            "text": search_text,
            "metadata": {
                "category": data.get("category", ""),
                "subcategory": data.get(
                    "subcategory", ""
                ),  # Остается subcategory для совместимости (внутренне используется)
                "button_text": data.get("button_text", ""),
                "keywords": keywords,
                "answer_ukr": data.get("answer_ukr", ""),
                "answer_rus": data.get("answer_rus", ""),
                "sort_order": data.get("sort_order", "999"),
                "source": "csv",
                "updated_at": datetime.now().isoformat(),
            },
        }

    def get_update_recommendations(self) -> List[Dict]:
        """Получает рекомендации по обновлению базы знаний"""
        try:
            # Загружаем текущие данные из CSV
            csv_data = self.knowledge_base.load_csv_data()

            # Обнаруживаем изменения
            changes = self.detect_changes(csv_data)

            recommendations = []

            if changes["added"]:
                recommendations.append(
                    {
                        "type": "new_content",
                        "priority": "high",
                        "count": len(changes["added"]),
                        "description": f"Обнаружено {len(changes['added'])} новых записей для добавления",
                        "action": "Выполните умное обновление",
                    }
                )

            if changes["modified"]:
                recommendations.append(
                    {
                        "type": "updated_content",
                        "priority": "medium",
                        "count": len(changes["modified"]),
                        "description": f"Обнаружено {len(changes['modified'])} измененных записей",
                        "action": "Рекомендуется обновить для актуальности",
                    }
                )

            if changes["deleted"]:
                recommendations.append(
                    {
                        "type": "removed_content",
                        "priority": "low",
                        "count": len(changes["deleted"]),
                        "description": f"{len(changes['deleted'])} записей больше нет в исходных данных",
                        "action": "Будут удалены при обновлении",
                    }
                )

            if changes["admin_kept"]:
                recommendations.append(
                    {
                        "type": "admin_content",
                        "priority": "info",
                        "count": len(changes["admin_kept"]),
                        "description": f"{len(changes['admin_kept'])} админских записей будут сохранены",
                        "action": "Автоматически сохранены",
                    }
                )

            return recommendations

        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций: {e}")
            return []

    def _full_reload_knowledge_base(self, csv_data: List[Dict] = None) -> Dict:
        """Полная перезагрузка базы знаний (принудительная)"""
        try:
            logger.info("Выполняется полная перезагрузка базы знаний...")

            # Сохраняем админские записи перед очисткой
            admin_records = self._preserve_admin_records()

            # Полная перезагрузка через стандартный механизм
            success = self.knowledge_base.populate_vector_store(force_reload=True)

            if not success:
                return {"success": False, "error": "Ошибка полной перезагрузки базы знаний"}

            # Восстанавливаем админские записи
            restored_count = self._restore_admin_records(admin_records)

            # Обновляем кеш (очищаем старый)
            cache = {"hashes": {}, "last_update": None}
            if csv_data:
                # Создаем новый кеш для текущих данных
                for i, row in enumerate(csv_data):
                    stable_id = self.generate_stable_id(row, i)
                    content_hash = self.generate_content_hash(row)
                    cache["hashes"][stable_id] = content_hash
            self.save_changes_cache(cache)

            return {
                "success": True,
                "message": f"База знаний полностью перезагружена, восстановлено {restored_count} админских записей",
                "stats": {"full_reload": True, "admin_records_restored": restored_count},
            }

        except Exception as e:
            logger.error(f"Ошибка полной перезагрузки: {e}")
            return {"success": False, "error": str(e)}

    def _preserve_admin_records(self) -> List[Dict]:
        """Сохраняет админские записи перед полной перезагрузкой"""
        admin_records = []

        try:
            if not self.knowledge_base.is_initialized:
                return admin_records

            # Получаем все записи
            all_docs = self.knowledge_base.collection.get(include=["documents", "metadatas"])

            if all_docs["metadatas"]:
                for i, metadata in enumerate(all_docs["metadatas"]):
                    source = metadata.get("source", "")
                    if source in ["admin_correction", "admin_addition"]:
                        admin_record = {
                            "id": all_docs["ids"][i],
                            "document": all_docs["documents"][i],
                            "metadata": metadata,
                        }
                        admin_records.append(admin_record)

            logger.info(f"Сохранено {len(admin_records)} админских записей")

        except Exception as e:
            logger.error(f"Ошибка сохранения админских записей: {e}")

        return admin_records

    def _restore_admin_records(self, admin_records: List[Dict]) -> int:
        """Восстанавливает админские записи после перезагрузки"""
        restored_count = 0

        try:
            if not admin_records or not self.knowledge_base.is_initialized:
                return 0

            # Восстанавливаем записи
            ids = [record["id"] for record in admin_records]
            documents = [record["document"] for record in admin_records]
            metadatas = [record["metadata"] for record in admin_records]

            self.knowledge_base.collection.add(ids=ids, documents=documents, metadatas=metadatas)

            restored_count = len(admin_records)
            logger.info(f"Восстановлено {restored_count} админских записей")

        except Exception as e:
            logger.error(f"Ошибка восстановления админских записей: {e}")

        return restored_count

    def get_update_strategy_recommendation(self, csv_data: List[Dict] = None) -> Dict:
        """Рекомендует стратегию обновления базы знаний"""
        try:
            if csv_data is None:
                csv_data = self.knowledge_base.load_csv_data()

            if not csv_data:
                return {"strategy": "no_data", "reason": "Нет данных для анализа"}

            # Анализируем изменения
            changes = self.detect_changes(csv_data)

            total_changes = (
                len(changes["added"]) + len(changes["modified"]) + len(changes["deleted"])
            )
            total_records = len(csv_data)
            change_percentage = (total_changes / total_records * 100) if total_records > 0 else 0

            # Определяем стратегию
            if change_percentage > 50:
                return {
                    "strategy": "full_reload",
                    "reason": f"Слишком много изменений ({change_percentage:.1f}%), полная перезагрузка эффективнее",
                    "changes": changes,
                    "change_percentage": change_percentage,
                }
            elif total_changes == 0:
                return {
                    "strategy": "no_update",
                    "reason": "Изменений не обнаружено",
                    "changes": changes,
                    "change_percentage": 0,
                }
            else:
                return {
                    "strategy": "incremental_update",
                    "reason": f"Умеренное количество изменений ({change_percentage:.1f}%), инкрементальное обновление оптимально",
                    "changes": changes,
                    "change_percentage": change_percentage,
                }

        except Exception as e:
            logger.error(f"Ошибка анализа стратегии обновления: {e}")
            return {"strategy": "error", "reason": f"Ошибка анализа: {str(e)}"}


# Глобальный экземпляр
smart_updater = SmartKnowledgeUpdater()
