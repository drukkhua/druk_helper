"""
Тесты для stats
Тестирование статистики использования шаблонов
"""

import pytest
import json
import os
import tempfile
from datetime import datetime
from unittest.mock import patch, mock_open

from stats import (
    update_template_stats,
    get_stats_text,
    update_copy_stats,
    get_popular_templates,
    cleanup_old_stats
)


class TestStats:
    """Тесты для модуля статистики"""

    @pytest.fixture
    def temp_stats_file(self):
        """Временный файл для статистики"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_file.close()
        yield temp_file.name
        os.unlink(temp_file.name)

    @pytest.fixture
    def sample_stats_data(self):
        """Образец данных статистики"""
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            today: {
                "визитки": {
                    "1": {
                        "count": 10,
                        "last_used": "14:30:22",
                        "copies": 5
                    },
                    "2": {
                        "count": 8,
                        "last_used": "13:45:11",
                        "copies": 3
                    }
                },
                "футболки": {
                    "1": {
                        "count": 15,
                        "last_used": "15:20:45",
                        "copies": 7
                    }
                }
            }
        }

    def test_update_template_stats_new_file(self, temp_stats_file):
        """Тест обновления статистики в новом файле"""
        with patch('stats.STATS_FILE', temp_stats_file):
            update_template_stats('визитки', '1', 123456789)
            
            # Проверяем, что файл создан и содержит правильные данные
            assert os.path.exists(temp_stats_file)
            
            with open(temp_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            today = datetime.now().strftime('%Y-%m-%d')
            assert today in data
            assert 'визитки' in data[today]
            assert '1' in data[today]['визитки']
            assert data[today]['визитки']['1']['count'] == 1

    def test_update_template_stats_existing_entry(self, temp_stats_file, sample_stats_data):
        """Тест обновления существующей записи статистики"""
        # Записываем начальные данные
        with open(temp_stats_file, 'w', encoding='utf-8') as f:
            json.dump(sample_stats_data, f)
        
        with patch('stats.STATS_FILE', temp_stats_file):
            update_template_stats('визитки', '1', 123456789)
            
            with open(temp_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            today = datetime.now().strftime('%Y-%m-%d')
            # Счетчик должен увеличиться с 10 до 11
            assert data[today]['визитки']['1']['count'] == 11

    def test_update_template_stats_new_category(self, temp_stats_file, sample_stats_data):
        """Тест добавления новой категории в статистику"""
        with open(temp_stats_file, 'w', encoding='utf-8') as f:
            json.dump(sample_stats_data, f)
        
        with patch('stats.STATS_FILE', temp_stats_file):
            update_template_stats('наклейки', '1', 123456789)
            
            with open(temp_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            today = datetime.now().strftime('%Y-%m-%d')
            assert 'наклейки' in data[today]
            assert data[today]['наклейки']['1']['count'] == 1

    def test_update_copy_stats(self, temp_stats_file, sample_stats_data):
        """Тест обновления статистики копирований"""
        with open(temp_stats_file, 'w', encoding='utf-8') as f:
            json.dump(sample_stats_data, f)
        
        with patch('stats.STATS_FILE', temp_stats_file):
            update_copy_stats('визитки', '1')
            
            with open(temp_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            today = datetime.now().strftime('%Y-%m-%d')
            # Количество копирований должно увеличиться с 5 до 6
            assert data[today]['визитки']['1']['copies'] == 6

    def test_update_copy_stats_new_entry(self, temp_stats_file):
        """Тест копирования для новой записи"""
        with patch('stats.STATS_FILE', temp_stats_file):
            update_copy_stats('визитки', '1')
            
            with open(temp_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            today = datetime.now().strftime('%Y-%m-%d')
            assert data[today]['визитки']['1']['copies'] == 1
            assert data[today]['визитки']['1']['count'] == 0  # Просмотров пока не было

    def test_get_stats_text_with_data(self, temp_stats_file, sample_stats_data):
        """Тест получения текста статистики с данными"""
        with open(temp_stats_file, 'w', encoding='utf-8') as f:
            json.dump(sample_stats_data, f)
        
        with patch('stats.STATS_FILE', temp_stats_file):
            stats_text = get_stats_text()
            
            assert 'Статистика использования' in stats_text
            assert 'визитки' in stats_text
            assert 'футболки' in stats_text
            assert '10' in stats_text  # Количество просмотров
            assert '5' in stats_text   # Количество копирований

    def test_get_stats_text_empty_file(self, temp_stats_file):
        """Тест получения статистики из пустого файла"""
        with open(temp_stats_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        
        with patch('stats.STATS_FILE', temp_stats_file):
            stats_text = get_stats_text()
            
            assert 'данных нет' in stats_text or 'пусто' in stats_text.lower()

    def test_get_stats_text_nonexistent_file(self):
        """Тест получения статистики из несуществующего файла"""
        with patch('stats.STATS_FILE', '/nonexistent/path/stats.json'):
            stats_text = get_stats_text()
            
            assert 'ошибка' in stats_text.lower() or 'данных нет' in stats_text

    def test_get_popular_templates(self, temp_stats_file, sample_stats_data):
        """Тест получения популярных шаблонов"""
        with open(temp_stats_file, 'w', encoding='utf-8') as f:
            json.dump(sample_stats_data, f)
        
        with patch('stats.STATS_FILE', temp_stats_file):
            popular = get_popular_templates(limit=2)
            
            assert len(popular) == 2
            # Первым должен быть самый популярный (футболки:1 с 15 просмотрами)
            assert popular[0]['category'] == 'футболки'
            assert popular[0]['subcategory'] == '1'
            assert popular[0]['count'] == 15

    def test_get_popular_templates_empty_data(self, temp_stats_file):
        """Тест получения популярных шаблонов без данных"""
        with open(temp_stats_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        
        with patch('stats.STATS_FILE', temp_stats_file):
            popular = get_popular_templates()
            
            assert popular == []

    def test_cleanup_old_stats(self, temp_stats_file):
        """Тест очистки старой статистики"""
        from datetime import datetime, timedelta
        
        # Создаем данные с разными датами
        old_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        recent_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        
        test_data = {
            old_date: {
                "визитки": {"1": {"count": 5, "copies": 2}}
            },
            recent_date: {
                "футболки": {"1": {"count": 8, "copies": 4}}
            },
            today: {
                "наклейки": {"1": {"count": 3, "copies": 1}}
            }
        }
        
        with open(temp_stats_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        with patch('stats.STATS_FILE', temp_stats_file):
            cleanup_old_stats(days=7)  # Удаляем данные старше 7 дней
            
            with open(temp_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Старые данные должны быть удалены
            assert old_date not in data
            # Недавние данные должны остаться
            assert recent_date in data
            assert today in data

    def test_stats_file_corruption_handling(self):
        """Тест обработки поврежденного файла статистики"""
        corrupted_content = '{"invalid": json content'
        
        with patch('builtins.open', mock_open(read_data=corrupted_content)):
            with patch('stats.STATS_FILE', 'test_stats.json'):
                # Функция должна обработать ошибку и не упасть
                update_template_stats('визитки', '1', 123456789)
                stats_text = get_stats_text()
                
                assert isinstance(stats_text, str)

    def test_concurrent_stats_updates(self, temp_stats_file):
        """Тест параллельных обновлений статистики"""
        import threading
        
        def update_stats_worker(category, subcategory, user_id):
            for _ in range(10):
                update_template_stats(category, subcategory, user_id)
        
        with patch('stats.STATS_FILE', temp_stats_file):
            # Запускаем несколько потоков одновременно
            threads = []
            for i in range(3):
                thread = threading.Thread(
                    target=update_stats_worker,
                    args=('визитки', '1', 123456789 + i)
                )
                threads.append(thread)
                thread.start()
            
            # Ждем завершения всех потоков
            for thread in threads:
                thread.join()
            
            # Проверяем результат
            with open(temp_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            today = datetime.now().strftime('%Y-%m-%d')
            # Должно быть 30 обновлений (3 потока × 10 обновлений)
            assert data[today]['визитки']['1']['count'] == 30

    def test_stats_performance_with_large_data(self, temp_stats_file):
        """Тест производительности с большим объемом данных"""
        import time
        
        # Создаем большой объем данных
        large_data = {}
        for day in range(30):  # 30 дней
            date = (datetime.now() - timedelta(days=day)).strftime('%Y-%m-%d')
            large_data[date] = {}
            
            for category in ['визитки', 'футболки', 'листовки', 'наклейки', 'блокноты']:
                large_data[date][category] = {}
                for subcategory in range(1, 21):  # 20 подкатегорий каждая
                    large_data[date][category][str(subcategory)] = {
                        "count": 100,
                        "copies": 50,
                        "last_used": "12:00:00"
                    }
        
        with open(temp_stats_file, 'w', encoding='utf-8') as f:
            json.dump(large_data, f)
        
        with patch('stats.STATS_FILE', temp_stats_file):
            # Тестируем скорость обновления
            start_time = time.time()
            update_template_stats('визитки', '1', 123456789)
            update_time = time.time() - start_time
            
            # Обновление должно быть быстрым (менее 1 секунды)
            assert update_time < 1.0
            
            # Тестируем скорость получения статистики
            start_time = time.time()
            stats_text = get_stats_text()
            get_stats_time = time.time() - start_time
            
            # Получение статистики должно быть быстрым
            assert get_stats_time < 2.0
            assert len(stats_text) > 0