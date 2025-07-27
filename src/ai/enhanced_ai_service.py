"""
Улучшенный AI сервис с персонализированными промптами
Расширяет базовый AIService с поддержкой персонажа "Олена"
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
from src.ai.enhanced_rag_service import enhanced_rag_service
from src.ai.conversation_memory import conversation_memory
from src.analytics.analytics_service import analytics_service
from src.managers.models import unified_db
from config import Config

logger = logging.getLogger(__name__)


class EnhancedAIService:
    """Улучшенный AI сервис с персонализацией"""

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
                logger.info("Enhanced AI Service инициализирован с реальным OpenAI API")
            except Exception as e:
                logger.error(f"Ошибка инициализации OpenAI: {e}")
                self.use_real_ai = False

        # Инициализация базы знаний
        self.knowledge_base = knowledge_base
        self.enhanced_rag = enhanced_rag_service
        self.knowledge_ready = False

        if self.enabled:
            self._init_knowledge_base()
            mode = "REAL OpenAI" if self.use_real_ai else "MOCK"
            kb_status = (
                "with Enhanced Knowledge Base" if self.knowledge_ready else "without Knowledge Base"
            )
            logger.info(
                f"Enhanced AI Service инициализирован в режиме: ENABLED ({mode}) {kb_status}"
            )
        else:
            logger.info("Enhanced AI Service инициализирован в режиме: DISABLED")

    def _init_knowledge_base(self):
        """Инициализация базы знаний"""
        try:
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

        if not self.use_real_ai:
            return True

        if not self.openai_client or not self.config.OPENAI_API_KEY:
            logger.warning("Enhanced AI Service недоступен: проблемы с OpenAI API")
            return False

        return True

    async def process_query(self, user_query: str, user_id: int, language: str = "ukr") -> Dict:
        """
        Обрабатывает запрос пользователя с персонализацией

        Args:
            user_query: Запрос пользователя
            user_id: ID пользователя
            language: Язык ответа

        Returns:
            Dict с результатом обработки
        """
        start_time = time.time()

        try:
            # Логируем аналитику
            query_id = analytics_service.log_user_query(user_id, user_query, language)

            # Добавляем в память разговора
            conversation_memory.add_user_message(user_id, user_query, language)

            # Проверяем доступность AI
            if not self.is_available():
                logger.warning("Enhanced AI недоступен, используем fallback")
                return await self._fallback_response(user_query, user_id, language)

            # Обрабатываем через улучшенный AI
            if self.use_real_ai:
                ai_result = await self._process_with_enhanced_openai(user_query, user_id, language)
            else:
                ai_result = await self._process_with_enhanced_mock(user_query, user_id, language)

            # Добавляем ответ в память разговора
            conversation_memory.add_assistant_message(
                user_id,
                ai_result["answer"],
                metadata={
                    "confidence": ai_result["confidence"],
                    "source": ai_result["source"],
                    "persona_enhanced": True,
                    "language": language,
                },
            )

            # Логируем результат
            response_time_ms = int((time.time() - start_time) * 1000)
            analytics_service.log_ai_response(
                query_id,
                ai_result["answer"],
                ai_result["confidence"],
                ai_result["source"],
                response_time_ms=response_time_ms,
            )

            # Генерируем уточняющий вопрос
            follow_up = self.enhanced_rag.generate_follow_up_question(
                user_query, {"language": language, "user_id": user_id}
            )

            if follow_up:
                ai_result["answer"] += f"\n\n❓ {follow_up}"

            ai_result["response_time_ms"] = response_time_ms
            ai_result["enhanced"] = True

            return ai_result

        except Exception as e:
            logger.error(f"Ошибка обработки запроса (Enhanced): {e}")
            response_time_ms = int((time.time() - start_time) * 1000)

            # Возвращаем fallback ответ
            return {
                "answer": (
                    "Вибачте, виникла помилка. Спробуйте ще раз або зв'яжіться з менеджером."
                    if language == "ukr"
                    else "Извините, возникла ошибка. Попробуйте еще раз или свяжитесь с менеджером."
                ),
                "confidence": 0.0,
                "source": "error_fallback",
                "response_time_ms": response_time_ms,
                "enhanced": True,
                "error": str(e),
            }

    async def _process_with_enhanced_openai(
        self, user_query: str, user_id: int, language: str
    ) -> Dict:
        """Обработка через реальный OpenAI с улучшенными промптами"""
        try:
            # Получаем контекст из базы знаний
            context = await self.enhanced_rag.get_context_for_query(user_query, language)

            # Получаем информацию о пользователе для персонализации
            user_context = await self._get_user_context(user_id, user_query)

            # Создаем персонализированный системный промпт
            system_prompt = self.enhanced_rag.create_enhanced_system_prompt(
                language, context, user_context
            )

            # Получаем историю разговора
            conversation_history = conversation_memory.get_conversation_context(
                user_id, max_messages=6
            )

            # Формируем сообщения для OpenAI
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_query})

            # Вызываем OpenAI
            response = await self.openai_client.chat.completions.create(
                model=self.config.AI_MODEL,
                messages=messages,
                temperature=self.config.AI_TEMPERATURE,
                max_tokens=self.config.AI_MAX_TOKENS,
            )

            answer = response.choices[0].message.content.strip()

            # Улучшаем ответ с учетом премиального ценообразования
            try:
                from PREMIUM_PRICING_ENHANCEMENT import enhance_ai_response_with_premium_pricing

                answer = enhance_ai_response_with_premium_pricing(answer, user_query, language)
            except ImportError:
                logger.warning("Premium pricing enhancement не доступен")

            # Добавляем эмодзи если их нет
            if not any(emoji in answer for emoji in ["🔸", "📋", "👕", "📄", "💰", "⏰", "😊", "💙", "🎯"]):
                answer = f"😊 {answer}"

            # Рассчитываем уверенность
            confidence = self._calculate_enhanced_confidence(answer, context, user_query)

            logger.info(
                f"Enhanced OpenAI ответ для пользователя {user_id}: {len(answer)} символов, уверенность: {confidence:.1%}"
            )

            return {
                "answer": answer,
                "confidence": confidence,
                "source": "enhanced_openai",
                "context_used": bool(context),
                "persona_name": "Олена",
            }

        except Exception as e:
            logger.error(f"Ошибка Enhanced OpenAI: {e}")
            raise

    async def _process_with_enhanced_mock(
        self, user_query: str, user_id: int, language: str
    ) -> Dict:
        """Mock режим с улучшенными ответами"""
        try:
            # Получаем контекст из базы знаний
            context = await self.enhanced_rag.get_context_for_query(user_query, language)

            if context:
                if language == "ukr":
                    base_answer = f"Ось що можу розповісти з досвіду:\n\n{context}"
                else:
                    base_answer = f"Вот что могу рассказать из опыта:\n\n{context}"
                confidence = 0.8
            else:
                if language == "ukr":
                    base_answer = "На жаль, не маю точної інформації з цього питання. Зв'яжіться з нашим менеджером для детальної консультації!"
                else:
                    base_answer = "К сожалению, не имею точной информации по этому вопросу. Свяжитесь с нашим менеджером для детальной консультации!"
                confidence = 0.3

            # Добавляем персональные элементы
            user_context = await self._get_user_context(user_id, user_query)
            if user_context.get("is_returning_user"):
                if language == "ukr":
                    base_answer = f"Привіт знову! 😊 Радий, що повертаєтесь.\n\n{base_answer}"
                else:
                    base_answer = f"Привет снова! 😊 Рада, что возвращаетесь.\n\n{base_answer}"

            # Улучшаем ответ с учетом премиального ценообразования
            try:
                from PREMIUM_PRICING_ENHANCEMENT import enhance_ai_response_with_premium_pricing

                base_answer = enhance_ai_response_with_premium_pricing(
                    base_answer, user_query, language
                )
            except ImportError:
                logger.warning("Premium pricing enhancement не доступен")

            # Добавляем подпись Олены
            if language == "ukr":
                base_answer += "\n\n💙 З повагою, Олена"
            else:
                base_answer += "\n\n💙 С уважением, Олена"

            return {
                "answer": base_answer,
                "confidence": confidence,
                "source": "enhanced_mock",
                "context_used": bool(context),
                "persona_name": "Олена",
            }

        except Exception as e:
            logger.error(f"Ошибка Enhanced Mock: {e}")
            raise

    async def _get_user_context(self, user_id: int, current_message: str) -> Dict:
        """Получает контекст о пользователе для персонализации"""
        try:
            # Базовый контекст
            context = {
                "user_id": user_id,
                "last_message": current_message,
                "is_returning_user": False,
                "total_messages": 0,
                "favorite_category": None,
            }

            # Получаем статистику пользователя
            stats = unified_db.get_user_stats_summary(user_id)
            if stats:
                context.update(
                    {
                        "is_returning_user": stats.get("total_messages", 0) > 1,
                        "total_messages": stats.get("total_messages", 0),
                        "favorite_category": stats.get("top_category"),
                    }
                )

            return context

        except Exception as e:
            logger.error(f"Ошибка получения контекста пользователя: {e}")
            return {"user_id": user_id, "last_message": current_message}

    def _calculate_enhanced_confidence(self, answer: str, context: str, query: str) -> float:
        """Рассчитывает уверенность для улучшенного ответа"""
        confidence = 0.5  # Базовая уверенность

        # Увеличиваем уверенность если есть контекст
        if context:
            confidence += 0.3

        # Увеличиваем если ответ содержит конкретную информацию
        if any(word in answer.lower() for word in ["грн", "день", "час", "размер", "розмір"]):
            confidence += 0.2

        # Уменьшаем если ответ слишком общий
        if any(phrase in answer.lower() for phrase in ["зв'яжіться", "свяжитесь", "уточните"]):
            confidence -= 0.1

        # Увеличиваем за персональные элементы
        if any(word in answer.lower() for word in ["олена", "досвід", "опыт", "пам'ятаю", "помню"]):
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    async def _fallback_response(self, user_query: str, user_id: int, language: str) -> Dict:
        """Fallback ответ при недоступности AI"""
        if language == "ukr":
            answer = "Вибачте, зараз я не можу дати повну відповідь. Зв'яжіться з нашим менеджером для детальної консультації!"
        else:
            answer = "Извините, сейчас не могу дать полный ответ. Свяжитесь с нашим менеджером для детальной консультации!"

        return {
            "answer": answer,
            "confidence": 0.1,
            "source": "fallback",
            "enhanced": True,
            "response_time_ms": 100,
        }

    def get_service_info(self) -> Dict:
        """Возвращает информацию о сервисе"""
        return {
            "service_type": "Enhanced AI Service",
            "persona_enabled": True,
            "persona_name": "Олена",
            "ai_enabled": self.enabled,
            "real_ai": self.use_real_ai,
            "knowledge_ready": self.knowledge_ready,
            "model": self.config.AI_MODEL if self.use_real_ai else "Mock",
        }


# Глобальный экземпляр улучшенного AI сервиса
enhanced_ai_service = EnhancedAIService()
