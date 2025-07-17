"""
Тесты для validation
Тестирование валидации входных данных и безопасности
"""

import pytest
from validation import (
    validate_user_input,
    sanitize_text,
    is_admin_user,
    validate_callback_data,
    validate_search_query
)


class TestValidation:
    """Тесты для модуля валидации"""

    def test_validate_user_input_valid_text(self):
        """Тест валидации корректного текста"""
        valid_inputs = [
            "Нормальный текст",
            "Text with numbers 123",
            "Текст с эмодзи 😀",
            "Short",
            "Символы: .,!?-"
        ]
        
        for text in valid_inputs:
            assert validate_user_input(text) is True

    def test_validate_user_input_empty(self):
        """Тест валидации пустого текста"""
        invalid_inputs = ["", "   ", "\n\t  "]
        
        for text in invalid_inputs:
            assert validate_user_input(text) is False

    def test_validate_user_input_too_long(self):
        """Тест валидации слишком длинного текста"""
        long_text = "a" * 1001  # Больше лимита
        assert validate_user_input(long_text) is False

    def test_validate_user_input_malicious_content(self):
        """Тест валидации вредоносного контента"""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "SELECT * FROM users",
            "' OR '1'='1",
            "../../../etc/passwd"
        ]
        
        for text in malicious_inputs:
            assert validate_user_input(text) is False

    def test_sanitize_text_html_tags(self):
        """Тест очистки HTML тегов"""
        input_text = "<script>alert('test')</script>Hello World"
        sanitized = sanitize_text(input_text)
        assert "<script>" not in sanitized
        assert "Hello World" in sanitized

    def test_sanitize_text_sql_injection(self):
        """Тест очистки SQL инъекций"""
        input_text = "'; DROP TABLE users; --"
        sanitized = sanitize_text(input_text)
        assert "DROP TABLE" not in sanitized
        assert "--" not in sanitized

    def test_sanitize_text_normal_text(self):
        """Тест очистки обычного текста"""
        input_text = "Нормальный текст с числами 123"
        sanitized = sanitize_text(input_text)
        assert sanitized == input_text

    def test_sanitize_text_special_chars(self):
        """Тест очистки специальных символов"""
        input_text = "Текст с символами: .,!?-()[]"
        sanitized = sanitize_text(input_text)
        # Безопасные символы должны остаться
        assert "Текст с символами" in sanitized

    def test_is_admin_user_valid_admin(self):
        """Тест проверки валидного админа"""
        admin_ids = [123456789, 987654321]
        
        with pytest.fixture.mock.patch('validation.Config') as mock_config:
            mock_config.ADMIN_USER_IDS = admin_ids
            assert is_admin_user(123456789) is True
            assert is_admin_user(987654321) is True

    def test_is_admin_user_invalid_admin(self):
        """Тест проверки невалидного админа"""
        admin_ids = [123456789, 987654321]
        
        with pytest.fixture.mock.patch('validation.Config') as mock_config:
            mock_config.ADMIN_USER_IDS = admin_ids
            assert is_admin_user(999999999) is False
            assert is_admin_user(0) is False

    def test_validate_callback_data_valid(self):
        """Тест валидации корректных callback данных"""
        valid_callbacks = [
            "category_визитки",
            "template_футболки_1",
            "back_to_main",
            "copy_text_визитки_2",
            "search_results_page_1"
        ]
        
        for callback in valid_callbacks:
            assert validate_callback_data(callback) is True

    def test_validate_callback_data_invalid(self):
        """Тест валидации некорректных callback данных"""
        invalid_callbacks = [
            "",
            "a" * 65,  # Слишком длинный
            "category_<script>",
            "template_'; DROP TABLE",
            "../../etc/passwd",
            "javascript:alert(1)"
        ]
        
        for callback in invalid_callbacks:
            assert validate_callback_data(callback) is False

    def test_validate_search_query_valid(self):
        """Тест валидации корректного поискового запроса"""
        valid_queries = [
            "цена",
            "футболки цена",
            "макет визитки",
            "123",
            "test query"
        ]
        
        for query in valid_queries:
            assert validate_search_query(query) is True

    def test_validate_search_query_too_short(self):
        """Тест валидации слишком короткого запроса"""
        short_queries = ["", "a", " ", "\t"]
        
        for query in short_queries:
            assert validate_search_query(query) is False

    def test_validate_search_query_too_long(self):
        """Тест валидации слишком длинного запроса"""
        long_query = "a" * 101  # Больше лимита для поиска
        assert validate_search_query(long_query) is False

    def test_validate_search_query_malicious(self):
        """Тест валидации вредоносного поискового запроса"""
        malicious_queries = [
            "<script>alert('xss')</script>",
            "'; SELECT * FROM",
            "../../../etc/passwd"
        ]
        
        for query in malicious_queries:
            assert validate_search_query(query) is False

    def test_edge_cases_unicode(self):
        """Тест обработки Unicode символов"""
        unicode_text = "Текст с юникодом: 🇺🇦 emoji и спецсимволы ñáéíóú"
        assert validate_user_input(unicode_text) is True
        sanitized = sanitize_text(unicode_text)
        assert "🇺🇦" in sanitized

    def test_edge_cases_mixed_languages(self):
        """Тест обработки смешанных языков"""
        mixed_text = "English Українська Русский 中文"
        assert validate_user_input(mixed_text) is True
        sanitized = sanitize_text(mixed_text)
        assert "English" in sanitized
        assert "Українська" in sanitized

    def test_edge_cases_numeric_strings(self):
        """Тест обработки числовых строк"""
        numeric_inputs = ["123", "0", "-456", "3.14", "1,000"]
        
        for num_str in numeric_inputs:
            assert validate_user_input(num_str) is True
            assert sanitize_text(num_str) == num_str