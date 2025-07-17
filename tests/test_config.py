"""
Тесты для config
Тестирование конфигурации и переменных окружения
"""

import pytest
import os
from unittest.mock import patch

from config import Config


class TestConfig:
    """Тесты для класса Config"""

    def test_config_required_fields(self):
        """Тест наличия обязательных полей конфигурации"""
        required_fields = [
            'BOT_TOKEN',
            'ADMIN_USER_IDS',
            'GOOGLE_SHEETS_API_KEY',
            'BOT_NAME',
            'COMPANY_NAME',
            'PORTFOLIO_LINK',
            'DEBUG',
            'LOG_LEVEL'
        ]
        
        for field in required_fields:
            assert hasattr(Config, field), f"Отсутствует обязательное поле: {field}"

    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token_123',
        'ADMIN_USER_IDS': '123456789,987654321',
        'GOOGLE_SHEETS_API_KEY': 'test_api_key',
        'DEBUG': 'True',
        'LOG_LEVEL': 'INFO'
    })
    def test_config_loads_from_env(self):
        """Тест загрузки конфигурации из переменных окружения"""
        # Перезагружаем модуль конфигурации
        import importlib
        import config
        importlib.reload(config)
        
        assert config.Config.BOT_TOKEN == 'test_token_123'
        assert 123456789 in config.Config.ADMIN_USER_IDS
        assert 987654321 in config.Config.ADMIN_USER_IDS
        assert config.Config.GOOGLE_SHEETS_API_KEY == 'test_api_key'
        assert config.Config.DEBUG is True
        assert config.Config.LOG_LEVEL == 'INFO'

    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token',
        'ADMIN_USER_IDS': '123,456,789',
        'DEBUG': 'False',
        'LOG_LEVEL': 'ERROR'
    })
    def test_config_admin_ids_parsing(self):
        """Тест парсинга списка админов"""
        import importlib
        import config
        importlib.reload(config)
        
        expected_ids = [123, 456, 789]
        assert config.Config.ADMIN_USER_IDS == expected_ids

    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token',
        'ADMIN_USER_IDS': '  123 , 456 , 789  ',  # С пробелами
        'DEBUG': 'false',  # lowercase
    })
    def test_config_admin_ids_whitespace_handling(self):
        """Тест обработки пробелов в списке админов"""
        import importlib
        import config
        importlib.reload(config)
        
        expected_ids = [123, 456, 789]
        assert config.Config.ADMIN_USER_IDS == expected_ids

    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token',
        'DEBUG': 'yes',  # Нестандартное значение
    })
    def test_config_boolean_parsing(self):
        """Тест парсинга булевых значений"""
        import importlib
        import config
        importlib.reload(config)
        
        # 'yes' должно интерпретироваться как True
        assert config.Config.DEBUG is True

    @patch.dict(os.environ, {
        'BOT_TOKEN': '',  # Пустой токен
        'ADMIN_USER_IDS': '123',
    })
    def test_config_empty_values(self):
        """Тест обработки пустых значений"""
        import importlib
        import config
        
        # Перезагружаем конфигурацию с пустым токеном
        importlib.reload(config)
        
        # Проверяем что пустой токен загружается как None или пустая строка
        assert config.Config.BOT_TOKEN == '' or config.Config.BOT_TOKEN is None

    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token',
        'ADMIN_USER_IDS': 'not_a_number,123',
    })
    def test_config_invalid_admin_id(self):
        """Тест обработки невалидных ID админов"""
        import importlib
        import config
        
        with pytest.raises((ValueError, TypeError)):
            importlib.reload(config)

    def test_config_default_values(self):
        """Тест значений по умолчанию"""
        # Проверяем, что есть разумные значения по умолчанию
        assert isinstance(Config.BOT_NAME, str)
        assert isinstance(Config.COMPANY_NAME, str)
        assert isinstance(Config.PORTFOLIO_LINK, str)
        
        # LOG_LEVEL должен быть одним из валидных уровней
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        assert Config.LOG_LEVEL in valid_log_levels

    def test_config_token_format(self):
        """Тест формата токена бота"""
        if Config.BOT_TOKEN:
            # Токен должен содержать только допустимые символы
            import re
            token_pattern = r'^[0-9]+:[a-zA-Z0-9_-]+$'
            if not Config.BOT_TOKEN.startswith('test_'):  # Исключаем тестовые токены
                assert re.match(token_pattern, Config.BOT_TOKEN), \
                    "Токен бота имеет неправильный формат"

    def test_config_admin_ids_type(self):
        """Тест типа данных для списка админов"""
        assert isinstance(Config.ADMIN_USER_IDS, list)
        
        for admin_id in Config.ADMIN_USER_IDS:
            assert isinstance(admin_id, int)
            assert admin_id > 0  # ID должны быть положительными

    def test_config_debug_type(self):
        """Тест типа данных для DEBUG"""
        assert isinstance(Config.DEBUG, bool)

    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token',
        'GOOGLE_SHEETS_API_KEY': 'AIza' + 'a' * 35,  # Валидный формат
    })
    def test_config_api_key_format(self):
        """Тест формата Google Sheets API ключа"""
        import importlib
        import config
        importlib.reload(config)
        
        # Google API ключи обычно начинаются с "AIza"
        if not config.Config.GOOGLE_SHEETS_API_KEY.startswith('test_'):
            assert config.Config.GOOGLE_SHEETS_API_KEY.startswith('AIza'), \
                "Google Sheets API ключ имеет неправильный формат"

    def test_config_portfolio_link_format(self):
        """Тест формата ссылки на портфолио"""
        if Config.PORTFOLIO_LINK:
            assert Config.PORTFOLIO_LINK.startswith(('http://', 'https://', 't.me/')), \
                "Ссылка на портфолио должна быть валидным URL"

    def test_config_immutability(self):
        """Тест возможности изменения конфигурации"""
        # Конфигурация может изменяться (не защищена)
        original_token = Config.BOT_TOKEN
        original_debug = Config.DEBUG
        
        # Попытка изменить значения
        Config.BOT_TOKEN = "hacked_token"
        Config.DEBUG = not Config.DEBUG
        
        # Проверяем, что значения изменились (конфигурация не защищена)
        assert Config.BOT_TOKEN == "hacked_token"
        assert Config.DEBUG == (not original_debug)
        
        # Восстанавливаем исходные значения
        Config.BOT_TOKEN = original_token
        Config.DEBUG = original_debug