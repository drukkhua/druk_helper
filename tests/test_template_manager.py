"""
Тесты для TemplateManager
Тестирование загрузки шаблонов, поиска и валидации данных
"""

import pytest
import os
import tempfile
from unittest.mock import patch, mock_open

from template_manager import TemplateManager


class TestTemplateManager:
    """Тесты для класса TemplateManager"""

    def test_init_template_manager(self):
        """Тест инициализации TemplateManager"""
        tm = TemplateManager()
        assert tm.templates == {}
        assert tm.data_dir == "./data"

    def test_load_csv_file_success(self, temp_data_dir, sample_csv_content):
        """Тест успешной загрузки CSV файла"""
        # Создаем тестовый CSV файл
        csv_file = os.path.join(temp_data_dir, "test_templates.csv")
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write(sample_csv_content)
        
        tm = TemplateManager()
        templates = tm._load_csv_file(csv_file)
        
        assert len(templates) == 2
        assert templates[0]['category'] == 'визитки'
        assert templates[0]['button_text'] == '💰 Тест цена'
        assert templates[1]['keywords'] == 'макет,дизайн'

    def test_load_csv_file_not_found(self):
        """Тест загрузки несуществующего файла"""
        tm = TemplateManager()
        templates = tm._load_csv_file("nonexistent.csv")
        assert templates == []

    def test_load_csv_file_invalid_format(self, temp_data_dir):
        """Тест загрузки файла с неправильным форматом"""
        # Создаем файл с неправильным форматом
        csv_file = os.path.join(temp_data_dir, "invalid.csv")
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("invalid,csv,format\nno,headers,here")
        
        tm = TemplateManager()
        templates = tm._load_csv_file(csv_file)
        assert templates == []

    def test_validate_template_valid(self):
        """Тест валидации правильного шаблона"""
        tm = TemplateManager()
        template = {
            'category': 'визитки',
            'subcategory': '1',
            'button_text': '💰 Цена',
            'keywords': 'цена,стоимость',
            'answer_ukr': 'Український текст',
            'answer_rus': 'Русский текст',
            'sort_order': '1'
        }
        assert tm._validate_template(template) is True

    def test_validate_template_missing_fields(self):
        """Тест валидации шаблона с отсутствующими полями"""
        tm = TemplateManager()
        template = {
            'category': 'визитки',
            'button_text': '💰 Цена'
            # Отсутствуют обязательные поля
        }
        assert tm._validate_template(template) is False

    def test_validate_template_empty_fields(self):
        """Тест валидации шаблона с пустыми полями"""
        tm = TemplateManager()
        template = {
            'category': '',
            'subcategory': '1',
            'button_text': '💰 Цена',
            'keywords': 'цена',
            'answer_ukr': 'Текст',
            'answer_rus': 'Текст',
            'sort_order': '1'
        }
        assert tm._validate_template(template) is False

    @patch('os.path.exists')
    @patch('template_manager.TemplateManager._load_csv_file')
    def test_load_templates_success(self, mock_load_csv, mock_exists):
        """Тест успешной загрузки всех шаблонов"""
        mock_exists.return_value = True
        mock_load_csv.return_value = [
            {
                'category': 'визитки',
                'subcategory': '1',
                'button_text': '💰 Цена',
                'keywords': 'цена',
                'answer_ukr': 'Текст',
                'answer_rus': 'Текст',
                'sort_order': '1'
            }
        ]
        
        tm = TemplateManager()
        success = tm.load_templates()
        
        assert success is True
        assert 'визитки' in tm.templates
        assert len(tm.templates['визитки']) == 1

    def test_get_categories(self, sample_templates):
        """Тест получения списка категорий"""
        tm = TemplateManager()
        tm.templates = {'визитки': sample_templates}
        
        categories = tm.get_categories()
        assert 'визитки' in categories
        assert len(categories) == 1

    def test_get_templates_by_category(self, sample_templates):
        """Тест получения шаблонов по категории"""
        tm = TemplateManager()
        tm.templates = {'визитки': sample_templates}
        
        templates = tm.get_templates_by_category('визитки')
        assert len(templates) == 2
        assert templates[0]['button_text'] == '💰 Тест цена'

    def test_get_templates_by_category_not_found(self):
        """Тест получения шаблонов несуществующей категории"""
        tm = TemplateManager()
        tm.templates = {}
        
        templates = tm.get_templates_by_category('несуществует')
        assert templates == []

    def test_get_template_by_subcategory(self, sample_templates):
        """Тест получения шаблона по подкатегории"""
        tm = TemplateManager()
        tm.templates = {'визитки': sample_templates}
        
        template = tm.get_template_by_subcategory('визитки', '1')
        assert template is not None
        assert template['button_text'] == '💰 Тест цена'

    def test_get_template_by_subcategory_not_found(self, sample_templates):
        """Тест получения несуществующего шаблона"""
        tm = TemplateManager()
        tm.templates = {'визитки': sample_templates}
        
        template = tm.get_template_by_subcategory('визитки', '999')
        assert template is None

    def test_search_templates(self, sample_templates):
        """Тест поиска шаблонов по ключевым словам"""
        tm = TemplateManager()
        tm.templates = {'визитки': sample_templates}
        
        # Поиск по ключевому слову
        results = tm.search_templates('цена')
        assert len(results) == 1
        assert results[0]['button_text'] == '💰 Тест цена'
        
        # Поиск по тексту кнопки
        results = tm.search_templates('макет')
        assert len(results) == 1
        assert results[0]['button_text'] == '🎨 Тест макет'

    def test_search_templates_no_results(self, sample_templates):
        """Тест поиска без результатов"""
        tm = TemplateManager()
        tm.templates = {'визитки': sample_templates}
        
        results = tm.search_templates('несуществующее')
        assert results == []

    def test_search_templates_case_insensitive(self, sample_templates):
        """Тест поиска без учета регистра"""
        tm = TemplateManager()
        tm.templates = {'визитки': sample_templates}
        
        # Поиск в разном регистре
        results1 = tm.search_templates('ЦЕНА')
        results2 = tm.search_templates('цена')
        results3 = tm.search_templates('Цена')
        
        assert len(results1) == len(results2) == len(results3) == 1

    def test_get_total_templates_count(self, sample_templates):
        """Тест подсчета общего количества шаблонов"""
        tm = TemplateManager()
        tm.templates = {
            'визитки': sample_templates,
            'футболки': sample_templates.copy()
        }
        
        total = tm.get_total_templates_count()
        assert total == 4  # 2 + 2

    def test_get_total_templates_count_empty(self):
        """Тест подсчета при отсутствии шаблонов"""
        tm = TemplateManager()
        tm.templates = {}
        
        total = tm.get_total_templates_count()
        assert total == 0