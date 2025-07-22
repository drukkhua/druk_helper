"""
AI сервис для обработки запросов пользователей с использованием RAG
Retrieval-Augmented Generation с векторным поиском по базе знаний
"""

import logging
from typing import Dict

from business_hours import is_business_time
from config import Config


logger = logging.getLogger(__name__)


class AIService:
    """Сервис для AI-обработки запросов пользователей"""

    def __init__(self):
        self.config = Config()
        self.enabled = self.config.AI_ENABLED
        self.fallback_to_templates = self.config.AI_FALLBACK_TO_TEMPLATES

        # Пока что заглушки - будем реализовывать пошагово
        self.vector_store = None
        self.llm = None
        self.embeddings = None

        if self.enabled:
            logger.info("AI Service инициализирован в режиме: ENABLED")
        else:
            logger.info("AI Service инициализирован в режиме: DISABLED (fallback to templates)")

    def is_available(self) -> bool:
        """Проверяет доступность AI сервиса"""
        if not self.enabled:
            return False

        # Проверяем наличие API ключа
        if not self.config.OPENAI_API_KEY:
            logger.warning("AI Service недоступен: отсутствует OPENAI_API_KEY")
            return False

        # В будущем здесь будем проверять векторную БД и другие компоненты
        return True

    async def process_query(self, user_query: str, user_id: int, language: str = "ukr") -> Dict:
        """
        Обрабатывает запрос пользователя

        Args:
            user_query: Текст запроса пользователя
            user_id: ID пользователя
            language: Язык ответа ("ukr" или "rus")

        Returns:
            Dict с результатом обработки:
            {
                "success": bool,
                "answer": str,
                "confidence": float,
                "source": str,  # "ai" или "template" или "fallback"
                "should_contact_manager": bool
            }
        """
        try:
            logger.info(f"Обработка AI запроса от пользователя {user_id}: {user_query[:100]}...")

            # Если AI отключен, сразу возвращаем fallback
            if not self.is_available():
                return self._create_fallback_response(language)

            # TODO: Здесь будет основная AI логика
            # 1. Векторный поиск по базе знаний
            # 2. Проверка релевантности
            # 3. Генерация ответа через LLM
            # 4. Постобработка

            # Пока что возвращаем заглушку
            return self._create_mock_ai_response(user_query, language)

        except Exception as e:
            logger.error(f"Ошибка при обработке AI запроса: {e}")
            return self._create_fallback_response(language, error=True)

    def _create_mock_ai_response(self, query: str, language: str) -> Dict:
        """Временная заглушка для AI ответа"""
        # Простейшая логика для демонстрации
        query_lower = query.lower()

        # Расширенные ключевые слова для лучшего поиска
        keywords_map = {
            "ukr": {
                "price": [
                    "ціна",
                    "цін",
                    "коштує",
                    "коштують",
                    "стоїть",
                    "стоять",
                    "вартість",
                    "тариф",
                ],
                "design": ["макет", "дизайн", "файл", "psd", "ai", "pdf", "png"],
                "timeline": [
                    "терміни",
                    "термін",
                    "час",
                    "швидко",
                    "скоро",
                    "виготовлення",
                    "готовий",
                    "готові",
                ],
                "quality": ["якість", "матеріал", "друк", "поліграфія", "качество"],
                "tshirts": ["футболка", "футболки", "майка", "майки", "одяг"],
            },
            "rus": {
                "price": ["цена", "цен", "стоит", "стоят", "стоимость", "тариф"],
                "design": ["макет", "дизайн", "файл", "psd", "ai", "pdf", "png"],
                "timeline": [
                    "сроки",
                    "срок",
                    "время",
                    "быстро",
                    "скоро",
                    "изготовление",
                    "готов",
                    "готовы",
                ],
                "quality": ["качество", "материал", "печать", "полиграфия"],
                "tshirts": ["футболка", "футболки", "майка", "майки", "одежда"],
            },
        }

        mock_responses = {
            "ukr": {
                "price": "🔸 Ціни на нашу продукцію залежать від тиражу та складності.\n\n"
                "📋 Візитки: від 50 грн за 100 шт\n"
                "👕 Футболки: від 200 грн\n"
                "📄 Листівки: від 80 грн за 100 шт\n\n"
                "📞 Для точного розрахунку зверніться до менеджера!",
                "design": "🎨 Щодо макетів:\n\n"
                "✅ Приймаємо файли: AI, PSD, PDF, PNG (300+ dpi)\n"
                "✅ Безкоштовна корекція макету\n"
                "✅ Можемо створити макет з нуля\n\n"
                "📞 Надішліть ваш макет менеджеру для перевірки!",
                "timeline": "⏰ Терміни виготовлення:\n\n"
                "📋 Візитки: 1-2 дні\n"
                "👕 Футболки: 2-3 дні\n"
                "📄 Листівки: 1-2 дні\n\n"
                "⚡ Є експрес-виготовлення за доплату!",
                "tshirts": "👕 Про футболки:\n\n"
                "💰 Ціна: від 200 грн\n"
                "⏰ Терміни: 2-3 дні\n"
                "🎨 Друк: цифровий, шовкографія\n"
                "📏 Розміри: XS-5XL\n\n"
                "📞 Для детальної консультації зверніться до менеджера!",
                "quality": "🏆 Якість нашої продукції:\n\n"
                "✅ Преміум матеріали\n"
                "✅ Професійне обладнання\n"
                "✅ Контроль якості на всіх етапах\n"
                "✅ Гарантія на всі роботи\n\n"
                "📞 Маємо сертифікати якості - питайте у менеджера!",
            },
            "rus": {
                "price": "🔸 Цены на нашу продукцию зависят от тиража и сложности.\n\n"
                "📋 Визитки: от 50 грн за 100 шт\n"
                "👕 Футболки: от 200 грн\n"
                "📄 Листовки: от 80 грн за 100 шт\n\n"
                "📞 Для точного расчета обратитесь к менеджеру!",
                "design": "🎨 По макетам:\n\n"
                "✅ Принимаем файлы: AI, PSD, PDF, PNG (300+ dpi)\n"
                "✅ Бесплатная коррекция макета\n"
                "✅ Можем создать макет с нуля\n\n"
                "📞 Отправьте ваш макет менеджеру для проверки!",
                "timeline": "⏰ Сроки изготовления:\n\n"
                "📋 Визитки: 1-2 дня\n"
                "👕 Футболки: 2-3 дня\n"
                "📄 Листовки: 1-2 дня\n\n"
                "⚡ Есть экспресс-изготовление за доплату!",
                "tshirts": "👕 О футболках:\n\n"
                "💰 Цена: от 200 грн\n"
                "⏰ Сроки: 2-3 дня\n"
                "🎨 Печать: цифровая, шелкография\n"
                "📏 Размеры: XS-5XL\n\n"
                "📞 Для детальной консультации обратитесь к менеджеру!",
                "quality": "🏆 Качество нашей продукции:\n\n"
                "✅ Премиум материалы\n"
                "✅ Профессиональное оборудование\n"
                "✅ Контроль качества на всех этапах\n"
                "✅ Гарантия на все работы\n\n"
                "📞 У нас есть сертификаты качества - спрашивайте у менеджера!",
            },
        }

        # Ищем подходящий ответ с новой логикой
        keywords = keywords_map.get(language, keywords_map["ukr"])
        responses = mock_responses.get(language, mock_responses["ukr"])

        # Проверяем по каждой категории ключевых слов
        for response_type, word_list in keywords.items():
            for word in word_list:
                if word in query_lower:
                    response = responses.get(response_type)
                    if response:
                        return {
                            "success": True,
                            "answer": response,
                            "confidence": 0.90,  # Высокая уверенность для mock
                            "source": "ai",
                            "should_contact_manager": False,
                        }

        # Если не нашли подходящий ответ
        return self._create_fallback_response(language)

    def _create_fallback_response(self, language: str, error: bool = False) -> Dict:
        """Создает fallback ответ когда AI не может помочь"""
        is_work_time = is_business_time()

        if language == "ukr":
            if error:
                base_msg = "😔 Вибачте, сталася технічна помилка з AI-помічником.\n\n"
            else:
                base_msg = "🤔 На жаль, я не знайшов точної відповіді на ваше питання.\n\n"

            if is_work_time:
                msg = base_msg + "📞 Наш менеджер зараз онлайн і обов'язково вам допоможе!"
            else:
                msg = base_msg + "📞 Наш менеджер зв'яжеться з вами найближчим часом!"
        else:
            if error:
                base_msg = "😔 Извините, произошла техническая ошибка с AI-помощником.\n\n"
            else:
                base_msg = "🤔 К сожалению, я не нашел точного ответа на ваш вопрос.\n\n"

            if is_work_time:
                msg = base_msg + "📞 Наш менеджер сейчас онлайн и обязательно вам поможет!"
            else:
                msg = base_msg + "📞 Наш менеджер свяжется с вами в ближайшее время!"

        return {
            "success": False,
            "answer": msg,
            "confidence": 0.0,
            "source": "fallback",
            "should_contact_manager": True,
        }


# Глобальный экземпляр для использования в приложении
ai_service = AIService()


async def process_user_query(user_query: str, user_id: int, language: str = "ukr") -> Dict:
    """Упрощенная функция для обработки запросов"""
    return await ai_service.process_query(user_query, user_id, language)
