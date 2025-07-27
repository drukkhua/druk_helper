"""
Сервис быстрых исправлений через Telegram для администраторов
Позволяет оперативно исправлять ответы AI и обновлять базу знаний
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

from src.ai.knowledge_base import knowledge_base
from src.analytics.analytics_service import analytics_service

logger = logging.getLogger(__name__)


class QuickCorrectionsService:
    """Сервис для быстрых исправлений AI ответов администраторами"""

    def __init__(self):
        self.knowledge_base = knowledge_base
        self.analytics = analytics_service

        # Временное хранение для процесса исправлений
        self.correction_sessions = {}  # user_id -> correction_data

        # Временное хранение для callback данных (query -> session_id)
        self.callback_sessions = {}  # callback_id -> query_data

        logger.info("Quick Corrections Service инициализирован")

    def start_correction_session(
        self, admin_user_id: int, original_query: str, original_answer: str
    ) -> str:
        """
        Начинает сессию исправления ответа

        Args:
            admin_user_id: ID администратора
            original_query: Оригинальный запрос пользователя
            original_answer: Оригинальный ответ AI

        Returns:
            session_id для отслеживания сессии
        """
        session_id = f"correction_{admin_user_id}_{int(time.time())}"

        self.correction_sessions[admin_user_id] = {
            "session_id": session_id,
            "original_query": original_query,
            "original_answer": original_answer,
            "started_at": datetime.now(),
            "status": "waiting_for_correction",
        }

        logger.info(f"Начата сессия исправления {session_id} для админа {admin_user_id}")
        return session_id

    def process_correction(self, admin_user_id: int, corrected_answer: str) -> Dict:
        """
        Обрабатывает исправленный ответ от администратора

        Args:
            admin_user_id: ID администратора
            corrected_answer: Исправленный ответ

        Returns:
            Результат обработки исправления
        """
        if admin_user_id not in self.correction_sessions:
            return {
                "success": False,
                "error": "Сессия исправления не найдена. Начните процесс заново.",
            }

        session = self.correction_sessions[admin_user_id]
        original_query = session["original_query"]

        try:
            # 1. Определяем категорию для запроса
            category = self._classify_query_category(original_query)

            # 2. Создаем новую запись для базы знаний
            extracted_keywords = self._extract_keywords_from_query(original_query)
            suggested_keywords = self.suggest_additional_keywords(original_query, category)

            # Комбинируем извлеченные и предложенные ключевые слова
            all_keywords = extracted_keywords
            if suggested_keywords:
                # Добавляем только релевантные предложенные ключевые слова
                relevant_suggested = [
                    kw
                    for kw in suggested_keywords[:5]
                    if kw.lower() in original_query.lower()
                    or kw.lower() in corrected_answer.lower()
                ]
                if relevant_suggested:
                    all_keywords += ", " + ", ".join(relevant_suggested)

            new_entry = {
                "category": category,
                "subcategory": "admin_correction",
                "button_text": f"Исправление: {original_query[:30]}...",
                "keywords": all_keywords,
                "answer_ukr": (
                    corrected_answer if self._detect_language(corrected_answer) == "ukr" else ""
                ),
                "answer_rus": (
                    corrected_answer if self._detect_language(corrected_answer) == "rus" else ""
                ),
                "sort_order": "999",
            }

            # 3. Добавляем в временное хранилище (позже можно синхронизировать с Google Sheets)
            result = self._add_to_knowledge_base(new_entry)

            if result["success"]:
                # Обновляем сессию
                session["status"] = "completed"
                session["corrected_answer"] = corrected_answer
                session["category"] = category
                session["completed_at"] = datetime.now()

                # Логируем в аналитику как улучшение
                self._log_correction_analytics(
                    admin_user_id, original_query, corrected_answer, category
                )

                return {
                    "success": True,
                    "message": f"✅ Исправление добавлено в категорию '{category}'",
                    "category": category,
                    "keywords": new_entry["keywords"],
                    "session_id": session["session_id"],
                }
            else:
                return {
                    "success": False,
                    "error": f"Ошибка добавления в базу знаний: {result['error']}",
                }

        except Exception as e:
            logger.error(f"Ошибка при обработке исправления от {admin_user_id}: {e}")
            return {"success": False, "error": f"Техническая ошибка: {e}"}
        finally:
            # Очищаем сессию после обработки
            if admin_user_id in self.correction_sessions:
                del self.correction_sessions[admin_user_id]

    def start_add_to_kb_session(self, admin_user_id: int, query: str) -> str:
        """
        Начинает сессию добавления нового вопроса-ответа в базу знаний

        Args:
            admin_user_id: ID администратора
            query: Запрос для добавления

        Returns:
            session_id для отслеживания сессии
        """
        session_id = f"add_kb_{admin_user_id}_{int(time.time())}"

        self.correction_sessions[admin_user_id] = {
            "session_id": session_id,
            "type": "add_to_kb",
            "query": query,
            "started_at": datetime.now(),
            "status": "waiting_for_answer",
        }

        logger.info(f"Начата сессия добавления в БЗ {session_id} для админа {admin_user_id}")
        return session_id

    def process_kb_addition(self, admin_user_id: int, answer: str) -> Dict:
        """
        Обрабатывает добавление нового вопроса-ответа в базу знаний

        Args:
            admin_user_id: ID администратора
            answer: Ответ для добавления

        Returns:
            Результат добавления
        """
        if admin_user_id not in self.correction_sessions:
            return {
                "success": False,
                "error": "Сессия добавления не найдена. Начните процесс заново.",
            }

        session = self.correction_sessions[admin_user_id]
        if session.get("type") != "add_to_kb":
            return {"success": False, "error": "Неверный тип сессии. Начните процесс заново."}

        query = session["query"]

        try:
            # Создаем новую запись
            category = self._classify_query_category(query)

            # Улучшенное извлечение ключевых слов
            extracted_keywords = self._extract_keywords_from_query(query)
            suggested_keywords = self.suggest_additional_keywords(query, category)

            # Комбинируем извлеченные и предложенные ключевые слова
            all_keywords = extracted_keywords
            if suggested_keywords:
                # Добавляем только релевантные предложенные ключевые слова
                relevant_suggested = [
                    kw
                    for kw in suggested_keywords[:5]
                    if kw.lower() in query.lower() or kw.lower() in answer.lower()
                ]
                if relevant_suggested:
                    all_keywords += ", " + ", ".join(relevant_suggested)

            new_entry = {
                "category": category,
                "subcategory": "admin_addition",
                "button_text": f"Новый: {query[:30]}...",
                "keywords": all_keywords,
                "answer_ukr": answer if self._detect_language(answer) == "ukr" else "",
                "answer_rus": answer if self._detect_language(answer) == "rus" else "",
                "sort_order": "998",
            }

            result = self._add_to_knowledge_base(new_entry)

            if result["success"]:
                session["status"] = "completed"
                session["answer"] = answer
                session["category"] = category
                session["completed_at"] = datetime.now()

                # Логируем как новое добавление
                self._log_addition_analytics(admin_user_id, query, answer, category)

                return {
                    "success": True,
                    "message": f"✅ Новый вопрос-ответ добавлен в категорию '{category}'",
                    "category": category,
                    "keywords": new_entry["keywords"],
                }
            else:
                return {"success": False, "error": f"Ошибка добавления: {result['error']}"}

        except Exception as e:
            logger.error(f"Ошибка при добавлении в БЗ от {admin_user_id}: {e}")
            return {"success": False, "error": f"Техническая ошибка: {e}"}
        finally:
            if admin_user_id in self.correction_sessions:
                del self.correction_sessions[admin_user_id]

    def get_session_status(self, admin_user_id: int) -> Optional[Dict]:
        """Получает статус текущей сессии администратора"""
        return self.correction_sessions.get(admin_user_id)

    def cancel_session(self, admin_user_id: int) -> bool:
        """Отменяет текущую сессию администратора"""
        if admin_user_id in self.correction_sessions:
            del self.correction_sessions[admin_user_id]
            return True
        return False

    def create_callback_session(
        self, admin_user_id: int, query: str, answer: str, session_type: str
    ) -> str:
        """
        Создает короткую сессию для callback данных

        Args:
            admin_user_id: ID администратора
            query: Оригинальный запрос
            answer: Ответ AI
            session_type: 'correct' или 'add'

        Returns:
            Короткий callback_id для использования в кнопках
        """
        callback_id = f"{session_type}_{admin_user_id}_{int(time.time() % 100000)}"

        self.callback_sessions[callback_id] = {
            "admin_user_id": admin_user_id,
            "query": query,
            "answer": answer,
            "session_type": session_type,
            "created_at": datetime.now(),
        }

        # Ограничиваем количество сохраненных callback сессий (очищаем старые)
        if len(self.callback_sessions) > 100:
            oldest_keys = sorted(self.callback_sessions.keys())[:50]
            for key in oldest_keys:
                del self.callback_sessions[key]

        logger.info(f"Создана callback сессия {callback_id} для админа {admin_user_id}")
        return callback_id

    def get_callback_session(self, callback_id: str) -> Optional[Dict]:
        """Получает данные callback сессии"""
        return self.callback_sessions.get(callback_id)

    def cleanup_callback_session(self, callback_id: str) -> bool:
        """Удаляет callback сессию"""
        if callback_id in self.callback_sessions:
            del self.callback_sessions[callback_id]
            return True
        return False

    def _add_to_knowledge_base(self, entry: Dict) -> Dict:
        """
        Добавляет запись в базу знаний ChromaDB

        В будущем можно интегрировать с Google Sheets
        """
        try:
            if not self.knowledge_base.is_initialized:
                return {"success": False, "error": "ChromaDB не инициализирована"}

            # Создаем уникальный ID
            entry_id = f"admin_correction_{int(time.time())}"

            # Формируем документ для ChromaDB
            search_text = f"""
            Категория: {entry['category']}
            Ключевые слова: {entry['keywords']}
            Украинский ответ: {entry['answer_ukr']}
            Русский ответ: {entry['answer_rus']}
            """.strip()

            metadata = {
                "category": entry["category"],
                "subcategory": entry["subcategory"],
                "button_text": entry["button_text"],
                "keywords": entry["keywords"],
                "answer_ukr": entry["answer_ukr"],
                "answer_rus": entry["answer_rus"],
                "sort_order": entry["sort_order"],
                "source": "admin_correction",
                "created_at": datetime.now().isoformat(),
            }

            # Добавляем в ChromaDB
            self.knowledge_base.collection.add(
                documents=[search_text], metadatas=[metadata], ids=[entry_id]
            )

            logger.info(f"Добавлена админская запись {entry_id} в категорию {entry['category']}")

            return {"success": True, "entry_id": entry_id, "category": entry["category"]}

        except Exception as e:
            logger.error(f"Ошибка добавления в ChromaDB: {e}")
            return {"success": False, "error": str(e)}

    def _classify_query_category(self, query: str) -> str:
        """Автоматически определяет категорию для запроса"""
        query_lower = query.lower()

        category_keywords = {
            "визитки": ["визитк", "business card", "візитк"],
            "футболки": ["футболк", "майк", "t-shirt", "футболк"],
            "листовки": ["листовк", "листівк", "flyer", "буклет"],
            "наклейки": ["наклейк", "наклійк", "sticker", "этикетк"],
            "блокноты": ["блокнот", "notebook", "записн"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return category

        return "общее"

    def _extract_keywords_from_query(self, query: str) -> str:
        """Извлекает ключевые слова из запроса с умным алгоритмом"""
        query_lower = query.lower()

        # Расширенный список стоп-слов
        stop_words = {
            # Украинские стоп-слова
            "що",
            "як",
            "де",
            "коли",
            "чому",
            "скільки",
            "який",
            "які",
            "кого",
            "чого",
            "можна",
            "потрібно",
            "хочу",
            "хочемо",
            "будь",
            "ласка",
            "дякую",
            "про",
            "для",
            "або",
            "але",
            "якщо",
            "коли",
            "тоді",
            "також",
            "більш",
            "менш",
            "дуже",
            "досить",
            "трохи",
            "багато",
            "мало",
            "все",
            "нічого",
            # Русские стоп-слова
            "что",
            "как",
            "где",
            "когда",
            "почему",
            "сколько",
            "какой",
            "какие",
            "кого",
            "чего",
            "можно",
            "нужно",
            "хочу",
            "хочется",
            "пожалуйста",
            "спасибо",
            "про",
            "для",
            "или",
            "но",
            "если",
            "когда",
            "тогда",
            "также",
            "более",
            "менее",
            "очень",
            "довольно",
            "немного",
            "много",
            "мало",
            "все",
            "ничего",
            # Общие предлоги и союзы
            "в",
            "на",
            "по",
            "за",
            "из",
            "от",
            "до",
            "без",
            "при",
            "под",
            "над",
            "через",
            "у",
            "к",
            "с",
            "о",
            "об",
            "и",
            "а",
            "но",
            "да",
            "или",
            "либо",
            "то",
            "не",
        }

        # Важные ключевые слова, которые НЕ должны быть исключены
        important_keywords = {
            # Продукты
            "визитки",
            "візитки",
            "футболки",
            "листовки",
            "листівки",
            "наклейки",
            "наклійки",
            "блокноты",
            "блокноти",
            "майки",
            "буклеты",
            "буклети",
            "этикетки",
            "етикетки",
            # Характеристики
            "цена",
            "ціна",
            "стоимость",
            "вартість",
            "цены",
            "ціни",
            "тариф",
            "тарифи",
            "сроки",
            "терміни",
            "время",
            "час",
            "быстро",
            "швидко",
            "скоро",
            "качество",
            "якість",
            "материал",
            "матеріал",
            "размер",
            "розмір",
            "формат",
            "дизайн",
            "макет",
            "печать",
            "друк",
            "цвет",
            "колір",
            # Количество и размеры
            "тираж",
            "тираж",
            "штук",
            "штуки",
            "экземпляры",
            "примірники",
            "100",
            "500",
            "1000",
            "грн",
            "гривен",
            "гривень",
            "рублей",
            "долларов",
            # Услуги
            "доставка",
            "доставки",
            "курьер",
            "самовывоз",
            "самовивіз",
            "изготовление",
            "виготовлення",
            "производство",
            "виробництво",
        }

        # Извлекаем все слова
        words = re.findall(r"\b\w+\b", query_lower)

        # Фильтруем ключевые слова
        keywords = []
        for word in words:
            if len(word) > 2:  # Минимум 3 символа
                # Добавляем важные слова даже если они короткие
                if word in important_keywords:
                    keywords.append(word)
                # Исключаем стоп-слова, но добавляем остальные
                elif word not in stop_words:
                    keywords.append(word)

        # Убираем дубликаты, сохраняя порядок
        unique_keywords = []
        for keyword in keywords:
            if keyword not in unique_keywords:
                unique_keywords.append(keyword)

        return ", ".join(unique_keywords[:15])  # Увеличиваем до 15 ключевых слов

    def suggest_additional_keywords(self, query: str, category: str) -> List[str]:
        """Предлагает дополнительные ключевые слова на основе категории"""
        additional_keywords = {
            "визитки": [
                "business card",
                "карточки",
                "картки",
                "контакты",
                "контакти",
                "персональные",
                "персональні",
                "корпоративные",
                "корпоративні",
                "двухсторонние",
                "двосторонні",
                "односторонние",
                "односторонні",
                "ламинация",
                "ламінація",
                "матовые",
                "матові",
                "глянцевые",
                "глянцеві",
            ],
            "футболки": [
                "t-shirt",
                "майки",
                "одежда",
                "одяг",
                "принт",
                "печать",
                "друк",
                "хлопок",
                "бавовна",
                "размеры",
                "розміри",
                "цвета",
                "кольори",
                "шелкография",
                "шовкографія",
                "термопечать",
                "термодрук",
                "вышивка",
                "вишивка",
            ],
            "листовки": [
                "флаеры",
                "флаєри",
                "буклеты",
                "буклети",
                "реклама",
                "рекламні",
                "промо",
                "акция",
                "акції",
                "скидки",
                "знижки",
                "информация",
                "інформація",
                "односторонние",
                "односторонні",
                "двухсторонние",
                "двосторонні",
            ],
            "наклейки": [
                "стикеры",
                "стікери",
                "этикетки",
                "етикетки",
                "логотип",
                "логотипи",
                "брендинг",
                "брендінг",
                "водостойкие",
                "водостійкі",
                "прозрачные",
                "прозорі",
                "круглые",
                "круглі",
                "квадратные",
                "квадратні",
                "фигурные",
                "фігурні",
            ],
            "блокноты": [
                "записные",
                "записні",
                "тетради",
                "зошити",
                "планеры",
                "планери",
                "ежедневники",
                "щоденники",
                "скрепление",
                "скріплення",
                "пружина",
                "пружини",
                "брошюровка",
                "брошурування",
                "страницы",
                "сторінки",
                "линованные",
                "лінійовані",
            ],
        }

        return additional_keywords.get(category, [])

    def get_keyword_preview(self, query: str, answer: str, category: str) -> Dict:
        """Возвращает превью ключевых слов для администратора"""
        extracted = self._extract_keywords_from_query(query)
        suggested = self.suggest_additional_keywords(query, category)

        # Релевантные предложенные ключевые слова
        relevant_suggested = [
            kw
            for kw in suggested[:5]
            if kw.lower() in query.lower() or kw.lower() in answer.lower()
        ]

        # Все дополнительные ключевые слова для показа
        additional_options = [kw for kw in suggested[:10] if kw not in relevant_suggested]

        return {
            "extracted": extracted,
            "auto_added": relevant_suggested,
            "suggestions": additional_options,
            "category": category,
        }

    def _detect_language(self, text: str) -> str:
        """Определяет язык текста (украинский или русский)"""
        ukrainian_chars = set("їієґ")
        russian_chars = set("ыъё")

        text_chars = set(text.lower())

        if ukrainian_chars.intersection(text_chars):
            return "ukr"
        elif russian_chars.intersection(text_chars):
            return "rus"
        else:
            # По умолчанию украинский
            return "ukr"

    def _log_correction_analytics(self, admin_user_id: int, query: str, answer: str, category: str):
        """Логирует исправление в аналитику"""
        try:
            # Можно добавить специальную таблицу для админских исправлений
            logger.info(
                f"Админ {admin_user_id} исправил ответ для запроса '{query[:50]}...' в категории {category}"
            )
        except Exception as e:
            logger.error(f"Ошибка логирования исправления: {e}")

    def _log_addition_analytics(self, admin_user_id: int, query: str, answer: str, category: str):
        """Логирует добавление в аналитику"""
        try:
            logger.info(
                f"Админ {admin_user_id} добавил новый Q&A для запроса '{query[:50]}...' в категории {category}"
            )
        except Exception as e:
            logger.error(f"Ошибка логирования добавления: {e}")

    def get_correction_statistics(self) -> Dict:
        """Получает статистику исправлений"""
        # Можно добавить подсчет исправлений из ChromaDB
        return {
            "total_corrections": 0,  # Пока заглушка
            "active_sessions": len(self.correction_sessions),
        }


# Глобальный экземпляр сервиса
quick_corrections_service = QuickCorrectionsService()
