"""
База знаний для RAG системы
Загружает данные из CSV файлов и создает векторную базу данных
"""

import csv
import logging
import os
from typing import Dict, List, Optional, Tuple

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    Settings = None

from config import Config

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Класс для работы с базой знаний из CSV файлов"""

    def __init__(self):
        self.config = Config()
        self.chroma_client = None
        self.collection = None
        self.is_initialized = False

        # Пути к CSV файлам
        self.csv_files = {
            "визитки": self.config.VISITKI_CSV_PATH,
            "футболки": self.config.FUTBOLKI_CSV_PATH,
            "листовки": self.config.LISTOVKI_CSV_PATH,
            "наклейки": self.config.NAKLEYKI_CSV_PATH,
            "блокноты": self.config.BLOKNOTY_CSV_PATH,
        }

        # Инициализируем ChromaDB
        self._init_chroma()

    def _init_chroma(self):
        """Инициализация ChromaDB"""
        if chromadb is None:
            logger.warning("ChromaDB не установлен - база знаний недоступна")
            self.is_initialized = False
            return

        try:
            # Создаем директорию для хранения векторной базы
            persist_dir = os.path.join(os.getcwd(), "data", "vectorstore")
            os.makedirs(persist_dir, exist_ok=True)

            # Инициализация ChromaDB клиента
            self.chroma_client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    is_persistent=True
                )
            )

            # Получаем или создаем коллекцию
            collection_name = self.config.CHROMA_COLLECTION_NAME
            try:
                self.collection = self.chroma_client.get_collection(collection_name)
                logger.info(f"Загружена существующая коллекция: {collection_name}")
            except Exception:
                # Коллекция не существует, создаем новую
                self.collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"description": "Bot knowledge base from CSV templates"}
                )
                logger.info(f"Создана новая коллекция: {collection_name}")

            self.is_initialized = True
            logger.info("ChromaDB успешно инициализирован")

        except Exception as e:
            logger.error(f"Ошибка инициализации ChromaDB: {e}")
            self.is_initialized = False

    def load_csv_data(self) -> List[Dict]:
        """Загружает данные из всех CSV файлов"""
        all_data = []

        for category, file_path in self.csv_files.items():
            if not os.path.exists(file_path):
                logger.warning(f"CSV файл не найден: {file_path}")
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    # Определяем разделитель
                    sample = file.read(1024)
                    file.seek(0)

                    delimiter = ';' if ';' in sample else ','

                    reader = csv.DictReader(file, delimiter=delimiter)
                    for row_num, row in enumerate(reader, 1):
                        if self._is_valid_row(row):
                            # Создаем уникальный ID для каждой записи
                            unique_id = f"{category}_{row_num}"

                            data_item = {
                                "id": unique_id,
                                "category": category,
                                "subcategory": row.get("subcategory", ""),
                                "button_text": row.get("button_text", ""),
                                "keywords": row.get("keywords", ""),
                                "answer_ukr": row.get("answer_ukr", ""),
                                "answer_rus": row.get("answer_rus", ""),
                                "sort_order": row.get("sort_order", "0")
                            }
                            all_data.append(data_item)

                logger.info(f"Загружено {len([d for d in all_data if d['category'] == category])} записей из {category}")

            except Exception as e:
                logger.error(f"Ошибка при загрузке CSV файла {file_path}: {e}")

        logger.info(f"Всего загружено {len(all_data)} записей из базы знаний")
        return all_data

    def _is_valid_row(self, row: Dict) -> bool:
        """Проверяет валидность строки данных"""
        required_fields = ["keywords", "answer_ukr", "answer_rus"]
        return all(row.get(field, "").strip() for field in required_fields)

    def create_search_documents(self, data: List[Dict]) -> List[Dict]:
        """Создает документы для поиска, объединяя ключевые слова и ответы"""
        documents = []

        for item in data:
            # Создаем поисковый текст из ключевых слов и части ответов
            keywords = item["keywords"].strip()
            answer_ukr = item["answer_ukr"][:200].strip()  # Первые 200 символов
            answer_rus = item["answer_rus"][:200].strip()

            # Объединяем все в один поисковый документ
            search_text = f"""
            Категория: {item['category']}
            Ключевые слова: {keywords}
            Украинский ответ: {answer_ukr}
            Русский ответ: {answer_rus}
            """.strip()

            doc = {
                "id": item["id"],
                "text": search_text,
                "metadata": {
                    "category": item["category"],
                    "subcategory": item["subcategory"],
                    "button_text": item["button_text"],
                    "keywords": keywords,
                    "answer_ukr": item["answer_ukr"],
                    "answer_rus": item["answer_rus"],
                    "sort_order": item["sort_order"]
                }
            }
            documents.append(doc)

        return documents

    def populate_vector_store(self, force_reload: bool = False):
        """Заполняет векторную базу данных"""
        if not self.is_initialized:
            logger.error("ChromaDB не инициализирован")
            return False

        try:
            # Проверяем, есть ли уже данные в коллекции
            collection_count = self.collection.count()
            if collection_count > 0 and not force_reload:
                logger.info(f"База знаний уже содержит {collection_count} документов")
                return True

            # Если нужно перезагрузить, очищаем коллекцию
            if force_reload and collection_count > 0:
                logger.info("Очистка существующей коллекции...")
                self.chroma_client.delete_collection(self.config.CHROMA_COLLECTION_NAME)
                self.collection = self.chroma_client.create_collection(
                    name=self.config.CHROMA_COLLECTION_NAME,
                    metadata={"description": "Bot knowledge base from CSV templates"}
                )

            # Загружаем данные из CSV
            csv_data = self.load_csv_data()
            if not csv_data:
                logger.warning("Нет данных для загрузки в векторную базу")
                return False

            # Создаем поисковые документы
            documents = self.create_search_documents(csv_data)

            # Подготавливаем данные для ChromaDB
            ids = [doc["id"] for doc in documents]
            texts = [doc["text"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]

            # Добавляем документы в коллекцию
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Успешно добавлено {len(documents)} документов в векторную базу данных")
            return True

        except Exception as e:
            logger.error(f"Ошибка при заполнении векторной базы: {e}")
            return False

    def search_by_keywords(self, query: str, language: str = "ukr", n_results: int = 3) -> List[Dict]:
        """Поиск по ключевым словам (точное совпадение)"""
        if not self.is_initialized or not self.collection:
            logger.error("База знаний не инициализирована")
            return []

        try:
            # Получаем все документы с их ID
            all_docs = self.collection.get(include=["metadatas"])

            # Нормализуем запрос для поиска
            query_words = set(word.lower().strip() for word in query.replace(",", " ").split())

            # Ищем совпадения по ключевым словам
            matches = []
            for i, (doc_id, metadata) in enumerate(zip(all_docs["ids"], all_docs["metadatas"])):
                keywords = metadata.get("keywords", "").lower()
                keyword_words = set(word.strip() for word in keywords.replace(",", " ").split())

                # Считаем количество совпадающих слов
                intersection = query_words.intersection(keyword_words)
                if intersection:
                    match_score = len(intersection) / len(query_words)  # Доля совпавших слов

                    answer = metadata.get(f"answer_{language}", metadata.get("answer_ukr", ""))

                    # Добавляем ID в метаданные для комбинирования
                    metadata_with_id = dict(metadata)
                    metadata_with_id["id"] = doc_id

                    matches.append({
                        "category": metadata.get("category", ""),
                        "keywords": metadata.get("keywords", ""),
                        "answer": answer,
                        "relevance_score": match_score,
                        "metadata": metadata_with_id,
                        "search_type": "keyword"
                    })

            # Сортируем по релевантности и возвращаем топ результаты
            matches.sort(key=lambda x: x["relevance_score"], reverse=True)
            return matches[:n_results]

        except Exception as e:
            logger.error(f"Ошибка при поиске по ключевым словам: {e}")
            return []

    def search_knowledge(self, query: str, language: str = "ukr", n_results: int = 3) -> List[Dict]:
        """Гибридный поиск по базе знаний (ключевые слова + векторный)"""
        if not self.is_initialized or not self.collection:
            logger.error("База знаний не инициализирована")
            return []

        # 1. Сначала ищем по ключевым словам
        keyword_results = self.search_by_keywords(query, language, n_results)

        # 2. Выполняем векторный поиск
        vector_results = self._vector_search(query, language, n_results)

        # 3. Комбинируем результаты
        combined_results = self._combine_search_results(keyword_results, vector_results, n_results)

        logger.info(f"Гибридный поиск: найдено {len(keyword_results)} по ключевым словам, {len(vector_results)} векторным поиском")
        logger.info(f"Итого {len(combined_results)} релевантных документов для запроса: {query[:50]}...")

        return combined_results

    def _vector_search(self, query: str, language: str = "ukr", n_results: int = 3) -> List[Dict]:
        """Векторный поиск"""
        try:
            # Выполняем семантический поиск
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )

            # Обрабатываем результаты
            knowledge_items = []
            if results["documents"] and results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )):
                    # Выбираем ответ на нужном языке
                    answer = metadata.get(f"answer_{language}", metadata.get("answer_ukr", ""))

                    # Создаем уникальный ID для векторного поиска (если его нет в метаданных)
                    doc_id = f"vector_{metadata.get('category', 'unknown')}_{i}"
                    metadata_with_id = dict(metadata)
                    metadata_with_id["id"] = doc_id

                    knowledge_item = {
                        "category": metadata.get("category", ""),
                        "keywords": metadata.get("keywords", ""),
                        "answer": answer,
                        "relevance_score": 1.0 - distance,  # Преобразуем distance в score
                        "metadata": metadata_with_id,
                        "search_type": "vector"
                    }
                    knowledge_items.append(knowledge_item)

            return knowledge_items

        except Exception as e:
            logger.error(f"Ошибка при векторном поиске: {e}")
            return []

    def _combine_search_results(self, keyword_results: List[Dict], vector_results: List[Dict], n_results: int) -> List[Dict]:
        """Комбинирует результаты ключевого и векторного поиска"""
        # Создаем словарь для избежания дубликатов по ID документа
        combined = {}

        # Сначала добавляем результаты поиска по ключевым словам (высокий приоритет)
        for result in keyword_results:
            doc_id = result["metadata"].get("id", "")
            if doc_id:
                # Повышаем релевантность для результатов поиска по ключевым словам
                result["relevance_score"] = result["relevance_score"] + 0.5  # Бонус за точное совпадение
                combined[doc_id] = result

        # Затем добавляем векторные результаты (если их еще нет)
        for result in vector_results:
            doc_id = result["metadata"].get("id", "")
            if doc_id and doc_id not in combined:
                combined[doc_id] = result

        # Сортируем по релевантности и возвращаем топ результаты
        final_results = list(combined.values())
        final_results.sort(key=lambda x: x["relevance_score"], reverse=True)

        return final_results[:n_results]

    def get_statistics(self) -> Dict:
        """Получает статистику базы знаний"""
        if not self.is_initialized:
            return {"error": "База знаний не инициализирована"}

        try:
            collection_count = self.collection.count()

            # Подсчитываем количество документов по категориям
            all_docs = self.collection.get(include=["metadatas"])
            category_counts = {}

            if all_docs["metadatas"]:
                for metadata in all_docs["metadatas"]:
                    category = metadata.get("category", "unknown")
                    category_counts[category] = category_counts.get(category, 0) + 1

            return {
                "total_documents": collection_count,
                "categories": category_counts,
                "csv_files_status": {
                    category: os.path.exists(path)
                    for category, path in self.csv_files.items()
                }
            }

        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {"error": str(e)}


# Глобальный экземпляр базы знаний
knowledge_base = KnowledgeBase()
