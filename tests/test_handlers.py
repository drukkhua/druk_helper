"""
Тесты для handlers
Тестирование обработчиков команд и callback'ов бота
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from handlers import cmd_start, cmd_stats, cmd_reload, callback_category, callback_template


class TestHandlers:
    """Тесты для обработчиков бота"""

    @pytest.mark.asyncio
    async def test_cmd_start_new_user(self, mock_telegram_message):
        """Тест команды /start для нового пользователя"""
        mock_telegram_message.answer = AsyncMock()
        
        with patch('handlers.get_main_keyboard') as mock_keyboard:
            mock_keyboard.return_value = Mock()
            await cmd_start(mock_telegram_message)
            
            mock_telegram_message.answer.assert_called_once()
            # Проверяем, что был вызван с клавиатурой
            call_args = mock_telegram_message.answer.call_args
            assert 'reply_markup' in call_args.kwargs

    @pytest.mark.asyncio
    async def test_cmd_start_admin_user(self, mock_telegram_message, mock_config):
        """Тест команды /start для админа"""
        mock_telegram_message.from_user.id = 123456789  # ID админа
        mock_telegram_message.answer = AsyncMock()
        
        with patch('handlers.Config', mock_config), \
             patch('handlers.get_main_keyboard') as mock_keyboard:
            mock_keyboard.return_value = Mock()
            await cmd_start(mock_telegram_message)
            
            mock_telegram_message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_stats_admin(self, mock_telegram_message, mock_config):
        """Тест команды /stats для админа"""
        mock_telegram_message.from_user.id = 123456789  # ID админа
        mock_telegram_message.answer = AsyncMock()
        
        mock_stats_text = "Статистика за 7 дней:\n📇 Визитки: 10 просмотров"
        
        with patch('handlers.Config', mock_config), \
             patch('handlers.get_stats_text') as mock_get_stats:
            mock_get_stats.return_value = mock_stats_text
            await cmd_stats(mock_telegram_message)
            
            mock_telegram_message.answer.assert_called_once()
            call_args = mock_telegram_message.answer.call_args[0][0]
            assert "Статистика" in call_args

    @pytest.mark.asyncio
    async def test_cmd_stats_non_admin(self, mock_telegram_message, mock_config):
        """Тест команды /stats для обычного пользователя"""
        mock_telegram_message.from_user.id = 999999999  # Не админ
        mock_telegram_message.answer = AsyncMock()
        
        with patch('handlers.Config', mock_config):
            await cmd_stats(mock_telegram_message)
            
            mock_telegram_message.answer.assert_called_once()
            call_args = mock_telegram_message.answer.call_args[0][0]
            assert "У вас нет прав" in call_args

    @pytest.mark.asyncio
    async def test_cmd_reload_admin_success(self, mock_telegram_message, mock_config):
        """Тест команды /reload для админа - успешно"""
        mock_telegram_message.from_user.id = 123456789  # ID админа
        mock_telegram_message.answer = AsyncMock()
        
        with patch('handlers.Config', mock_config), \
             patch('handlers.update_templates_from_sheets') as mock_update, \
             patch('handlers.template_manager') as mock_tm:
            mock_update.return_value = True
            mock_tm.load_templates.return_value = True
            mock_tm.get_total_templates_count.return_value = 84
            
            await cmd_reload(mock_telegram_message)
            
            mock_telegram_message.answer.assert_called()
            # Проверяем последний вызов (должен быть успех)
            last_call = mock_telegram_message.answer.call_args_list[-1][0][0]
            assert "✅" in last_call and "84" in last_call

    @pytest.mark.asyncio
    async def test_cmd_reload_admin_failure(self, mock_telegram_message, mock_config):
        """Тест команды /reload для админа - ошибка"""
        mock_telegram_message.from_user.id = 123456789  # ID админа
        mock_telegram_message.answer = AsyncMock()
        
        with patch('handlers.Config', mock_config), \
             patch('handlers.update_templates_from_sheets') as mock_update:
            mock_update.return_value = False
            
            await cmd_reload(mock_telegram_message)
            
            mock_telegram_message.answer.assert_called()
            last_call = mock_telegram_message.answer.call_args_list[-1][0][0]
            assert "❌" in last_call

    @pytest.mark.asyncio
    async def test_callback_category_valid(self, mock_callback_query):
        """Тест callback для валидной категории"""
        mock_callback_query.data = "category_визитки"
        mock_callback_query.answer = AsyncMock()
        mock_callback_query.message.edit_text = AsyncMock()
        
        sample_templates = [
            {'subcategory': '1', 'button_text': '💰 Цена', 'sort_order': '1'},
            {'subcategory': '2', 'button_text': '🎨 Макет', 'sort_order': '2'}
        ]
        
        with patch('handlers.template_manager') as mock_tm, \
             patch('handlers.get_category_keyboard') as mock_keyboard:
            mock_tm.get_templates_by_category.return_value = sample_templates
            mock_keyboard.return_value = Mock()
            
            await callback_category(mock_callback_query)
            
            mock_callback_query.answer.assert_called_once()
            mock_callback_query.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_category_empty(self, mock_callback_query):
        """Тест callback для категории без шаблонов"""
        mock_callback_query.data = "category_пустая"
        mock_callback_query.answer = AsyncMock()
        mock_callback_query.message.edit_text = AsyncMock()
        
        with patch('handlers.template_manager') as mock_tm:
            mock_tm.get_templates_by_category.return_value = []
            
            await callback_category(mock_callback_query)
            
            mock_callback_query.answer.assert_called_once()
            call_args = mock_callback_query.message.edit_text.call_args[0][0]
            assert "шаблонов не найдено" in call_args

    @pytest.mark.asyncio
    async def test_callback_template_found(self, mock_callback_query):
        """Тест callback для существующего шаблона"""
        mock_callback_query.data = "template_визитки_1"
        mock_callback_query.answer = AsyncMock()
        mock_callback_query.message.edit_text = AsyncMock()
        
        sample_template = {
            'category': 'визитки',
            'subcategory': '1',
            'button_text': '💰 Цена',
            'answer_ukr': 'Український текст',
            'answer_rus': 'Русский текст'
        }
        
        with patch('handlers.template_manager') as mock_tm, \
             patch('handlers.get_template_keyboard') as mock_keyboard, \
             patch('handlers.update_template_stats') as mock_stats:
            mock_tm.get_template_by_subcategory.return_value = sample_template
            mock_keyboard.return_value = Mock()
            
            await callback_template(mock_callback_query)
            
            mock_callback_query.answer.assert_called_once()
            mock_callback_query.message.edit_text.assert_called_once()
            mock_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_template_not_found(self, mock_callback_query):
        """Тест callback для несуществующего шаблона"""
        mock_callback_query.data = "template_визитки_999"
        mock_callback_query.answer = AsyncMock()
        mock_callback_query.message.edit_text = AsyncMock()
        
        with patch('handlers.template_manager') as mock_tm:
            mock_tm.get_template_by_subcategory.return_value = None
            
            await callback_template(mock_callback_query)
            
            mock_callback_query.answer.assert_called_once()
            call_args = mock_callback_query.message.edit_text.call_args[0][0]
            assert "Шаблон не найден" in call_args

    @pytest.mark.asyncio
    async def test_callback_template_language_preference(self, mock_callback_query):
        """Тест отображения шаблона с учетом языковых предпочтений"""
        mock_callback_query.data = "template_визитки_1"
        mock_callback_query.from_user.language_code = "uk"
        mock_callback_query.answer = AsyncMock()
        mock_callback_query.message.edit_text = AsyncMock()
        
        sample_template = {
            'category': 'визитки',
            'subcategory': '1',
            'button_text': '💰 Цена',
            'answer_ukr': 'Український текст',
            'answer_rus': 'Русский текст'
        }
        
        with patch('handlers.template_manager') as mock_tm, \
             patch('handlers.get_template_keyboard') as mock_keyboard, \
             patch('handlers.update_template_stats') as mock_stats:
            mock_tm.get_template_by_subcategory.return_value = sample_template
            mock_keyboard.return_value = Mock()
            
            await callback_template(mock_callback_query)
            
            # Проверяем, что используется украинский текст
            call_args = mock_callback_query.message.edit_text.call_args[0][0]
            assert "Український текст" in call_args