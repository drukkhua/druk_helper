"""
Интеграционные тесты
Тестирование взаимодействия между компонентами системы
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock

from template_manager import TemplateManager
from google_sheets_updater import GoogleSheetsUpdater


class TestIntegration:
    """Интеграционные тесты для системы"""

    @pytest.fixture
    def integration_temp_dir(self):
        """Временная директория для интеграционных тестов"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        import shutil
        shutil.rmtree(temp_dir)

    def test_template_manager_and_google_sheets_integration(self, integration_temp_dir):
        """Тест интеграции TemplateManager с GoogleSheetsUpdater"""
        # Создаем тестовые CSV файлы
        test_files = {
            'visitki_templates.csv': """category;subcategory;button_text;keywords;answer_ukr;answer_rus;sort_order
визитки;1;💰 Цена;цена,стоимость;Український текст;Русский текст;1
визитки;2;🎨 Макет;макет,дизайн;Макет УКР;Макет РУС;2""",
            
            'futbolki_templates.csv': """category;subcategory;button_text;keywords;answer_ukr;answer_rus;sort_order
футболки;1;💰 Цена;цена футболки;Футболка УКР;Футболка РУС;1"""
        }
        
        # Создаем файлы
        for filename, content in test_files.items():
            filepath = os.path.join(integration_temp_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Тестируем TemplateManager
        tm = TemplateManager()
        tm.data_dir = integration_temp_dir
        
        success = tm.load_templates()
        assert success is True
        assert len(tm.templates) == 2
        assert 'визитки' in tm.templates
        assert 'футболки' in tm.templates
        assert len(tm.templates['визитки']) == 2
        assert len(tm.templates['футболки']) == 1

    @patch('requests.get')
    def test_google_sheets_to_template_manager_flow(self, mock_get, integration_temp_dir):
        """Тест полного потока: Google Sheets -> CSV -> TemplateManager"""
        
        # Мок ответа Google Sheets API (метаданные)
        mock_sheets_response = Mock()
        mock_sheets_response.raise_for_status.return_value = None
        mock_sheets_response.json.return_value = {
            "sheets": [
                {"properties": {"sheetId": 0, "title": "визитки"}},
                {"properties": {"sheetId": 123, "title": "футболки"}}
            ]
        }
        
        # Мок ответа CSV export
        mock_csv_response = Mock()
        mock_csv_response.raise_for_status.return_value = None
        mock_csv_response.content = b'''category,subcategory,button_text,keywords,answer_ukr,answer_rus,sort_order
\xd0\xb2\xd0\xb8\xd0\xb7\xd0\xb8\xd1\x82\xd0\xba\xd0\xb8,1,\xf0\x9f\x92\xb0 \xd0\xa6\xd0\xb5\xd0\xbd\xd0\xb0,\xd1\x86\xd0\xb5\xd0\xbd\xd0\xb0,\xd0\xa3\xd0\xba\xd1\x80\xd0\xb0\xd1\x97\xd0\xbd\xd1\x81\xd1\x8c\xd0\xba\xd0\xb8\xd0\xb9,\xd0\xa0\xd1\x83\xd1\x81\xd1\x81\xd0\xba\xd0\xb8\xd0\xb9,1'''
        
        # Настройка mock'а для разных URL'ов
        def mock_get_side_effect(url, **kwargs):
            if 'spreadsheets' in url and 'export' not in url:
                return mock_sheets_response
            elif 'export' in url:
                return mock_csv_response
            return Mock()
        
        mock_get.side_effect = mock_get_side_effect
        
        # Тестируем GoogleSheetsUpdater
        updater = GoogleSheetsUpdater()
        updater.output_dir = integration_temp_dir
        
        test_url = "https://docs.google.com/spreadsheets/d/test_id/edit"
        success = updater.update_templates_from_google_sheets(test_url)
        assert success is True
        
        # Проверяем, что файлы созданы
        expected_files = ['visitki_templates.csv', 'futbolki_templates.csv']
        for filename in expected_files:
            filepath = os.path.join(integration_temp_dir, filename)
            assert os.path.exists(filepath)
        
        # Тестируем загрузку в TemplateManager
        tm = TemplateManager()
        tm.data_dir = integration_temp_dir
        success = tm.load_templates()
        assert success is True
        assert len(tm.templates) >= 1

    @patch('handlers.template_manager')
    @patch('handlers.update_templates_from_sheets')
    async def test_reload_command_integration(self, mock_update_sheets, mock_template_manager):
        """Тест интеграции команды /reload с обновлением шаблонов"""
        from handlers import cmd_reload
        
        # Настройка моков
        mock_update_sheets.return_value = True
        mock_template_manager.load_templates.return_value = True
        mock_template_manager.get_total_templates_count.return_value = 84
        
        # Мок сообщения от админа
        mock_message = Mock()
        mock_message.from_user.id = 123456789
        mock_message.answer = AsyncMock()
        
        with patch('handlers.Config') as mock_config:
            mock_config.ADMIN_USER_IDS = [123456789]
            
            await cmd_reload(mock_message)
            
            # Проверяем, что были вызваны нужные функции
            mock_update_sheets.assert_called_once()
            mock_template_manager.load_templates.assert_called_once()
            
            # Проверяем, что было отправлено сообщение об успехе
            assert mock_message.answer.call_count >= 1
            last_call = mock_message.answer.call_args_list[-1][0][0]
            assert "✅" in last_call

    def test_search_functionality_integration(self, integration_temp_dir):
        """Тест интеграции функции поиска"""
        # Создаем тестовые данные с разными категориями
        test_data = {
            'visitki_templates.csv': """category;subcategory;button_text;keywords;answer_ukr;answer_rus;sort_order
визитки;1;💰 Цена визиток;цена,стоимость,визитки;Цена визиток УКР;Цена визиток РУС;1
визитки;2;🎨 Макет визиток;макет,дизайн;Макет УКР;Макет РУС;2""",
            
            'futbolki_templates.csv': """category;subcategory;button_text;keywords;answer_ukr;answer_rus;sort_order
футболки;1;💰 Цена футболок;цена,футболки;Цена футболок УКР;Цена футболок РУС;1
футболки;2;👕 Виды футболок;виды,типы;Виды УКР;Виды РУС;2"""
        }
        
        # Создаем файлы
        for filename, content in test_data.items():
            filepath = os.path.join(integration_temp_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Загружаем в TemplateManager
        tm = TemplateManager()
        tm.data_dir = integration_temp_dir
        tm.load_templates()
        
        # Тестируем поиск
        # Поиск по общему слову "цена"
        results = tm.search_templates('цена')
        assert len(results) == 2  # Должно найти в обеих категориях
        
        # Поиск по специфичному слову
        results = tm.search_templates('визитки')
        assert len(results) == 1  # Только в категории визиток
        
        # Поиск по слову в названии кнопки
        results = tm.search_templates('макет')
        assert len(results) == 1
        assert results[0]['category'] == 'визитки'

    def test_statistics_integration(self, integration_temp_dir):
        """Тест интеграции статистики"""
        from stats import update_template_stats, get_stats_text
        
        # Создаем тестовый файл статистики
        stats_file = os.path.join(integration_temp_dir, 'stats.json')
        
        with patch('stats.STATS_FILE', stats_file):
            # Обновляем статистику несколько раз
            update_template_stats('визитки', '1', 123456789)
            update_template_stats('визитки', '1', 123456789)
            update_template_stats('футболки', '1', 987654321)
            
            # Получаем текст статистики
            stats_text = get_stats_text()
            
            assert 'визитки' in stats_text
            assert 'футболки' in stats_text
            assert '2' in stats_text  # Два просмотра визиток
            assert '1' in stats_text  # Один просмотр футболок

    async def test_error_handling_integration(self):
        """Тест интеграции обработки ошибок"""
        from error_handler import handle_error
        from error_monitor import log_error
        
        # Создаем тестовую ошибку
        test_error = ValueError("Test integration error")
        test_context = {
            'user_id': 123456789,
            'action': 'integration_test',
            'data': {'test': 'value'}
        }
        
        # Логируем ошибку
        log_error(test_error, test_context)
        
        # Обрабатываем ошибку
        error_message = handle_error(test_error, test_context)
        
        assert error_message is not None
        assert isinstance(error_message, str)
        assert len(error_message) > 0

    def test_keyboard_generation_integration(self, integration_temp_dir):
        """Тест интеграции генерации клавиатур"""
        from keyboards import get_main_keyboard, get_category_keyboard
        
        # Создаем тестовые данные
        test_data = """category;subcategory;button_text;keywords;answer_ukr;answer_rus;sort_order
визитки;1;💰 Цена;цена;УКР;РУС;1
визитки;2;🎨 Макет;макет;УКР;РУС;2"""
        
        filepath = os.path.join(integration_temp_dir, 'visitki_templates.csv')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(test_data)
        
        # Загружаем шаблоны
        tm = TemplateManager()
        tm.data_dir = integration_temp_dir
        tm.load_templates()
        
        with patch('keyboards.template_manager', tm):
            # Тестируем главную клавиатуру
            main_kb = get_main_keyboard(123456789)
            assert main_kb is not None
            
            # Тестируем клавиатуру категории
            templates = tm.get_templates_by_category('визитки')
            category_kb = get_category_keyboard(templates, 'визитки')
            assert category_kb is not None