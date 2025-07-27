"""
Движок умного upselling с поддержкой триггеров и динамических цен
Интегрируется с Google Sheets для управления ценами
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from src.ai.knowledge_base import knowledge_base

logger = logging.getLogger(__name__)


class UpsellTriggerAnalyzer:
    """Анализатор триггеров для upselling"""

    def __init__(self):
        # Ключевые слова для определения триггеров
        self.trigger_keywords = {
            "price": [
                "цена",
                "стоимость",
                "сколько",
                "прайс",
                "расценки",
                "тариф",
                "дешево",
                "недорого",
                "бюджет",
                "экономия",
                "скидка",
            ],
            "materials": [
                "материал",
                "бумага",
                "качество",
                "картон",
                "плотность",
                "фактура",
                "текстура",
                "прочность",
            ],
            "time": [
                "срок",
                "время",
                "быстро",
                "срочно",
                "завтра",
                "сегодня",
                "когда готово",
                "сколько дней",
                "как долго",
            ],
            "design": [
                "дизайн",
                "макет",
                "красиво",
                "оформление",
                "стиль",
                "креатив",
                "уникальный",
                "индивидуальный",
            ],
            "quantity": [
                "штук",
                "тираж",
                "количество",
                "много",
                "мало",
                "объем",
                "партия",
                "оптом",
            ],
            "quality": ["качество", "лучший", "хороший", "надежный", "долговечный"],
            "premium": [
                "премиум",
                "элитный",
                "статусный",
                "престижный",
                "эксклюзивный",
                "люкс",
                "vip",
                "высший класс",
                "топ",
                "дорогой",
                "роскошный",
            ],
            "delivery": ["доставка", "отправка", "почта", "курьер", "самовывоз", "получение"],
            "urgent": ["срочно", "очень быстро", "экспресс", "в течение дня", "немедленно"],
        }

        # Веса триггеров для расчета релевантности
        self.trigger_weights = {
            "price": 1.0,
            "materials": 0.9,
            "time": 0.8,
            "design": 0.7,
            "quantity": 0.6,
            "quality": 1.2,
            "premium": 1.5,  # Высокий вес для премиальных запросов
            "first_time": 1.1,
            "returning": 0.9,
            "price_sensitive": 0.8,
            "quality_focused": 1.3,
            "delivery": 0.7,
            "standard_order": 0.5,
            "small_quantity": 0.6,
            "large_quantity": 0.8,
            "urgent": 0.9,
            "base": 0.1,
        }

    def analyze_query_triggers(self, query: str, user_context: Dict = None) -> List[str]:
        """Анализирует запрос и определяет активные триггеры"""

        if user_context is None:
            user_context = {}

        active_triggers = []
        query_lower = query.lower()

        # Анализируем контекстные триггеры
        for trigger, keywords in self.trigger_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                active_triggers.append(trigger)

        # Поведенческие триггеры
        if user_context.get("is_first_time", False):
            active_triggers.append("first_time")

        if user_context.get("previous_orders", 0) > 0:
            active_triggers.append("returning")

        # Определяем специальные фокусы клиента
        if self._is_price_sensitive(query_lower):
            active_triggers.append("price_sensitive")
        elif self._is_quality_focused(query_lower):
            active_triggers.append("quality_focused")

        logger.info(f"Определены триггеры для запроса '{query[:50]}...': {active_triggers}")
        return active_triggers

    def _is_price_sensitive(self, query_lower: str) -> bool:
        """Определяет, чувствителен ли клиент к цене"""
        price_sensitive_words = [
            "дешево",
            "недорого",
            "бюджет",
            "экономия",
            "скидка",
            "дешевле",
            "выгодно",
            "акция",
            "минимальная цена",
        ]
        return any(word in query_lower for word in price_sensitive_words)

    def _is_quality_focused(self, query_lower: str) -> bool:
        """Определяет, фокусируется ли клиент на качестве"""
        quality_words = [
            "качество",
            "лучший",
            "премиум",
            "элитный",
            "статусный",
            "престижный",
            "эксклюзивный",
            "люкс",
            "высококачественный",
        ]
        return any(word in query_lower for word in quality_words)

    def calculate_trigger_relevance(
        self, upsell_triggers: str, active_triggers: List[str]
    ) -> float:
        """Вычисляет релевантность upselling опции для активных триггеров"""

        if not upsell_triggers or not active_triggers:
            return 0.0

        # Парсим триггеры из строки (могут быть через запятую)
        option_triggers = [t.strip() for t in upsell_triggers.split(",")]

        relevance_score = 0.0

        # Считаем совпадения триггеров
        for option_trigger in option_triggers:
            if option_trigger in active_triggers:
                weight = self.trigger_weights.get(option_trigger, 0.5)
                relevance_score += weight

        return relevance_score


class PriceFormatter:
    """Форматировщик цен с поддержкой динамических значений из Google Sheets"""

    def __init__(self):
        self.price_pattern = re.compile(r"\{(base_price|upsell_price|total_price)\}")

    def format_answer_with_prices(self, answer_template: str, price_data: Dict) -> str:
        """Форматирует ответ, подставляя актуальные цены"""

        def replace_price(match):
            price_key = match.group(1)
            price_value = price_data.get(price_key, 0)

            if isinstance(price_value, (int, float)):
                return str(int(price_value))
            return str(price_value)

        formatted_answer = self.price_pattern.sub(replace_price, answer_template)
        return formatted_answer

    def calculate_total_price(self, base_price: float, upsell_price: float) -> float:
        """Вычисляет общую стоимость с upselling"""
        return base_price + upsell_price


class UpsellEngine:
    """Основной движок upselling"""

    def __init__(self):
        self.trigger_analyzer = UpsellTriggerAnalyzer()
        self.price_formatter = PriceFormatter()
        self.knowledge_base = knowledge_base

    def search_with_upselling(
        self, query: str, user_context: Dict = None, language: str = "ukr", max_upsell: int = 2
    ) -> List[Dict]:
        """Выполняет поиск с автоматическим добавлением upselling предложений"""

        if user_context is None:
            user_context = {}

        try:
            logger.info(f"Начинаем поиск с upselling для запроса: {query[:50]}...")

            # 1. Получаем базовые результаты поиска
            base_results = self.knowledge_base.search_knowledge(query, language)

            if not base_results:
                logger.info("Базовые результаты не найдены")
                return base_results

            # 2. Анализируем триггеры из запроса
            active_triggers = self.trigger_analyzer.analyze_query_triggers(query, user_context)

            # 3. Находим релевантные upselling опции
            upsell_options = self._find_upselling_options(base_results, active_triggers, language)

            # 4. Форматируем цены в ответах
            formatted_results = self._format_results_with_prices(base_results + upsell_options)

            # 5. Сортируем и ограничиваем количество upsell предложений
            final_results = self._organize_results(formatted_results, max_upsell)

            logger.info(
                f"Найдено {len(base_results)} базовых результатов и {len(upsell_options)} upselling опций"
            )

            return final_results

        except Exception as e:
            logger.error(f"Ошибка в upselling движке: {e}")
            # В случае ошибки возвращаем базовые результаты
            return self.knowledge_base.search_knowledge(query, language)

    def _find_upselling_options(
        self, base_results: List[Dict], active_triggers: List[str], language: str
    ) -> List[Dict]:
        """Находит подходящие upselling опции"""

        if not base_results or not active_triggers:
            return []

        main_result = base_results[0]
        main_category = main_result.get("metadata", {}).get("category", "")

        if not main_category:
            return []

        # Получаем все записи для данной категории
        all_category_results = self._get_category_results(main_category, language)

        # Фильтруем потенциальные upselling опции
        upsell_candidates = []

        for result in all_category_results:
            metadata = result.get("metadata", {})
            priority = int(metadata.get("priority", 10))
            upsell_trigger = metadata.get("upsell_trigger", "")

            # Пропускаем базовые ответы (priority 10) и записи без триггеров
            if priority >= 10 or not upsell_trigger:
                continue

            # Вычисляем релевантность триггеров
            trigger_relevance = self.trigger_analyzer.calculate_trigger_relevance(
                upsell_trigger, active_triggers
            )

            if trigger_relevance > 0.3:  # Минимальный порог релевантности
                # Добавляем метаданные для upselling
                result["metadata"]["is_upselling"] = True
                result["metadata"]["trigger_relevance"] = trigger_relevance
                result["metadata"]["priority_score"] = (11 - priority) / 10.0
                result["metadata"]["final_score"] = (
                    trigger_relevance + result["metadata"]["priority_score"]
                )

                upsell_candidates.append(result)

        # Сортируем по финальному скору
        upsell_candidates.sort(key=lambda x: x["metadata"]["final_score"], reverse=True)

        return upsell_candidates

    def _get_category_results(self, category: str, language: str) -> List[Dict]:
        """Получает все результаты для определенной категории"""

        try:
            if not self.knowledge_base.is_initialized:
                return []

            # Получаем все документы категории
            all_docs = self.knowledge_base.collection.get(
                where={"category": category}, include=["documents", "metadatas"]
            )

            results = []
            if all_docs["metadatas"]:
                for i, metadata in enumerate(all_docs["metadatas"]):
                    answer_key = f"answer_{language}"
                    answer = metadata.get(answer_key, metadata.get("answer_ukr", ""))

                    result = {
                        "category": metadata.get("category", ""),
                        "keywords": metadata.get("keywords", ""),
                        "answer": answer,
                        "metadata": metadata,
                        "search_type": "category_filter",
                    }
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"Ошибка получения результатов категории {category}: {e}")
            return []

    def _format_results_with_prices(self, results: List[Dict]) -> List[Dict]:
        """Форматирует результаты, подставляя актуальные цены"""

        formatted_results = []

        for result in results:
            try:
                metadata = result.get("metadata", {})

                # Собираем данные о ценах
                price_data = {
                    "base_price": metadata.get("base_price", 0),
                    "upsell_price": metadata.get("upsell_price", 0),
                }

                # Вычисляем общую цену
                if price_data["base_price"] and price_data["upsell_price"]:
                    price_data["total_price"] = self.price_formatter.calculate_total_price(
                        float(price_data["base_price"]), float(price_data["upsell_price"])
                    )

                # Форматируем ответ с ценами
                formatted_answer = self.price_formatter.format_answer_with_prices(
                    result["answer"], price_data
                )

                formatted_result = result.copy()
                formatted_result["answer"] = formatted_answer
                formatted_result["metadata"]["formatted_prices"] = price_data

                formatted_results.append(formatted_result)

            except Exception as e:
                logger.error(f"Ошибка форматирования цен для результата: {e}")
                # В случае ошибки добавляем результат без форматирования
                formatted_results.append(result)

        return formatted_results

    def _organize_results(self, all_results: List[Dict], max_upsell: int) -> List[Dict]:
        """Организует результаты: базовые + ограниченное количество upselling"""

        base_results = [
            r for r in all_results if not r.get("metadata", {}).get("is_upselling", False)
        ]
        upsell_results = [
            r for r in all_results if r.get("metadata", {}).get("is_upselling", False)
        ]

        # Ограничиваем количество upselling предложений
        limited_upsell = upsell_results[:max_upsell]

        # Объединяем: сначала базовые, потом upselling
        final_results = base_results + limited_upsell

        return final_results

    def format_final_answer(self, results: List[Dict], language: str = "ukr") -> str:
        """Форматирует финальный ответ с upselling предложениями"""

        if not results:
            return ""

        base_results = [r for r in results if not r.get("metadata", {}).get("is_upselling", False)]
        upsell_results = [r for r in results if r.get("metadata", {}).get("is_upselling", False)]

        # Основной ответ
        main_answer = base_results[0]["answer"] if base_results else ""

        # Добавляем upselling предложения
        if upsell_results:
            upsell_header = (
                "\n\n✨ Додаткові можливості:"
                if language == "ukr"
                else "\n\n✨ Дополнительные возможности:"
            )

            upsell_text = upsell_header
            for i, option in enumerate(upsell_results, 1):
                upsell_text += f"\n• {option['answer']}"

            main_answer += upsell_text

        return main_answer

    def get_upselling_analytics(self, results: List[Dict]) -> Dict:
        """Возвращает аналитику по upselling для мониторинга"""

        base_count = len(
            [r for r in results if not r.get("metadata", {}).get("is_upselling", False)]
        )
        upsell_count = len([r for r in results if r.get("metadata", {}).get("is_upselling", False)])

        upsell_triggers = []
        for result in results:
            if result.get("metadata", {}).get("is_upselling", False):
                trigger = result.get("metadata", {}).get("upsell_trigger", "")
                if trigger:
                    upsell_triggers.extend(trigger.split(","))

        return {
            "total_results": len(results),
            "base_results": base_count,
            "upsell_results": upsell_count,
            "upsell_ratio": upsell_count / len(results) if results else 0,
            "active_triggers": list(set(upsell_triggers)),
            "timestamp": datetime.now().isoformat(),
        }


# Глобальный экземпляр движка upselling
upsell_engine = UpsellEngine()
