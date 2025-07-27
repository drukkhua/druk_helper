"""
Сервис аналитики для отслеживания эффективности AI бота
Собирает данные о запросах пользователей, ответах системы и пробелах в знаниях
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re

from .models import UserQuery, FeedbackEntry, KnowledgeGap, analytics_db

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Сервис для сбора и анализа данных о работе AI бота"""

    def __init__(self):
        self.db = analytics_db
        self.confidence_threshold = 0.7  # Порог для определения "хорошего" ответа
        logger.info("Analytics Service инициализирован")

    def log_user_query(self, user_id: int, query_text: str, language: str = "ukr") -> int:
        """
        Логирует пользовательский запрос (вызывается в начале обработки)

        Args:
            user_id: ID пользователя
            query_text: Текст запроса
            language: Язык запроса

        Returns:
            ID записи в базе данных
        """
        query = UserQuery(
            user_id=user_id, query_text=query_text, language=language, timestamp=datetime.now()
        )

        query_id = self.db.save_user_query(query)
        logger.debug(f"Запрос пользователя {user_id} залогирован с ID {query_id}")
        return query_id

    def log_ai_response(
        self,
        query_id: int,
        ai_response: str,
        confidence: float,
        source: str,
        should_contact_manager: bool = False,
        context_used: str = "",
        search_type: str = "",
        relevance_scores: List[float] = None,
        response_time_ms: int = 0,
    ):
        """
        Логирует ответ AI системы (вызывается после получения ответа)

        Args:
            query_id: ID запроса из log_user_query
            ai_response: Текст ответа AI
            confidence: Уверенность в ответе (0.0-1.0)
            source: Источник ответа ("ai", "template", "fallback")
            should_contact_manager: Нужно ли связаться с менеджером
            context_used: Использованный контекст из базы знаний
            search_type: Тип поиска ("keyword", "vector", "hybrid")
            relevance_scores: Скоры релевантности найденных документов
            response_time_ms: Время ответа в миллисекундах
        """
        try:
            # Обновляем существующую запись
            with self.db._get_connection() as conn:
                is_answered = confidence >= self.confidence_threshold
                relevance_json = json.dumps(relevance_scores or [])

                conn.execute(
                    """
                    UPDATE user_queries SET
                        ai_response = ?,
                        confidence = ?,
                        source = ?,
                        should_contact_manager = ?,
                        context_used = ?,
                        search_type = ?,
                        relevance_scores = ?,
                        is_answered = ?,
                        response_time_ms = ?
                    WHERE id = ?
                """,
                    (
                        ai_response,
                        confidence,
                        source,
                        should_contact_manager,
                        context_used,
                        search_type,
                        relevance_json,
                        is_answered,
                        response_time_ms,
                        query_id,
                    ),
                )
                conn.commit()

            # Если ответ плохой - логируем как пробел в знаниях
            if not is_answered:
                # Получаем информацию о запросе
                with self.db._get_connection() as conn:
                    query_row = conn.execute(
                        "SELECT query_text, language FROM user_queries WHERE id = ?", (query_id,)
                    ).fetchone()

                    if query_row:
                        self._log_knowledge_gap(query_row["query_text"], query_row["language"])

            logger.debug(
                f"AI ответ для запроса {query_id} залогирован (confidence: {confidence:.3f})"
            )

        except Exception as e:
            logger.error(f"Ошибка при логировании AI ответа: {e}")

    def log_feedback(
        self, user_id: int, query_id: Optional[int], feedback_type: str, feedback_text: str = ""
    ) -> int:
        """
        Логирует пользовательский фидбек

        Args:
            user_id: ID пользователя
            query_id: ID запроса (если есть)
            feedback_type: Тип фидбека ("helpful", "not_helpful", "suggestion")
            feedback_text: Дополнительный текст фидбека

        Returns:
            ID записи фидбека
        """
        feedback = FeedbackEntry(
            user_id=user_id,
            query_id=query_id,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
        )

        feedback_id = self.db.save_feedback(feedback)
        logger.info(f"Фидбек от пользователя {user_id} залогирован: {feedback_type}")
        return feedback_id

    def _log_knowledge_gap(self, query_text: str, language: str):
        """Логирует пробел в знаниях на основе неотвеченного запроса"""
        try:
            # Нормализуем запрос для создания паттерна
            pattern = self._normalize_query_pattern(query_text)
            category = self._classify_query_category(query_text)
            priority = self._calculate_gap_priority(query_text)

            gap = KnowledgeGap(
                query_pattern=pattern,
                category=category,
                language=language,
                priority=priority,
                status="new",
            )

            self.db.save_knowledge_gap(gap)
            logger.info(f"Пробел в знаниях залогирован: {pattern}")

        except Exception as e:
            logger.error(f"Ошибка при логировании пробела в знаниях: {e}")

    def _normalize_query_pattern(self, query: str) -> str:
        """Нормализует запрос для создания паттерна поиска"""
        # Убираем лишние символы и приводим к нижнему регистру
        pattern = re.sub(r"[^\w\s]", "", query.lower().strip())

        # Заменяем числа на плейсхолдеры
        pattern = re.sub(r"\d+", "[ЧИСЛО]", pattern)

        # Убираем лишние пробелы
        pattern = re.sub(r"\s+", " ", pattern).strip()

        return pattern

    def _classify_query_category(self, query: str) -> str:
        """Классифицирует запрос по категории"""
        query_lower = query.lower()

        category_keywords = {
            "визитки": ["визитк", "визитни", "business card"],
            "футболки": ["футболк", "майк", "t-shirt", "tshirt"],
            "листовки": ["листовк", "листівк", "flyer"],
            "наклейки": ["наклейк", "наклійк", "sticker"],
            "блокноты": ["блокнот", "блокнот", "notebook"],
            "цены": ["цена", "ціна", "стоимость", "вартість", "коштує", "стоит"],
            "сроки": ["срок", "термін", "время", "час", "быстро", "швидко"],
            "качество": ["качество", "якість", "материал", "матеріал"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return category

        return "общее"

    def _calculate_gap_priority(self, query: str) -> str:
        """Рассчитывает приоритет пробела в знаниях"""
        query_lower = query.lower()

        # Высокий приоритет - частые коммерческие запросы
        high_priority_keywords = ["цена", "ціна", "стоимость", "купить", "заказать", "срочно"]
        if any(keyword in query_lower for keyword in high_priority_keywords):
            return "high"

        # Средний приоритет - информационные запросы
        medium_priority_keywords = ["как", "что", "когда", "где", "почему"]
        if any(keyword in query_lower for keyword in medium_priority_keywords):
            return "medium"

        return "low"

    def get_analytics_summary(self, days: int = 7) -> Dict:
        """
        Получает сводку аналитики за указанный период

        Args:
            days: Количество дней для анализа

        Returns:
            Словарь с аналитическими данными
        """
        try:
            # Общая статистика
            stats = self.db.get_stats()

            # Статистика за период
            with self.db._get_connection() as conn:
                # Запросы за период
                period_stats = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total_queries,
                        COUNT(CASE WHEN is_answered = 1 THEN 1 END) as answered_queries,
                        AVG(confidence) as avg_confidence,
                        AVG(response_time_ms) as avg_response_time
                    FROM user_queries
                    WHERE timestamp >= datetime('now', '-' || ? || ' days')
                """,
                    (days,),
                ).fetchone()

                # Топ неотвеченных запросов
                unanswered = conn.execute(
                    """
                    SELECT query_text, COUNT(*) as frequency
                    FROM user_queries
                    WHERE is_answered = 0
                    AND timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY query_text
                    ORDER BY frequency DESC
                    LIMIT 10
                """,
                    (days,),
                ).fetchall()

                # Распределение по источникам
                sources = conn.execute(
                    """
                    SELECT source, COUNT(*) as count
                    FROM user_queries
                    WHERE timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY source
                """,
                    (days,),
                ).fetchall()

            # Топ пробелов в знаниях
            top_gaps = self.db.get_knowledge_gaps(limit=10)

            return {
                "period_days": days,
                "overall_stats": stats,
                "period_stats": {
                    "total_queries": period_stats["total_queries"] or 0,
                    "answered_queries": period_stats["answered_queries"] or 0,
                    "answer_rate": (
                        (period_stats["answered_queries"] / period_stats["total_queries"] * 100)
                        if period_stats["total_queries"] > 0
                        else 0
                    ),
                    "avg_confidence": round(period_stats["avg_confidence"] or 0, 3),
                    "avg_response_time_ms": round(period_stats["avg_response_time"] or 0, 1),
                },
                "top_unanswered": [
                    {"query": row["query_text"], "frequency": row["frequency"]}
                    for row in unanswered
                ],
                "source_distribution": [
                    {"source": row["source"], "count": row["count"]} for row in sources
                ],
                "knowledge_gaps": [
                    {
                        "pattern": gap.query_pattern,
                        "frequency": gap.frequency,
                        "category": gap.category,
                        "priority": gap.priority,
                    }
                    for gap in top_gaps
                ],
            }

        except Exception as e:
            logger.error(f"Ошибка при получении аналитики: {e}")
            return {"error": str(e)}

    def get_improvement_suggestions(self) -> List[Dict]:
        """Получает предложения по улучшению на основе аналитики"""
        suggestions = []

        try:
            # Анализируем топ пробелы в знаниях
            gaps = self.db.get_knowledge_gaps(limit=20)

            # Группируем по категориям
            category_gaps = {}
            for gap in gaps:
                category = gap.category or "общее"
                if category not in category_gaps:
                    category_gaps[category] = []
                category_gaps[category].append(gap)

            # Генерируем предложения
            for category, category_gaps_list in category_gaps.items():
                total_frequency = sum(gap.frequency for gap in category_gaps_list)

                if total_frequency >= 5:  # Если категория проблемная
                    suggestions.append(
                        {
                            "type": "knowledge_expansion",
                            "category": category,
                            "priority": "high" if total_frequency >= 15 else "medium",
                            "description": f"Добавить больше информации по категории '{category}' "
                            f"(найдено {len(category_gaps_list)} паттернов с {total_frequency} запросами)",
                            "examples": [gap.query_pattern for gap in category_gaps_list[:3]],
                        }
                    )

            # Анализируем общую статистику
            stats = self.db.get_stats()
            if stats["answer_rate"] < 70:
                suggestions.append(
                    {
                        "type": "general_improvement",
                        "priority": "high",
                        "description": f"Низкий процент ответов ({stats['answer_rate']:.1f}%). "
                        "Рекомендуется расширить базу знаний и улучшить алгоритмы поиска.",
                    }
                )

            if stats["avg_confidence"] < 0.6:
                suggestions.append(
                    {
                        "type": "confidence_improvement",
                        "priority": "medium",
                        "description": f"Низкая средняя уверенность ответов ({stats['avg_confidence']:.3f}). "
                        "Рекомендуется улучшить качество ключевых слов и синонимов.",
                    }
                )

            return suggestions

        except Exception as e:
            logger.error(f"Ошибка при генерации предложений: {e}")
            return []


# Глобальный экземпляр сервиса аналитики
analytics_service = AnalyticsService()
