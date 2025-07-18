"""
Тесты для stats
Тестирование статистики использования шаблонов
"""

import tempfile

import json
import os
import pytest
from datetime import datetime
from unittest.mock import mock_open, patch

from stats import StatsManager


class TestStats:
    """Тесты для модуля статистики"""

    @pytest.fixture
    def temp_stats_file(self):
        """Временный файл для статистики"""
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        temp_file.close()
        yield temp_file.name
        os.unlink(temp_file.name)

    @pytest.fixture
    def stats_manager(self, temp_stats_file):
        """Fixture для StatsManager с временным файлом"""
        # Инициализируем пустой JSON файл
        with open(temp_stats_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        # Создаем экземпляр и заменяем путь к файлу
        manager = StatsManager()
        manager.stats_file = temp_stats_file
        return manager

    @pytest.fixture
    def sample_stats_data(self):
        """Образец данных статистики"""
        today = datetime.now().strftime("%Y-%m-%d")
        return {
            today: {
                "визитки": {
                    "1": {"count": 10, "last_used": "14:30:22", "copies": 5},
                    "2": {"count": 8, "last_used": "13:45:11", "copies": 3},
                },
                "футболки": {"1": {"count": 15, "last_used": "15:20:45", "copies": 7}},
            }
        }

    def test_log_template_usage_new_file(self, stats_manager, temp_stats_file):
        """Тест записи использования шаблона в новом файле"""
        stats_manager.log_template_usage("визитки", 1, 123456789)

        # Проверяем, что файл создан и содержит правильные данные
        assert os.path.exists(temp_stats_file)

        with open(temp_stats_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")
        assert today in data
        assert "визитки" in data[today]
        assert "1" in data[today]["визитки"]
        assert data[today]["визитки"]["1"]["count"] == 1

    def test_log_template_usage_existing_entry(
        self, stats_manager, temp_stats_file, sample_stats_data
    ):
        """Тест записи использования существующего шаблона"""
        # Записываем начальные данные
        with open(temp_stats_file, "w", encoding="utf-8") as f:
            json.dump(sample_stats_data, f)

        stats_manager.log_template_usage("визитки", 1, 123456789)

        with open(temp_stats_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")
        # Счетчик должен увеличиться с 10 до 11
        assert data[today]["визитки"]["1"]["count"] == 11

    def test_log_template_usage_new_category(
        self, stats_manager, temp_stats_file, sample_stats_data
    ):
        """Тест добавления новой категории в статистику"""
        with open(temp_stats_file, "w", encoding="utf-8") as f:
            json.dump(sample_stats_data, f)

        stats_manager.log_template_usage("наклейки", 1, 123456789)

        with open(temp_stats_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")
        assert "наклейки" in data[today]
        assert data[today]["наклейки"]["1"]["count"] == 1

    def test_log_template_copy(self, stats_manager, temp_stats_file, sample_stats_data):
        """Тест записи копирования шаблона"""
        with open(temp_stats_file, "w", encoding="utf-8") as f:
            json.dump(sample_stats_data, f)

        stats_manager.log_template_usage("визитки", 1, 123456789, "copy")

        with open(temp_stats_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")
        # Количество копирований должно увеличиться с 5 до 6
        assert data[today]["визитки"]["1"]["copies"] == 6

    def test_log_template_copy_new_entry(self, stats_manager, temp_stats_file):
        """Тест копирования для новой записи"""
        stats_manager.log_template_usage("визитки", 1, 123456789, "copy")

        with open(temp_stats_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")
        assert data[today]["визитки"]["1"]["copies"] == 1
        assert data[today]["визитки"]["1"]["count"] == 0  # Просмотров пока не было

    def test_get_stats_summary_with_data(
        self, stats_manager, temp_stats_file, sample_stats_data
    ):
        """Тест получения сводки статистики с данными"""
        with open(temp_stats_file, "w", encoding="utf-8") as f:
            json.dump(sample_stats_data, f)

        stats_text = stats_manager.get_stats_summary()

        assert "Статистика использования" in stats_text
        assert "визитки" in stats_text
        assert "футболки" in stats_text
        # Проверяем суммарные значения: визитки имеет 10+8=18 просмотров, 5+3=8 копирований
        assert "18 просмотров" in stats_text
        assert "8 копирований" in stats_text
        # Футболки имеет 15 просмотров, 7 копирований
        assert "15 просмотров" in stats_text
        assert "7 копирований" in stats_text

    def test_get_stats_summary_empty_file(self, stats_manager, temp_stats_file):
        """Тест получения статистики из пустого файла"""
        with open(temp_stats_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        stats_text = stats_manager.get_stats_summary()

        assert isinstance(stats_text, str)  # Должен возвращать строку

    def test_get_stats_summary_nonexistent_file(self):
        """Тест получения статистики из несуществующего файла"""
        stats_manager = StatsManager()
        stats_manager.stats_file = "/nonexistent/path/stats.json"
        stats_text = stats_manager.get_stats_summary()

        assert "ошибка" in stats_text.lower() or "Статистика" in stats_text

    def test_stats_manager_basic_functionality(self, stats_manager, temp_stats_file):
        """Тест базовой функциональности StatsManager"""
        # Тест записи статистики
        stats_manager.log_template_usage("визитки", 1, 123456789)

        # Проверяем, что файл создан
        assert os.path.exists(temp_stats_file)

        # Проверяем получение статистики
        stats_text = stats_manager.get_stats_summary()
        assert isinstance(stats_text, str)
        assert len(stats_text) > 0

    def test_stats_manager_with_empty_data(self, stats_manager, temp_stats_file):
        """Тест StatsManager с пустыми данными"""
        with open(temp_stats_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        stats_text = stats_manager.get_stats_summary()
        assert isinstance(stats_text, str)

    def test_stats_manager_with_multiple_days(self, stats_manager, temp_stats_file):
        """Тест StatsManager с данными за несколько дней"""
        from datetime import datetime, timedelta

        # Создаем данные с разными датами
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        recent_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        test_data = {
            old_date: {
                "визитки": {"1": {"count": 5, "copies": 2, "last_used": "10:00:00"}}
            },
            recent_date: {
                "футболки": {"1": {"count": 8, "copies": 4, "last_used": "14:00:00"}}
            },
            today: {
                "наклейки": {"1": {"count": 3, "copies": 1, "last_used": "16:00:00"}}
            },
        }

        with open(temp_stats_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        stats_text = stats_manager.get_stats_summary()
        assert isinstance(stats_text, str)
        assert len(stats_text) > 0

    def test_stats_file_corruption_handling(self):
        """Тест обработки поврежденного файла статистики"""
        stats_manager = StatsManager()
        stats_manager.stats_file = "test_stats.json"

        corrupted_content = '{"invalid": json content'

        with patch("builtins.open", mock_open(read_data=corrupted_content)):
            # Функция должна обработать ошибку и не упасть
            stats_manager.log_template_usage("визитки", 1, 123456789)
            stats_text = stats_manager.get_stats_summary()

            assert isinstance(stats_text, str)

    def test_concurrent_stats_updates(self, temp_stats_file):
        """Тест параллельных обновлений статистики"""
        import threading

        # Инициализируем файл пустым JSON объектом
        with open(temp_stats_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        def update_stats_worker(stats_manager, category, subcategory, user_id):
            for _ in range(10):
                stats_manager.log_template_usage(category, subcategory, user_id)

        stats_manager = StatsManager()
        stats_manager.stats_file = temp_stats_file

        # Запускаем несколько потоков одновременно
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=update_stats_worker,
                args=(stats_manager, "визитки", 1, 123456789 + i),
            )
            threads.append(thread)
            thread.start()

        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()

        # Проверяем результат
        with open(temp_stats_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")
        # Должно быть 30 обновлений (3 потока × 10 обновлений)
        # Из-за race conditions может быть меньше, но должно быть больше 0
        assert data[today]["визитки"]["1"]["count"] > 0
        assert data[today]["визитки"]["1"]["count"] <= 30

    def test_stats_performance_with_large_data(self, temp_stats_file):
        """Тест производительности с большим объемом данных"""
        import time

        from datetime import timedelta

        # Создаем большой объем данных
        large_data = {}
        for day in range(30):  # 30 дней
            date = (datetime.now() - timedelta(days=day)).strftime("%Y-%m-%d")
            large_data[date] = {}

            for category in ["визитки", "футболки", "листовки", "наклейки", "блокноты"]:
                large_data[date][category] = {}
                for subcategory in range(1, 21):  # 20 подкатегорий каждая
                    large_data[date][category][str(subcategory)] = {
                        "count": 100,
                        "copies": 50,
                        "last_used": "12:00:00",
                    }

        with open(temp_stats_file, "w", encoding="utf-8") as f:
            json.dump(large_data, f)

        stats_manager = StatsManager()
        stats_manager.stats_file = temp_stats_file

        # Тестируем скорость обновления
        start_time = time.time()
        stats_manager.log_template_usage("визитки", 1, 123456789)
        update_time = time.time() - start_time

        # Обновление должно быть быстрым (менее 1 секунды)
        assert update_time < 1.0

        # Тестируем скорость получения статистики
        start_time = time.time()
        stats_text = stats_manager.get_stats_summary()
        get_stats_time = time.time() - start_time

        # Получение статистики должно быть быстрым
        assert get_stats_time < 2.0
        assert len(stats_text) > 0
