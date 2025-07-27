#!/usr/bin/env python3
"""
Интеграционные тесты для проверки основной функциональности после реструктуризации
"""

import pytest
import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIntegration:
    """Интеграционные тесты системы"""

    def test_core_imports(self):
        """Тест импорта основных компонентов"""
        try:
            from src.ai.service import ai_service
            from src.core.template_manager import TemplateManager
            from src.bot.keyboards import create_main_menu_keyboard
            from src.core.business_hours import get_business_status
            from src.utils.error_handler import handle_exceptions
            from src.utils.exceptions import ConfigurationError

            assert ai_service is not None
            assert TemplateManager is not None
            assert create_main_menu_keyboard is not None
            assert get_business_status is not None
            assert handle_exceptions is not None
            assert ConfigurationError is not None

        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_template_manager_basic(self):
        """Тест базовой функциональности TemplateManager"""
        try:
            from src.core.template_manager import TemplateManager

            tm = TemplateManager()
            tm.reload_templates()

            # Проверяем, что шаблоны загрузились
            assert len(tm.templates) > 0

            # Проверяем, что есть ожидаемые категории
            expected_categories = ["визитки", "футболки", "листовки", "наклейки", "блокноты"]
            for category in expected_categories:
                assert category in tm.templates, f"Category {category} not found"

        except Exception as e:
            pytest.fail(f"Template Manager test failed: {e}")

    @pytest.mark.asyncio
    async def test_ai_service_basic(self):
        """Тест базовой функциональности AI сервиса"""
        try:
            from src.ai.service import ai_service

            # Проверяем, что AI сервис инициализирован
            assert ai_service is not None
            # Проверяем доступность сервиса (независимо от включенности AI)
            assert hasattr(ai_service, "enabled")
            assert hasattr(ai_service, "is_available")

            # Тест обработки запроса
            result = await ai_service.process_query("Скільки коштують візитки?", 12345, "ukr")

            assert isinstance(result, dict)
            assert "success" in result
            assert "answer" in result
            assert "confidence" in result
            assert "source" in result

            # Проверяем что получили какой-то ответ
            if result["success"]:
                assert len(result["answer"]) > 0
                assert result["source"] in ["ai", "template", "fallback"]

        except Exception as e:
            pytest.fail(f"AI Service test failed: {e}")

    def test_business_hours(self):
        """Тест модуля рабочих часов"""
        try:
            from src.core.business_hours import get_business_status, is_business_time

            status = get_business_status("ukr")
            assert isinstance(status, str)
            assert len(status) > 0

            is_business = is_business_time()
            assert isinstance(is_business, bool)

        except Exception as e:
            pytest.fail(f"Business Hours test failed: {e}")

    def test_keyboard_creation(self):
        """Тест создания клавиатур"""
        try:
            from src.bot.keyboards import create_main_menu_keyboard, get_category_title
            from unittest.mock import Mock

            # Mock template manager
            mock_tm = Mock()
            mock_tm.get_user_language.return_value = "ukr"

            # Тест создания главного меню
            keyboard = create_main_menu_keyboard(12345, mock_tm)
            assert keyboard is not None

            # Тест получения заголовка категории
            title = get_category_title("визитки", "ukr")
            assert title == "📇 Візитки"

        except Exception as e:
            pytest.fail(f"Keyboard test failed: {e}")

    @pytest.mark.asyncio
    async def test_full_ai_pipeline(self):
        """Полный тест AI pipeline"""
        try:
            from src.ai.service import ai_service

            # Тестовые запросы
            test_queries = [
                ("Які терміни виготовлення футболок?", "ukr"),
                ("Скільки коштують візитки?", "ukr"),
                ("Сколько стоят визитки?", "rus"),
                ("What is the price?", "ukr"),  # Should fallback
            ]

            results = []
            for query, lang in test_queries:
                result = await ai_service.process_query(query, 12345, lang)
                results.append(result)

                # Базовые проверки
                assert isinstance(result, dict)
                assert "success" in result
                assert "answer" in result

            # Проверяем, что хотя бы некоторые запросы обработаны (успешно или с fallback)
            processed = [
                r for r in results if r["success"] or ("answer" in r and len(r["answer"]) > 0)
            ]
            assert (
                len(processed) >= 2
            ), f"Too few processed responses. Got {len(processed)} out of {len(results)}"

        except Exception as e:
            pytest.fail(f"Full AI pipeline test failed: {e}")

    def test_configuration_loading(self):
        """Тест загрузки конфигурации"""
        try:
            from config import Config

            config = Config()

            # Проверяем основные настройки
            assert hasattr(config, "BOT_TOKEN")
            assert hasattr(config, "AI_ENABLED")
            assert hasattr(config, "OPENAI_API_KEY")

            # Проверяем что AI_ENABLED имеет корректное значение (True или False)
            assert isinstance(config.AI_ENABLED, bool)

        except Exception as e:
            pytest.fail(f"Configuration test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
