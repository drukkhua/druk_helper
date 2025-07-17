"""
Базовые тесты для проверки импортов и основной функциональности
"""

import pytest


class TestBasicImports:
    """Тесты базовых импортов"""
    
    def test_import_config(self):
        """Тест импорта конфигурации"""
        from config import Config, BOT_TOKEN, ADMIN_USER_IDS
        assert Config is not None
        assert hasattr(Config, 'BOT_TOKEN')
        assert hasattr(Config, 'ADMIN_USER_IDS')
    
    def test_import_template_manager(self):
        """Тест импорта TemplateManager"""
        from template_manager import TemplateManager
        assert TemplateManager is not None
    
    def test_import_google_sheets_updater(self):
        """Тест импорта GoogleSheetsUpdater"""
        from google_sheets_updater import GoogleSheetsUpdater
        assert GoogleSheetsUpdater is not None
    
    def test_import_handlers(self):
        """Тест импорта handlers"""
        import handlers
        assert hasattr(handlers, 'cmd_start')
        assert hasattr(handlers, 'cmd_stats')
        assert hasattr(handlers, 'cmd_reload')
    
    def test_import_keyboards(self):
        """Тест импорта keyboards"""
        import keyboards
        assert hasattr(keyboards, 'get_category_title')
    
    def test_import_validation(self):
        """Тест импорта validation"""
        import validation
        assert hasattr(validation, 'ValidationResult')
    
    def test_import_stats(self):
        """Тест импорта stats"""
        import stats
        assert hasattr(stats, 'StatsManager')


class TestBasicFunctionality:
    """Тесты базовой функциональности"""
    
    def test_template_manager_creation(self):
        """Тест создания TemplateManager"""
        from template_manager import TemplateManager
        tm = TemplateManager()
        assert tm is not None
        assert isinstance(tm.templates, dict)
    
    def test_google_sheets_updater_creation(self):
        """Тест создания GoogleSheetsUpdater"""
        from google_sheets_updater import GoogleSheetsUpdater
        updater = GoogleSheetsUpdater()
        assert updater is not None
        assert hasattr(updater, 'sheet_mapping')
    
    def test_validation_functions(self):
        """Тест функций валидации"""
        from validation import ValidationResult
        
        # Тест создания ValidationResult
        result = ValidationResult(is_valid=True, cleaned_value="test", error_message=None)
        assert result.is_valid is True
        assert result.cleaned_value == "test"
        assert result.error_message is None
    
    def test_config_values(self):
        """Тест значений конфигурации"""
        from config import Config
        
        # Проверяем основные атрибуты
        assert hasattr(Config, 'BOT_TOKEN')
        assert hasattr(Config, 'ADMIN_USER_IDS')
        assert hasattr(Config, 'GOOGLE_SHEETS_API_KEY')
        assert hasattr(Config, 'DEBUG')
        assert hasattr(Config, 'LOG_LEVEL')
        
        # Проверяем типы
        assert isinstance(Config.ADMIN_USER_IDS, list)
        assert isinstance(Config.DEBUG, bool)
        assert isinstance(Config.LOG_LEVEL, str)