"""
Конфигурация для pytest
Общие фикстуры и настройки для всех тестов
"""

import shutil
import tempfile

import os
import pytest
import sys
from unittest.mock import Mock, patch

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.core.template_manager import TemplateManager


@pytest.fixture
def mock_config():
    """Мок конфигурации для тестов"""
    config = Mock(spec=Config)
    config.BOT_TOKEN = "test_token"
    config.ADMIN_USER_IDS = [123456789]
    config.GOOGLE_SHEETS_API_KEY = "test_api_key"
    config.DEBUG = True
    return config


@pytest.fixture
def temp_data_dir():
    """Временная директория для тестовых данных"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_csv_content():
    """Пример содержимого CSV файла"""
    return """category;subcategory;button_text;keywords;answer_ukr;answer_rus;sort_order
визитки;1;💰 Тест цена;цена,тест;Тестовий текст українською;Тестовый текст на русском;1
визитки;2;🎨 Тест макет;макет,дизайн;Тестовий макет;Тестовый макет;2"""


@pytest.fixture
def sample_templates():
    """Пример списка шаблонов"""
    return [
        {
            "category": "визитки",
            "subcategory": "1",
            "button_text": "💰 Тест цена",
            "keywords": "цена,тест",
            "answer_ukr": "Тестовий текст українською",
            "answer_rus": "Тестовый текст на русском",
            "sort_order": "1",
        },
        {
            "category": "визитки",
            "subcategory": "2",
            "button_text": "🎨 Тест макет",
            "keywords": "макет,дизайн",
            "answer_ukr": "Тестовий макет",
            "answer_rus": "Тестовый макет",
            "sort_order": "2",
        },
    ]


@pytest.fixture
def mock_telegram_user():
    """Мок Telegram пользователя"""
    user = Mock()
    user.id = 123456789
    user.first_name = "Test"
    user.last_name = "User"
    user.username = "testuser"
    user.language_code = "uk"
    return user


@pytest.fixture
def mock_telegram_message():
    """Мок Telegram сообщения"""
    message = Mock()
    message.message_id = 1
    message.text = "/start"
    message.chat = Mock()
    message.chat.id = 123456789
    message.from_user = Mock()
    message.from_user.id = 123456789
    return message


@pytest.fixture
def mock_callback_query():
    """Мок Telegram callback query"""
    callback = Mock()
    callback.id = "test_callback"
    callback.data = "category_визитки"
    callback.from_user = Mock()
    callback.from_user.id = 123456789
    callback.message = Mock()
    callback.message.chat = Mock()
    callback.message.chat.id = 123456789
    return callback
