"""
Тесты для handlers
Тестирование обработчиков команд и callback'ов бота
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from handlers import (
    cmd_reload,
    cmd_start,
    cmd_stats,
    process_category_selection,
    process_template_selection,
)


class TestHandlers:
    """Тесты для обработчиков бота"""

    @pytest.mark.asyncio
    async def test_cmd_start_new_user(self, mock_telegram_message):
        """Тест команды /start для нового пользователя"""
        mock_telegram_message.answer = AsyncMock()

        with patch("handlers.create_main_menu_keyboard") as mock_keyboard:
            mock_keyboard.return_value = Mock()
            mock_template_manager = Mock()
            mock_template_manager.get_user_language.return_value = "ukr"
            await cmd_start(mock_telegram_message, Mock(), mock_template_manager)

            mock_telegram_message.answer.assert_called_once()
            # Проверяем, что был вызван с клавиатурой
            call_args = mock_telegram_message.answer.call_args
            assert "reply_markup" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_cmd_start_admin_user(self, mock_telegram_message, mock_config):
        """Тест команды /start для админа"""
        mock_telegram_message.from_user.id = 123456789  # ID админа
        mock_telegram_message.answer = AsyncMock()

        with patch("handlers.create_main_menu_keyboard") as mock_keyboard:
            mock_keyboard.return_value = Mock()
            mock_template_manager = Mock()
            mock_template_manager.get_user_language.return_value = "ukr"
            await cmd_start(mock_telegram_message, Mock(), mock_template_manager)

            mock_telegram_message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_stats_admin(self, mock_telegram_message, mock_config):
        """Тест команды /stats для админа"""
        mock_telegram_message.from_user.id = 123456789  # ID админа
        mock_telegram_message.answer = AsyncMock()

        mock_stats_text = "Статистика за 7 дней:\n📇 Визитки: 10 просмотров"

        mock_stats_manager = Mock()
        mock_stats_manager.get_stats_summary.return_value = mock_stats_text
        mock_tm = Mock()
        mock_tm.stats = mock_stats_manager

        with patch("handlers.ADMIN_USER_IDS", [123456789]):
            await cmd_stats(mock_telegram_message, mock_tm)

            mock_telegram_message.answer.assert_called_once()
            call_args = mock_telegram_message.answer.call_args[0][0]
            assert "Статистика" in call_args

    @pytest.mark.asyncio
    async def test_cmd_stats_non_admin(self, mock_telegram_message, mock_config):
        """Тест команды /stats для обычного пользователя"""
        mock_telegram_message.from_user.id = 999999999  # Не админ
        mock_telegram_message.answer = AsyncMock()

        with patch("handlers.ADMIN_USER_IDS", [123456789]):
            await cmd_stats(mock_telegram_message, Mock())

            # Функция должна просто вернуться без ответа для не-админов
            mock_telegram_message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_cmd_reload_admin_success(self, mock_telegram_message, mock_config):
        """Тест команды /reload для админа - успешно"""
        mock_telegram_message.from_user.id = 123456789  # ID админа
        mock_telegram_message.answer = AsyncMock()

        with (
            patch("google_sheets_updater.update_templates_from_sheets") as mock_update,
            patch("handlers.ADMIN_USER_IDS", [123456789]),
        ):
            mock_update.return_value = asyncio.Future()
            mock_update.return_value.set_result(True)
            mock_tm = Mock()
            mock_tm.reload_templates.return_value = None
            mock_tm.templates = {"визитки": [1, 2, 3], "футболки": [1, 2, 3]}

            await cmd_reload(mock_telegram_message, mock_tm)

            mock_telegram_message.answer.assert_called()
            # Проверяем, что было несколько вызовов (сообщения о прогрессе)
            assert mock_telegram_message.answer.call_count >= 2

    @pytest.mark.asyncio
    async def test_cmd_reload_admin_failure(self, mock_telegram_message, mock_config):
        """Тест команды /reload для админа - ошибка"""
        mock_telegram_message.from_user.id = 123456789  # ID админа
        mock_telegram_message.answer = AsyncMock()

        with (
            patch("google_sheets_updater.update_templates_from_sheets") as mock_update,
            patch("handlers.ADMIN_USER_IDS", [123456789]),
        ):
            mock_update.return_value = asyncio.Future()
            mock_update.return_value.set_result(False)

            await cmd_reload(mock_telegram_message, Mock())

            mock_telegram_message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_callback_category_valid(self, mock_callback_query):
        """Тест callback для валидной категории"""
        mock_callback_query.data = "category_визитки"
        mock_callback_query.answer = AsyncMock()
        mock_callback_query.message.edit_text = AsyncMock()
        mock_state = AsyncMock()
        mock_state.update_data = AsyncMock()
        mock_template_manager = Mock()

        # Создаем моки с атрибутами
        template1 = Mock()
        template1.subcategory = "1"
        template1.button_text = "💰 Цена"
        template1.sort_order = 1

        template2 = Mock()
        template2.subcategory = "2"
        template2.button_text = "🎨 Макет"
        template2.sort_order = 2

        sample_templates = [template1, template2]

        mock_template_manager.templates = {"визитки": sample_templates}
        mock_template_manager.get_user_language.return_value = "ukr"

        with (
            patch("keyboards.create_category_menu_keyboard") as mock_keyboard,
            patch("keyboards.get_category_title") as mock_title,
        ):
            mock_keyboard.return_value = Mock()
            mock_title.return_value = "📇 Візитки"

            await process_category_selection(
                mock_callback_query, mock_state, mock_template_manager
            )

            mock_callback_query.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_category_empty(self, mock_callback_query):
        """Тест callback для категории без шаблонов"""
        mock_callback_query.data = "category_пустая"
        mock_callback_query.answer = AsyncMock()
        mock_callback_query.message.edit_text = AsyncMock()
        mock_state = Mock()
        mock_template_manager = Mock()

        mock_template_manager.templates = {}
        mock_template_manager.get_user_language.return_value = "ukr"

        await process_category_selection(
            mock_callback_query, mock_state, mock_template_manager
        )

        mock_callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_template_found(self, mock_callback_query):
        """Тест callback для существующего шаблона"""
        mock_callback_query.data = "template_визитки_1"
        mock_callback_query.answer = AsyncMock()
        mock_callback_query.message.edit_text = AsyncMock()

        sample_template = Mock()
        sample_template.sort_order = 1
        sample_template.category = "визитки"
        sample_template.subcategory = "1"

        mock_tm = Mock()
        mock_tm.get_template_by_subcategory.return_value = sample_template
        mock_tm.get_template_text.return_value = "Текст шаблона"
        mock_tm.get_user_language.return_value = "ukr"
        mock_tm.stats = Mock()

        with patch("keyboards.create_template_keyboard") as mock_keyboard:
            mock_keyboard.return_value = Mock()

            # Создаем AsyncMock для state
            mock_state = AsyncMock()
            mock_state.update_data = AsyncMock()

            await process_template_selection(mock_callback_query, mock_state, mock_tm)

            mock_callback_query.message.edit_text.assert_called_once()
            mock_tm.stats.log_template_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_template_not_found(self, mock_callback_query):
        """Тест callback для несуществующего шаблона"""
        mock_callback_query.data = "template_визитки_999"
        mock_callback_query.answer = AsyncMock()
        mock_callback_query.message.edit_text = AsyncMock()

        mock_tm = Mock()
        mock_tm.get_template_by_subcategory.return_value = None
        mock_tm.get_user_language.return_value = "rus"

        # Создаем AsyncMock для state
        mock_state = AsyncMock()
        mock_state.update_data = AsyncMock()

        await process_template_selection(mock_callback_query, mock_state, mock_tm)

        mock_callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_template_language_preference(self, mock_callback_query):
        """Тест отображения шаблона с учетом языковых предпочтений"""
        mock_callback_query.data = "template_визитки_1"
        mock_callback_query.from_user.language_code = "uk"
        mock_callback_query.answer = AsyncMock()
        mock_callback_query.message.edit_text = AsyncMock()

        sample_template = Mock()
        sample_template.sort_order = 1
        sample_template.category = "визитки"
        sample_template.subcategory = "1"

        mock_tm = Mock()
        mock_tm.get_template_by_subcategory.return_value = sample_template
        mock_tm.get_user_language.return_value = "ukr"
        mock_tm.get_template_text.return_value = "Український текст"
        mock_tm.stats = Mock()

        with patch("keyboards.create_template_keyboard") as mock_keyboard:
            mock_keyboard.return_value = Mock()

            # Создаем AsyncMock для state
            mock_state = AsyncMock()
            mock_state.update_data = AsyncMock()

            await process_template_selection(mock_callback_query, mock_state, mock_tm)

            # Проверяем, что используется украинский текст
            call_args = mock_callback_query.message.edit_text.call_args[0][0]
            assert "Український текст" in call_args
