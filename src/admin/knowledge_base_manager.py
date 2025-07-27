"""
Менеджер базы знаний для администраторов
Обеспечивает просмотр, экспорт и управление содержимым ChromaDB
"""

import json
import logging
import os
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import csv

from src.ai.knowledge_base import knowledge_base
from src.analytics.analytics_service import analytics_service

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """Менеджер для управления базой знаний ChromaDB"""

    def __init__(self):
        self.knowledge_base = knowledge_base
        self.analytics = analytics_service
        logger.info("Knowledge Base Manager инициализирован")

    def get_knowledge_base_overview(self) -> Dict:
        """Получает общий обзор базы знаний"""
        try:
            if not self.knowledge_base.is_initialized:
                return {"success": False, "error": "База знаний не инициализирована"}

            # Получаем все документы
            collection = self.knowledge_base.collection
            result = collection.get()

            total_documents = len(result["ids"])

            # Анализируем по категориям
            categories = {}
            sources = {}
            languages = {}

            for i, metadata in enumerate(result["metadatas"]):
                # Категории
                category = metadata.get("category", "unknown")
                categories[category] = categories.get(category, 0) + 1

                # Источники
                source = metadata.get("source", "csv")
                sources[source] = sources.get(source, 0) + 1

                # Языки (определяем по наличию ответов)
                if metadata.get("answer_ukr"):
                    languages["ukrainian"] = languages.get("ukrainian", 0) + 1
                if metadata.get("answer_rus"):
                    languages["russian"] = languages.get("russian", 0) + 1

            return {
                "success": True,
                "total_documents": total_documents,
                "categories": categories,
                "sources": sources,
                "languages": languages,
                "collection_name": collection.name,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Ошибка получения обзора базы знаний: {e}")
            return {"success": False, "error": str(e)}

    def browse_knowledge_base(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict:
        """Просматривает содержимое базы знаний с фильтрацией"""
        try:
            if not self.knowledge_base.is_initialized:
                return {"success": False, "error": "База знаний не инициализирована"}

            collection = self.knowledge_base.collection
            result = collection.get()

            # Фильтруем результаты
            filtered_items = []
            for i, (doc_id, document, metadata) in enumerate(
                zip(result["ids"], result["documents"], result["metadatas"])
            ):
                # Применяем фильтры
                if category and metadata.get("category") != category:
                    continue
                if source and metadata.get("source") != source:
                    continue

                item = {
                    "id": doc_id,
                    "category": metadata.get("category", "unknown"),
                    "subcategory": metadata.get("subcategory", ""),
                    "button_text": metadata.get("button_text", ""),
                    "keywords": metadata.get("keywords", ""),
                    "answer_ukr": metadata.get("answer_ukr", ""),
                    "answer_rus": metadata.get("answer_rus", ""),
                    "source": metadata.get("source", "csv"),
                    "created_at": metadata.get("created_at", ""),
                    "document_preview": document[:200] + "..." if len(document) > 200 else document,
                }
                filtered_items.append(item)

            # Применяем пагинацию
            total_filtered = len(filtered_items)
            paginated_items = filtered_items[offset : offset + limit]

            return {
                "success": True,
                "items": paginated_items,
                "total_count": total_filtered,
                "showing": len(paginated_items),
                "offset": offset,
                "limit": limit,
                "has_more": offset + limit < total_filtered,
                "filters": {"category": category, "source": source},
            }

        except Exception as e:
            logger.error(f"Ошибка просмотра базы знаний: {e}")
            return {"success": False, "error": str(e)}

    def search_knowledge_base(self, query: str, limit: int = 10) -> Dict:
        """Поиск в базе знаний"""
        try:
            if not self.knowledge_base.is_initialized:
                return {"success": False, "error": "База знаний не инициализирована"}

            # Выполняем векторный поиск
            collection = self.knowledge_base.collection
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )

            search_results = []
            for i, (doc_id, document, metadata, distance) in enumerate(
                zip(
                    results["ids"][0],
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ):
                item = {
                    "id": doc_id,
                    "category": metadata.get("category", "unknown"),
                    "keywords": metadata.get("keywords", ""),
                    "answer_ukr": metadata.get("answer_ukr", ""),
                    "answer_rus": metadata.get("answer_rus", ""),
                    "source": metadata.get("source", "csv"),
                    "relevance_score": 1 - distance,  # Преобразуем расстояние в релевантность
                    "document_preview": document[:150] + "..." if len(document) > 150 else document,
                }
                search_results.append(item)

            return {
                "success": True,
                "query": query,
                "results": search_results,
                "total_found": len(search_results),
            }

        except Exception as e:
            logger.error(f"Ошибка поиска в базе знаний: {e}")
            return {"success": False, "error": str(e)}

    def export_knowledge_base(
        self, export_format: str = "json", include_admin_additions: bool = True
    ) -> Dict:
        """Экспортирует базу знаний в различных форматах"""
        try:
            if not self.knowledge_base.is_initialized:
                return {"success": False, "error": "База знаний не инициализирована"}

            collection = self.knowledge_base.collection
            result = collection.get()

            # Подготавливаем данные для экспорта
            export_data = []
            for i, (doc_id, document, metadata) in enumerate(
                zip(result["ids"], result["documents"], result["metadatas"])
            ):
                # Фильтруем админские добавления если нужно
                if not include_admin_additions and metadata.get("source") == "admin_correction":
                    continue

                item = {
                    "id": doc_id,
                    "category": metadata.get("category", ""),
                    "subcategory": metadata.get("subcategory", ""),
                    "button_text": metadata.get("button_text", ""),
                    "keywords": metadata.get("keywords", ""),
                    "answer_ukr": metadata.get("answer_ukr", ""),
                    "answer_rus": metadata.get("answer_rus", ""),
                    "sort_order": metadata.get("sort_order", "999"),
                    "source": metadata.get("source", "csv"),
                    "created_at": metadata.get("created_at", ""),
                    "document_text": document,
                }
                export_data.append(item)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if export_format.lower() == "json":
                return self._export_as_json(export_data, timestamp)
            elif export_format.lower() == "csv":
                return self._export_as_csv(export_data, timestamp)
            elif export_format.lower() == "backup":
                return self._export_as_backup(export_data, timestamp)
            else:
                return {
                    "success": False,
                    "error": f"Неподдерживаемый формат экспорта: {export_format}",
                }

        except Exception as e:
            logger.error(f"Ошибка экспорта базы знаний: {e}")
            return {"success": False, "error": str(e)}

    def _export_as_json(self, data: List[Dict], timestamp: str) -> Dict:
        """Экспорт в JSON формате"""
        try:
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)

            filename = f"knowledge_base_export_{timestamp}.json"
            filepath = os.path.join(export_dir, filename)

            export_package = {
                "export_info": {
                    "timestamp": timestamp,
                    "total_items": len(data),
                    "format": "json",
                    "version": "1.0",
                },
                "knowledge_base": data,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_package, f, ensure_ascii=False, indent=2)

            return {
                "success": True,
                "format": "json",
                "filename": filename,
                "filepath": filepath,
                "items_exported": len(data),
                "file_size": os.path.getsize(filepath),
            }

        except Exception as e:
            logger.error(f"Ошибка JSON экспорта: {e}")
            return {"success": False, "error": str(e)}

    def _export_as_csv(self, data: List[Dict], timestamp: str) -> Dict:
        """Экспорт в CSV формате (совместимый с Google Sheets)"""
        try:
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)

            filename = f"knowledge_base_export_{timestamp}.csv"
            filepath = os.path.join(export_dir, filename)

            # CSV заголовки
            fieldnames = [
                "category",
                "subcategory",
                "button_text",
                "keywords",
                "answer_ukr",
                "answer_rus",
                "sort_order",
                "source",
                "created_at",
            ]

            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for item in data:
                    # Отбираем только нужные поля для CSV
                    csv_row = {field: item.get(field, "") for field in fieldnames}
                    writer.writerow(csv_row)

            return {
                "success": True,
                "format": "csv",
                "filename": filename,
                "filepath": filepath,
                "items_exported": len(data),
                "file_size": os.path.getsize(filepath),
            }

        except Exception as e:
            logger.error(f"Ошибка CSV экспорта: {e}")
            return {"success": False, "error": str(e)}

    def _export_as_backup(self, data: List[Dict], timestamp: str) -> Dict:
        """Создает полный бэкап для переноса на production"""
        try:
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)

            backup_name = f"knowledge_base_backup_{timestamp}"
            backup_dir = os.path.join(export_dir, backup_name)
            os.makedirs(backup_dir, exist_ok=True)

            # 1. JSON данные
            json_file = os.path.join(backup_dir, "knowledge_base.json")
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 2. CSV данные
            csv_file = os.path.join(backup_dir, "knowledge_base.csv")
            fieldnames = [
                "category",
                "subcategory",
                "button_text",
                "keywords",
                "answer_ukr",
                "answer_rus",
                "sort_order",
                "source",
            ]

            with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in data:
                    csv_row = {field: item.get(field, "") for field in fieldnames}
                    writer.writerow(csv_row)

            # 3. Метаданные бэкапа
            metadata_file = os.path.join(backup_dir, "backup_info.json")
            backup_metadata = {
                "created_at": timestamp,
                "total_items": len(data),
                "categories": {},
                "sources": {},
                "backup_version": "1.0",
                "compatible_with": ["ChromaDB", "Google Sheets", "CSV import"],
            }

            # Подсчитываем статистику
            for item in data:
                category = item.get("category", "unknown")
                source = item.get("source", "csv")
                backup_metadata["categories"][category] = (
                    backup_metadata["categories"].get(category, 0) + 1
                )
                backup_metadata["sources"][source] = backup_metadata["sources"].get(source, 0) + 1

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(backup_metadata, f, ensure_ascii=False, indent=2)

            # 4. Инструкции по развертыванию
            instructions_file = os.path.join(backup_dir, "DEPLOYMENT_INSTRUCTIONS.md")
            instructions = f"""# Инструкции по развертыванию базы знаний

## Информация о бэкапе
- Создан: {timestamp}
- Количество записей: {len(data)}
- Формат: JSON + CSV + Metadata

## Способы развертывания на production:

### 1. Автоматическое развертывание (рекомендуется)
```bash
# Скопируйте папку {backup_name} на production сервер
# Запустите скрипт импорта:
python import_knowledge_base.py --backup-dir {backup_name}
```

### 2. Через Google Sheets
1. Загрузите knowledge_base.csv в Google Sheets
2. Настройте существующую интеграцию с Google Sheets
3. Выполните синхронизацию: /reload

### 3. Ручной импорт в ChromaDB
```python
from src.ai.knowledge_base import knowledge_base
import json

# Загрузите данные
with open('knowledge_base.json', 'r') as f:
    data = json.load(f)

# Импортируйте в ChromaDB
knowledge_base.import_from_backup(data)
```

## Проверка развертывания
После развертывания выполните:
- /stats - проверка общей статистики
- /analytics - проверка работы AI
- Тестовые запросы в AI режиме

## Поддержка
При проблемах с развертыванием проверьте логи и убедитесь, что:
- ChromaDB инициализирована
- Все зависимости установлены
- Права доступа корректны
"""

            with open(instructions_file, "w", encoding="utf-8") as f:
                f.write(instructions)

            # 5. Создаем ZIP архив
            zip_filename = f"{backup_name}.zip"
            zip_filepath = os.path.join(export_dir, zip_filename)

            with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(backup_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, export_dir)
                        zipf.write(file_path, arcname)

            return {
                "success": True,
                "format": "backup",
                "backup_name": backup_name,
                "zip_file": zip_filename,
                "zip_filepath": zip_filepath,
                "items_exported": len(data),
                "file_size": os.path.getsize(zip_filepath),
                "includes": ["JSON", "CSV", "Metadata", "Instructions"],
            }

        except Exception as e:
            logger.error(f"Ошибка создания бэкапа: {e}")
            return {"success": False, "error": str(e)}

    def import_from_backup(self, backup_path: str) -> Dict:
        """Импортирует базу знаний из бэкапа"""
        try:
            if not os.path.exists(backup_path):
                return {"success": False, "error": f"Бэкап не найден: {backup_path}"}

            # Определяем тип бэкапа
            if backup_path.endswith(".zip"):
                return self._import_from_zip_backup(backup_path)
            elif backup_path.endswith(".json"):
                return self._import_from_json_backup(backup_path)
            elif os.path.isdir(backup_path):
                return self._import_from_directory_backup(backup_path)
            else:
                return {"success": False, "error": "Неподдерживаемый формат бэкапа"}

        except Exception as e:
            logger.error(f"Ошибка импорта бэкапа: {e}")
            return {"success": False, "error": str(e)}

    def _import_from_json_backup(self, json_path: str) -> Dict:
        """Импорт из JSON файла"""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Если это экспортированный пакет, извлекаем данные
            if isinstance(data, dict) and "knowledge_base" in data:
                items = data["knowledge_base"]
            else:
                items = data

            return self._populate_knowledge_base_from_data(items)

        except Exception as e:
            logger.error(f"Ошибка импорта JSON: {e}")
            return {"success": False, "error": str(e)}

    def _populate_knowledge_base_from_data(self, items: List[Dict]) -> Dict:
        """Заполняет базу знаний данными"""
        try:
            if not self.knowledge_base.is_initialized:
                # Пытаемся инициализировать
                success = self.knowledge_base.populate_vector_store()
                if not success:
                    return {"success": False, "error": "Не удалось инициализировать базу знаний"}

            collection = self.knowledge_base.collection

            # Очищаем существующую коллекцию
            try:
                collection.delete(where={})
            except Exception as e:
                logger.debug(f"Коллекция может быть пустой: {e}")  # Коллекция может быть пустой

            # Добавляем данные пакетами
            batch_size = 100
            imported_count = 0

            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]

                # Подготавливаем данные для ChromaDB
                ids = []
                documents = []
                metadatas = []

                for item in batch:
                    # Создаем ID если его нет
                    item_id = item.get("id", f"imported_{imported_count}")
                    ids.append(item_id)

                    # Создаем документ для поиска
                    doc_text = item.get("document_text")
                    if not doc_text:
                        doc_text = f"""
                        Категория: {item.get('category', '')}
                        Ключевые слова: {item.get('keywords', '')}
                        Украинский ответ: {item.get('answer_ukr', '')}
                        Русский ответ: {item.get('answer_rus', '')}
                        """.strip()

                    documents.append(doc_text)

                    # Подготавливаем метаданные
                    metadata = {
                        "category": item.get("category", ""),
                        "subcategory": item.get("subcategory", ""),
                        "button_text": item.get("button_text", ""),
                        "keywords": item.get("keywords", ""),
                        "answer_ukr": item.get("answer_ukr", ""),
                        "answer_rus": item.get("answer_rus", ""),
                        "sort_order": str(item.get("sort_order", "999")),
                        "source": item.get("source", "imported"),
                        "created_at": item.get("created_at", datetime.now().isoformat()),
                    }
                    metadatas.append(metadata)
                    imported_count += 1

                # Добавляем в ChromaDB
                collection.add(ids=ids, documents=documents, metadatas=metadatas)

            logger.info(f"Импортировано {imported_count} записей в базу знаний")

            return {
                "success": True,
                "imported_count": imported_count,
                "total_items": len(items),
                "message": f"Успешно импортировано {imported_count} записей",
            }

        except Exception as e:
            logger.error(f"Ошибка заполнения базы знаний: {e}")
            return {"success": False, "error": str(e)}


# Глобальный экземпляр
knowledge_base_manager = KnowledgeBaseManager()
