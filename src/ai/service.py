"""
AI сервис для обработки запросов пользователей с использованием RAG
Retrieval-Augmented Generation с векторным поиском по базе знаний
"""

import logging
import asyncio
import time
from typing import Dict, Optional

try:
    import openai
    from openai import AsyncOpenAI
except ImportError:
    openai = None
    AsyncOpenAI = None

from src.core.business_hours import is_business_time
from src.ai.knowledge_base import knowledge_base
from src.ai.rag_service import rag_service
from src.ai.conversation_memory import conversation_memory
from src.analytics.analytics_service import analytics_service
from config import Config


logger = logging.getLogger(__name__)


class AIService:
    """Сервис для AI-обработки запросов пользователей"""

    def __init__(self):
        self.config = Config()
        self.enabled = self.config.AI_ENABLED
        self.fallback_to_templates = self.config.AI_FALLBACK_TO_TEMPLATES

        # Инициализация OpenAI клиента
        self.openai_client: Optional[AsyncOpenAI] = None
        self.use_real_ai = False

        if self.enabled and openai and self.config.OPENAI_API_KEY:
            try:
                self.openai_client = AsyncOpenAI(api_key=self.config.OPENAI_API_KEY, timeout=30.0)
                self.use_real_ai = True
                logger.info("AI Service инициализирован с реальным OpenAI API")
            except Exception as e:
                logger.error(f"Ошибка инициализации OpenAI: {e}")
                self.use_real_ai = False
                logger.info("AI Service работает в mock режиме")

        # Инициализация базы знаний
        self.knowledge_base = knowledge_base
        self.knowledge_ready = False

        if self.enabled:
            # Загружаем базу знаний в фоновом режиме
            self._init_knowledge_base()
            mode = "REAL OpenAI" if self.use_real_ai else "MOCK"
            kb_status = "with Knowledge Base" if self.knowledge_ready else "without Knowledge Base"
            logger.info(f"AI Service инициализирован в режиме: ENABLED ({mode}) {kb_status}")
        else:
            logger.info("AI Service инициализирован в режиме: DISABLED (fallback to templates)")

    def _init_knowledge_base(self):
        """Инициализация базы знаний"""
        try:
            # Загружаем векторную базу знаний
            success = self.knowledge_base.populate_vector_store()
            if success:
                self.knowledge_ready = True
                stats = self.knowledge_base.get_statistics()
                logger.info(f"База знаний готова: {stats.get('total_documents', 0)} документов")
            else:
                logger.warning("Не удалось инициализировать базу знаний")
        except Exception as e:
            logger.error(f"Ошибка инициализации базы знаний: {e}")

    def is_available(self) -> bool:
        """Проверяет доступность AI сервиса"""
        if not self.enabled:
            return False

        # Для mock режима всегда доступен
        if not self.use_real_ai:
            return True

        # Для реального AI проверяем клиент
        if not self.openai_client or not self.config.OPENAI_API_KEY:
            logger.warning("AI Service недоступен: проблемы с OpenAI API")
            return False

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
        start_time = time.time()
        query_id = None

        try:
            logger.info(f"Обработка AI запроса от пользователя {user_id}: {user_query[:100]}...")

            # 1. Логируем начало обработки запроса
            query_id = analytics_service.log_user_query(user_id, user_query, language)

            # Добавляем сообщение пользователя в память
            conversation_memory.add_user_message(user_id, user_query, language)

            # Если AI отключен, сразу возвращаем fallback
            if not self.is_available():
                result = self._create_fallback_response(language)
                self._log_response_analytics(query_id, result, start_time)
                return result

            # Если используем реальный AI - пробуем его
            if self.use_real_ai:
                ai_result = await self._process_with_openai(user_query, user_id, language)
                if ai_result["success"]:
                    # Сохраняем ответ ассистента в память
                    conversation_memory.add_assistant_message(user_id, ai_result["answer"])
                    self._log_response_analytics(query_id, ai_result, start_time)
                    return ai_result
                else:
                    logger.warning("OpenAI запрос неуспешен, переходим на mock")

            # Fallback на mock ответы
            mock_result = self._create_mock_ai_response(user_query, language)
            if mock_result["success"]:
                # Сохраняем mock ответ в память
                conversation_memory.add_assistant_message(user_id, mock_result["answer"])

            self._log_response_analytics(query_id, mock_result, start_time)
            return mock_result

        except Exception as e:
            logger.error(f"Ошибка при обработке AI запроса: {e}")
            result = self._create_fallback_response(language, error=True)
            if query_id:
                self._log_response_analytics(query_id, result, start_time)
            return result

    async def _process_with_openai(self, user_query: str, user_id: int, language: str) -> Dict:
        """Обработка запроса через реальный OpenAI API с использованием базы знаний"""
        start_time = time.time()
        try:
            context = await rag_service.get_context_for_query(user_query, language)

            # Создаем системный промпт с контекстом из базы знаний
            system_prompt = rag_service.create_system_prompt(language, context)

            # Получаем историю разговора
            conversation_history = conversation_memory.get_conversation_context(
                user_id, max_messages=6
            )

            # Формируем сообщения для OpenAI
            messages = [{"role": "system", "content": system_prompt}]

            # Добавляем историю разговора (если есть)
            if conversation_history:
                # Добавляем предыдущие сообщения, исключая текущий запрос пользователя
                for msg in conversation_history[
                    :-1
                ]:  # Исключаем последнее сообщение (текущий запрос)
                    messages.append(msg)

            # Добавляем текущий запрос
            messages.append({"role": "user", "content": user_query})

            # Выполняем запрос к OpenAI
            response = await self.openai_client.chat.completions.create(
                model=self.config.AI_MODEL,
                messages=messages,
                max_tokens=self.config.AI_MAX_TOKENS,
                temperature=self.config.AI_TEMPERATURE,
                timeout=30.0,
            )

            if response.choices and response.choices[0].message:
                answer = response.choices[0].message.content.strip()

                # Логируем успешный запрос
                logger.info(f"OpenAI успешно ответил на запрос: {user_query[:50]}...")

                # Добавляем эмодзи и форматирование если их нет
                if not any(emoji in answer for emoji in ["🔸", "📋", "👕", "📄", "💰", "⏰"]):
                    answer = f"🤖 {answer}"

                response_time_ms = int((time.time() - start_time) * 1000)

                return {
                    "success": True,
                    "answer": answer,
                    "confidence": 0.95,  # Высокая уверенность для реального AI
                    "source": "ai",
                    "should_contact_manager": False,
                    "context_used": context,
                    "search_type": "hybrid",
                    "response_time_ms": response_time_ms,
                }
            else:
                logger.warning("OpenAI вернул пустой ответ")
                return {"success": False, "answer": "", "confidence": 0.0, "source": "ai"}

        except Exception as e:
            logger.error(f"Ошибка запроса к OpenAI: {e}")
            return {"success": False, "answer": str(e), "confidence": 0.0, "source": "ai"}

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

    def _log_response_analytics(self, query_id: Optional[int], result: Dict, start_time: float):
        """Логирует аналитику ответа"""
        if not query_id:
            return

        try:
            response_time_ms = int((time.time() - start_time) * 1000)

            analytics_service.log_ai_response(
                query_id=query_id,
                ai_response=result.get("answer", ""),
                confidence=result.get("confidence", 0.0),
                source=result.get("source", "unknown"),
                should_contact_manager=result.get("should_contact_manager", False),
                context_used=result.get("context_used", ""),
                search_type=result.get("search_type", ""),
                relevance_scores=result.get("relevance_scores", []),
                response_time_ms=response_time_ms,
            )
        except Exception as e:
            logger.error(f"Ошибка при логировании аналитики: {e}")


# Глобальный экземпляр для использования в приложении
ai_service = AIService()


async def process_user_query(user_query: str, user_id: int, language: str = "ukr") -> Dict:
    """Упрощенная функция для обработки запросов"""
    return await ai_service.process_query(user_query, user_id, language)
