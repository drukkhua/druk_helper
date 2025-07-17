#!/usr/bin/env python3
"""
Модульный Google Sheets Converter с Batch API
Архитектура разделена на независимые модули для легкого тестирования и расширения
"""

import hashlib
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, Tuple

import pandas as pd
import requests
import yaml


# Опциональные импорты
try:
    import openpyxl


    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

try:
    from slugify import slugify


    SLUGIFY_AVAILABLE = True
except ImportError:
    SLUGIFY_AVAILABLE = False


# ============================================================================
# КОНФИГУРАЦИЯ / CONFIGURATION
# ============================================================================

class Config:
    """Централизованная конфигурация"""

    def __init__(self,
                 api_key: Optional[str] = None,
                 output_dir: str = "output",
                 cache_file: str = "cache/sheets_cache.json",
                 batch_size: int = 100,
                 timeout: int = 60):
        # API конфигурация
        self.api_key = api_key or os.getenv('GOOGLE_SHEETS_API_KEY')

        # Пути и директории
        self.output_dir = output_dir
        self.cache_file = cache_file

        # Производительность
        self.batch_size = batch_size  # Максимум листов в одном batch запросе
        self.timeout = timeout

        # API URLs
        self.sheets_api_base = "https://sheets.googleapis.com/v4/spreadsheets"
        self.export_api_base = "https://docs.google.com/spreadsheets/d"

        # Валидация
        if not self.api_key:
            print("⚠️ Google Sheets API ключ не найден. Используется публичный режим.")


# ============================================================================
# ПРОТОКОЛЫ И ИНТЕРФЕЙСЫ / PROTOCOLS & INTERFACES  
# ============================================================================

class DataExporter(Protocol):
    """Протокол для экспортеров данных"""

    def export(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        """Экспортирует данные в файл"""
        ...


class CacheProvider(Protocol):
    """Протокол для кеш-провайдеров"""

    def get(self, key: str) -> Optional[Any]:
        """Получает значение из кеша"""
        ...

    def set(self, key: str, value: Any) -> None:
        """Сохраняет значение в кеш"""
        ...

    def is_changed(self, key: str, data: str) -> bool:
        """Проверяет, изменились ли данные"""
        ...


class DataProcessor(Protocol):
    """Протокол для обработчиков данных"""

    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Обрабатывает данные"""
        ...


# ============================================================================
# GOOGLE SHEETS API CLIENT / КЛИЕНТ API
# ============================================================================

class GoogleSheetsClient:
    """Клиент для работы с Google Sheets API с поддержкой batch запросов"""

    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ModularSheetsConverter/2.0'
        })

    def extract_sheet_id(self, url: str) -> str:
        """Извлекает ID таблицы из URL"""
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"Invalid Google Sheets URL: {url}")
        return match.group(1)

    def get_sheets_metadata(self, sheet_id: str) -> List[Dict[str, Any]]:
        """
        Получает метаданные всех листов таблицы
        Возвращает: [{'gid': str, 'name': str, 'rows': int, 'cols': int}, ...]
        """
        print("🔍 Получаем метаданные листов...")

        api_url = f"{self.config.sheets_api_base}/{sheet_id}"
        params = {'fields': 'sheets.properties'}

        if self.config.api_key:
            params['key'] = self.config.api_key

        try:
            response = self.session.get(api_url, params=params, timeout=self.config.timeout)
            response.raise_for_status()

            data = response.json()
            sheets_info = []

            for sheet in data.get('sheets', []):
                props = sheet.get('properties', {})
                grid_props = props.get('gridProperties', {})

                sheets_info.append({
                    'gid': str(props.get('sheetId', 0)),
                    'name': props.get('title', f'Sheet{props.get("sheetId", 0)}'),
                    'rows': grid_props.get('rowCount', 1000),
                    'cols': grid_props.get('columnCount', 26)
                })

            print(f"📋 Найдено листов: {len(sheets_info)}")
            for i, sheet in enumerate(sheets_info, 1):
                print(f"   {i}. '{sheet['name']}' ({sheet['rows']}x{sheet['cols']})")

            return sheets_info

        except requests.RequestException as e:
            print(f"❌ Ошибка получения метаданных: {e}")
            # Fallback: используем базовую информацию
            return [{'gid': '0', 'name': 'Sheet1', 'rows': 1000, 'cols': 26}]

    def batch_get_sheets_data(self, sheet_id: str, sheets_info: List[Dict]) -> Dict[str, Tuple[pd.DataFrame, str]]:
        """
        🚀 BATCH API: Загружает данные ВСЕХ листов за один запрос
        Поддерживает до 100+ листов в одном batch запросе
        Возвращает: Dict[sheet_name, (DataFrame, raw_data)]
        """
        results = {}

        # Разбиваем на батчи если листов больше чем batch_size
        batches = [sheets_info[i:i + self.config.batch_size]
                   for i in range(0, len(sheets_info), self.config.batch_size)]

        print(f"🚀 Batch загрузка: {len(sheets_info)} листов в {len(batches)} запросах")

        for batch_num, batch_sheets in enumerate(batches, 1):
            print(f"📦 Обрабатываем batch {batch_num}/{len(batches)} ({len(batch_sheets)} листов)")

            batch_results = self._load_single_batch(sheet_id, batch_sheets)
            results.update(batch_results)

        print(f"✅ Batch загрузка завершена: {len(results)} листов получено")
        return results

    def _load_single_batch(self, sheet_id: str, sheets_info: List[Dict]) -> Dict[str, Tuple[pd.DataFrame, str]]:
        """Загружает один batch листов"""
        try:
            # Формируем ranges для batch запроса
            ranges = []
            sheet_mapping = {}

            for i, sheet_info in enumerate(sheets_info):
                sheet_name = sheet_info['name']
                # Экранируем имена листов с специальными символами
                escaped_name = self._escape_sheet_name(sheet_name)

                # Определяем диапазон на основе размера листа
                rows = min(sheet_info.get('rows', 1000), 10000)  # Ограничиваем максимум
                cols = min(sheet_info.get('cols', 26), 26)  # До колонки Z
                col_letter = chr(ord('A') + cols - 1)

                range_name = f"{escaped_name}!A1:{col_letter}{rows}"
                ranges.append(range_name)
                sheet_mapping[i] = sheet_name

            # Выполняем batch запрос
            api_url = f"{self.config.sheets_api_base}/{sheet_id}/values:batchGet"
            params = {
                'ranges': ranges,
                'valueRenderOption': 'UNFORMATTED_VALUE',
                'dateTimeRenderOption': 'FORMATTED_STRING'
            }

            if self.config.api_key:
                params['key'] = self.config.api_key

            response = self.session.get(api_url, params=params, timeout=self.config.timeout)

            if response.status_code == 429:
                print("⏳ Rate limit достигнут, используем CSV fallback...")
                return self._csv_fallback_batch(sheet_id, sheets_info)

            response.raise_for_status()
            batch_data = response.json()

            return self._process_batch_response(batch_data, sheet_mapping)

        except Exception as e:
            print(f"❌ Ошибка batch запроса: {e}")
            print("🔄 Переключаемся на CSV fallback...")
            return self._csv_fallback_batch(sheet_id, sheets_info)

    def _process_batch_response(self, batch_data: Dict, sheet_mapping: Dict[int, str]) -> Dict[
        str, Tuple[pd.DataFrame, str]]:
        """Обрабатывает ответ batch API"""
        results = {}
        value_ranges = batch_data.get('valueRanges', [])

        for i, value_range in enumerate(value_ranges):
            sheet_name = sheet_mapping.get(i, f"Sheet{i}")

            try:
                values = value_range.get('values', [])
                raw_data = json.dumps(values, ensure_ascii=False)

                if not values:
                    results[sheet_name] = (pd.DataFrame(), raw_data)
                    continue

                # Создаем DataFrame
                if len(values) == 1:
                    # Только заголовки
                    df = pd.DataFrame(columns=values[0])
                else:
                    # Есть данные
                    headers = values[0]
                    data_rows = values[1:]

                    # Нормализуем длину строк
                    max_cols = len(headers)
                    normalized_rows = []
                    for row in data_rows:
                        while len(row) < max_cols:
                            row.append('')
                        normalized_rows.append(row[:max_cols])

                    df = pd.DataFrame(normalized_rows, columns=headers)

                # Очищаем пустые строки
                df = df.dropna(how='all')

                print(f"✅ [{sheet_name}] {len(df)} строк, {len(df.columns)} колонок")
                results[sheet_name] = (df, raw_data)

            except Exception as e:
                print(f"❌ [{sheet_name}] Ошибка обработки: {e}")
                results[sheet_name] = (pd.DataFrame(), "")

        return results

    def _csv_fallback_batch(self, sheet_id: str, sheets_info: List[Dict]) -> Dict[str, Tuple[pd.DataFrame, str]]:
        """Fallback: загрузка через CSV export"""
        results = {}
        print(f"📥 CSV fallback для {len(sheets_info)} листов...")

        for sheet_info in sheets_info:
            gid = sheet_info['gid']
            sheet_name = sheet_info['name']

            try:
                csv_url = f"{self.config.export_api_base}/{sheet_id}/export"
                params = {'format': 'csv', 'gid': gid}

                response = self.session.get(csv_url, params=params, timeout=30)
                response.raise_for_status()

                # Читаем CSV
                from io import StringIO
                csv_data = response.content.decode('utf-8')
                df = pd.read_csv(StringIO(csv_data))
                df = df.dropna(how='all')

                print(f"✅ [{sheet_name}] {len(df)} строк (CSV)")
                results[sheet_name] = (df, csv_data)

            except Exception as e:
                print(f"❌ [{sheet_name}] CSV ошибка: {e}")
                results[sheet_name] = (pd.DataFrame(), "")

        return results

    def _escape_sheet_name(self, sheet_name: str) -> str:
        """Экранирует имя листа для использования в API"""
        # Если есть специальные символы, заключаем в одинарные кавычки
        if any(c in sheet_name for c in " '\"!@#$%^&*()"):
            return f"'{sheet_name.replace(\"'\", \"''\")}'"
        return sheet_name


# ============================================================================
# СИСТЕМА КЕШИРОВАНИЯ / CACHING SYSTEM
# ============================================================================

class FileCache:
    """Файловая система кеширования"""

    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.cache_data = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Загружает кеш из файла"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                print(f"📂 Кеш загружен: {len(self.cache_data)} записей")
            else:
                self.cache_data = {}
        except Exception as e:
            print(f"⚠️ Ошибка загрузки кеша: {e}")
            self.cache_data = {}

    def _save_cache(self) -> None:
        """Сохраняет кеш в файл"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения кеша: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Получает значение из кеша"""
        return self.cache_data.get(key)

    def set(self, key: str, value: Any) -> None:
        """Сохраняет значение в кеш"""
        self.cache_data[key] = value
        self._save_cache()

    def is_changed(self, key: str, data: str) -> bool:
        """Проверяет, изменились ли данные с последнего кеширования"""
        current_hash = hashlib.md5(data.encode('utf-8')).hexdigest()
        cached_entry = self.get(key)

        if cached_entry and cached_entry.get('hash') == current_hash:
            print(f"📋 [{key}] Используем кеш")
            return False

        # Обновляем кеш
        self.set(key, {
            'hash': current_hash,
            'last_updated': datetime.now().isoformat()
        })
        return True


# ============================================================================
# ОБРАБОТЧИКИ ДАННЫХ / DATA PROCESSORS
# ============================================================================

class TextFieldProcessor:
    """Обработчик текстовых полей"""

    def __init__(self, text_fields: Optional[List[str]] = None, auto_detect: bool = True):
        self.text_fields = text_fields or []
        self.auto_detect = auto_detect

    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Обрабатывает текстовые поля"""
        if data.empty:
            return data

        df = data.copy()
        text_columns = self._detect_text_columns(df) if self.auto_detect else self.text_fields

        if text_columns:
            print(f"🔤 Обрабатываем текстовые колонки: {', '.join(text_columns)}")

            for column in text_columns:
                if column in df.columns:
                    # Убираем только \r, оставляем \n
                    df[column] = df[column].astype(str).str.replace('\r', '', regex=False)

        return df

    def _detect_text_columns(self, df: pd.DataFrame) -> List[str]:
        """Автоматически определяет текстовые колонки"""
        text_columns = []
        for column in df.columns:
            # ✅ Пропускаем числовые колонки
            if pd.api.types.is_numeric_dtype(df[column]):
                continue

            sample_data = df[column].dropna().astype(str).head(10)
            has_newlines = any('\n' in str(value) for value in sample_data)
            avg_length = sample_data.str.len().mean() if len(sample_data) > 0 else 0

            if has_newlines or avg_length > 50:
                text_columns.append(column)

        return text_columns


class FilenameProcessor:
    """Процессор для создания безопасных имен файлов"""

    def __init__(self, transliterate: bool = True):
        self.transliterate = transliterate

    def create_safe_filename(self, sheet_name: str, page_num: int) -> str:
        """Создает безопасное имя файла"""
        if not self.transliterate:
            clean_name = re.sub(r'[^a-zA-Z0-9\-\u0400-\u04FF]', '_', sheet_name)
            clean_name = re.sub(r'_+', '_', clean_name).strip('_').lower()
            safe_name = clean_name if clean_name else 'sheet'
        else:
            if SLUGIFY_AVAILABLE:
                safe_name = slugify(
                    sheet_name,
                    max_length=50,
                    word_boundary=True,
                    separator='_',
                    lowercase=True
                )
                safe_name = safe_name if safe_name else 'sheet'
            else:
                safe_name = self._basic_transliterate(sheet_name)

        return f"{safe_name}_{page_num:02d}"

    def _basic_transliterate(self, text: str) -> str:
        """Базовая русская транслитерация"""
        translit_dict = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }

        # Добавляем заглавные буквы
        for k, v in list(translit_dict.items()):
            if k != k.upper():
                translit_dict[k.upper()] = v.capitalize() if v else ''

        result = ''.join(translit_dict.get(char, char) for char in text)
        clean_name = re.sub(r'[^a-zA-Z0-9\-]', '_', result)
        clean_name = re.sub(r'_+', '_', clean_name).strip('_').lower()

        return clean_name if clean_name else 'sheet'


# ============================================================================
# ЭКСПОРТЕРЫ ДАННЫХ / DATA EXPORTERS
# ============================================================================

class BaseExporter(ABC):
    """Базовый класс для экспортеров"""

    def __init__(self, output_dir: str, format_name: str):
        self.output_dir = os.path.join(output_dir, format_name)
        self.format_name = format_name
        os.makedirs(self.output_dir, exist_ok=True)

    @abstractmethod
    def get_extension(self) -> str:
        """Возвращает расширение файла"""
        pass

    @abstractmethod
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        """Экспортирует данные в файл"""
        pass

    def export(self, data: pd.DataFrame, filename: str, **kwargs) -> str:
        """Экспортирует данные и возвращает путь к файлу"""
        if not filename.endswith(f'.{self.get_extension()}'):
            filename = f"{filename}.{self.get_extension()}"

        filepath = os.path.join(self.output_dir, filename)
        self.export_data(data, filepath, **kwargs)
        return filepath


class CSVExporter(BaseExporter):
    """Экспортер в CSV"""

    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'csv')

    def get_extension(self) -> str:
        return 'csv'

    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        separator = kwargs.get('separator', ';')
        encoding = kwargs.get('encoding', 'utf-8')
        data.to_csv(filepath, sep=separator, encoding=encoding, index=False, quoting=2)


class JSONExporter(BaseExporter):
    """Экспортер в JSON"""

    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'json')

    def get_extension(self) -> str:
        return 'json'

    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        orient = kwargs.get('orient', 'records')
        indent = kwargs.get('indent', 4)

        data_dict = data.to_dict(orient)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=indent)


class ExcelExporter(BaseExporter):
    """Экспортер в Excel"""

    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'excel')

    def get_extension(self) -> str:
        return 'xlsx'

    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        if not XLSX_AVAILABLE:
            raise ImportError("openpyxl required for Excel export")

        sheet_name = kwargs.get('sheet_name', 'Sheet1')
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            data.to_excel(writer, sheet_name=sheet_name, index=False)


class YAMLExporter(BaseExporter):
    """Экспортер в YAML"""

    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'yaml')

    def get_extension(self) -> str:
        return 'yml'

    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        data_dict = data.to_dict('records')
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data_dict, f, default_flow_style=False, allow_unicode=True, indent=2)


# ============================================================================
# СТАТИСТИКА И ОТЧЕТЫ / STATISTICS & REPORTS
# ============================================================================

class StatsCollector:
    """Сборщик статистики"""

    def __init__(self):
        self.stats = {
            'start_time': datetime.now(),
            'end_time': None,
            'total_sheets': 0,
            'processed_sheets': 0,
            'skipped_sheets': 0,
            'cached_sheets': 0,
            'batch_requests': 0,
            'formats_used': [],
            'files_created': [],
            'sheets_details': []
        }

    def add_file(self, format_name: str, filepath: str) -> None:
        """Добавляет информацию о созданном файле"""
        try:
            size = os.path.getsize(filepath)
        except OSError:
            size = 0

        self.stats['files_created'].append({
            'format': format_name,
            'filepath': filepath,
            'size_bytes': size
        })

    def add_sheet_detail(self, name: str, processed: bool, rows: int = 0,
                         columns: int = 0, from_cache: bool = False,
                         skip_reason: str = '') -> None:
        """Добавляет детали обработки листа"""
        self.stats['sheets_details'].append({
            'name': name,
            'processed': processed,
            'rows': rows,
            'columns': columns,
            'from_cache': from_cache,
            'skip_reason': skip_reason
        })

    def finalize(self) -> Dict[str, Any]:
        """Завершает сбор статистики и возвращает отчет"""
        self.stats['end_time'] = datetime.now()

        # Группируем файлы по форматам
        files_by_format = {}
        total_size = 0

        for file_info in self.stats['files_created']:
            format_name = file_info['format']
            if format_name not in files_by_format:
                files_by_format[format_name] = {'count': 0, 'total_size': 0}

            files_by_format[format_name]['count'] += 1
            files_by_format[format_name]['total_size'] += file_info['size_bytes']
            total_size += file_info['size_bytes']

        duration = self.stats['end_time'] - self.stats['start_time']

        return {
            'summary': {
                'duration': str(duration).split('.')[0],
                'total_sheets': self.stats['total_sheets'],
                'processed_sheets': self.stats['processed_sheets'],
                'cached_sheets': self.stats['cached_sheets'],
                'skipped_sheets': self.stats['skipped_sheets'],
                'batch_requests': self.stats['batch_requests'],
                'files_created': len(self.stats['files_created']),
                'total_size_bytes': total_size
            },
            'files_by_format': files_by_format,
            'sheets_details': self.stats['sheets_details']
        }


# ============================================================================
# ГЛАВНЫЙ КООРДИНАТОР / MAIN COORDINATOR
# ============================================================================

class ModularSheetsConverter:
    """Главный координатор - собирает все модули вместе"""

    def __init__(self,
                 config: Config,
                 cache: Optional[CacheProvider] = None,
                 exporters: Optional[Dict[str, BaseExporter]] = None,
                 processors: Optional[List[DataProcessor]] = None):

        self.config = config
        self.client = GoogleSheetsClient(config)
        self.cache = cache or FileCache(config.cache_file)
        self.exporters = exporters or {}
        self.processors = processors or []
        self.stats = StatsCollector()
        self.filename_processor = FilenameProcessor(transliterate=True)

        # Регистрируем экспортеры по умолчанию
        if not self.exporters:
            self._register_default_exporters()

    def _register_default_exporters(self) -> None:
        """Регистрирует экспортеры по умолчанию"""
        self.exporters = {
            'csv': CSVExporter(self.config.output_dir),
            'json': JSONExporter(self.config.output_dir),
            'yaml': YAMLExporter(self.config.output_dir)
        }

        if XLSX_AVAILABLE:
            self.exporters['xlsx'] = ExcelExporter(self.config.output_dir)

    def register_exporter(self, name: str, exporter: BaseExporter) -> None:
        """Регистрирует новый экспортер"""
        self.exporters[name] = exporter

    def add_processor(self, processor: DataProcessor) -> None:
        """Добавляет обработчик данных"""
        self.processors.append(processor)

    def convert_spreadsheet(self, url: str, formats: List[str]) -> Dict[str, Any]:
        """
        🚀 ГЛАВНЫЙ МЕТОД: Конвертирует всю таблицу с batch загрузкой
        """
        print("🚀 Запуск модульного конвертера Google Sheets")
        print("=" * 60)

        try:
            # 1. Извлекаем ID и получаем метаданные
            sheet_id = self.client.extract_sheet_id(url)
            print(f"🔍 ID таблицы: {sheet_id}")

            sheets_info = self.client.get_sheets_metadata(sheet_id)
            if not sheets_info:
                print("❌ Листы не найдены")
                return self.stats.finalize()

            self.stats.stats['total_sheets'] = len(sheets_info)
            self.stats.stats['formats_used'] = formats

            # 2. Batch загрузка ВСЕХ листов за один запрос  
            print(f"\n🚀 Batch загрузка {len(sheets_info)} листов...")
            sheets_data = self.client.batch_get_sheets_data(sheet_id, sheets_info)
            self.stats.stats['batch_requests'] = 1

            # 3. Обработка и экспорт каждого листа
            print(f"\n🔄 Обрабатываем {len(sheets_data)} листов...")

            for page_num, sheet_info in enumerate(sheets_info, 1):
                sheet_name = sheet_info['name']

                # Получаем предзагруженные данные
                sheet_result = sheets_data.get(sheet_name, (pd.DataFrame(), ""))
                df, raw_data = sheet_result

                if df.empty:
                    print(f"⏭️ [{sheet_name}] Пропуск - нет данных")
                    self.stats.add_sheet_detail(sheet_name, False, skip_reason="Нет данных")
                    self.stats.stats['skipped_sheets'] += 1
                    continue

                # Проверяем кеш
                cache_key = f"{sheet_id}:{sheet_name}"
                if not self.cache.is_changed(cache_key, raw_data):
                    print(f"📋 [{sheet_name}] Кеш актуален")
                    self.stats.add_sheet_detail(sheet_name, True, len(df), len(df.columns), from_cache=True)
                    self.stats.stats['cached_sheets'] += 1
                    continue

                # Обрабатываем данные
                processed_df = self._process_data(df)

                # Экспортируем во все форматы
                filename_base = self.filename_processor.create_safe_filename(sheet_name, page_num)
                exported_files = self._export_data(processed_df, filename_base, formats)

                # Обновляем статистику
                self.stats.add_sheet_detail(sheet_name, True, len(df), len(df.columns))
                self.stats.stats['processed_sheets'] += 1

                print(f"✅ [{sheet_name}] Экспортирован в {len(exported_files)} форматов")

            # 4. Финализация
            final_stats = self.stats.finalize()
            self._print_summary(final_stats)

            return final_stats

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
            return self.stats.finalize()

    def _process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Применяет все зарегистрированные обработчики"""
        processed_df = df
        for processor in self.processors:
            processed_df = processor.process(processed_df)
        return processed_df

    def _export_data(self, df: pd.DataFrame, filename_base: str, formats: List[str]) -> Dict[str, str]:
        """Экспортирует данные во все указанные форматы"""
        exported_files = {}

        for format_name in formats:
            if format_name not in self.exporters:
                print(f"⚠️ Неизвестный формат: {format_name}")
                continue

            try:
                exporter = self.exporters[format_name]
                filepath = exporter.export(df, filename_base)
                exported_files[format_name] = filepath
                self.stats.add_file(format_name, filepath)

            except Exception as e:
                print(f"❌ Ошибка экспорта {format_name}: {e}")

        return exported_files

    def _print_summary(self, stats: Dict[str, Any]) -> None:
        """Выводит краткую сводку"""
        summary = stats['summary']

        print("\n" + "=" * 60)
        print("📊 ИТОГОВАЯ СВОДКА")
        print("=" * 60)
        print(f"⏱️  Время выполнения: {summary['duration']}")
        print(f"📄 Обработано листов: {summary['processed_sheets']}/{summary['total_sheets']}")
        print(f"📂 Из кеша: {summary['cached_sheets']}")
        print(f"🚀 Batch запросов: {summary['batch_requests']}")
        print(f"📁 Создано файлов: {summary['files_created']}")

        # Размер файлов
        total_mb = summary['total_size_bytes'] / (1024 * 1024)
        if total_mb > 1:
            print(f"💾 Общий размер: {total_mb:.1f} MB")
        else:
            print(f"💾 Общий размер: {summary['total_size_bytes'] / 1024:.1f} KB")


# ============================================================================
# CONVENIENCE FUNCTIONS / ФУНКЦИИ УДОБСТВА
# ============================================================================

def quick_convert(url: str,
                  formats: List[str] = None,
                  output_dir: str = "output",
                  api_key: Optional[str] = None,
                  enable_cache: bool = True) -> Dict[str, Any]:
    """Быстрая конвертация с настройками по умолчанию"""

    if formats is None:
        formats = ['csv', 'json']

    # Создаем конфигурацию
    config = Config(api_key=api_key, output_dir=output_dir)

    # Создаем кеш если нужен
    cache = FileCache(config.cache_file) if enable_cache else None

    # Создаем конвертер
    converter = ModularSheetsConverter(config=config, cache=cache)

    # Добавляем текстовый процессор
    converter.add_processor(TextFieldProcessor(auto_detect=True))

    # Конвертируем
    return converter.convert_spreadsheet(url, formats)


def convert_with_validation(url: str,
                            expected_headers: List[str],
                            text_fields: List[str] = None,
                            formats: List[str] = None,
                            output_dir: str = "output") -> Dict[str, Any]:
    """Конвертация с валидацией заголовков"""

    if formats is None:
        formats = ['csv', 'json']

    config = Config(output_dir=output_dir)
    converter = ModularSheetsConverter(config=config)

    # Добавляем валидатор заголовков (можно реализовать как DataProcessor)
    if text_fields:
        converter.add_processor(TextFieldProcessor(text_fields=text_fields, auto_detect=False))

    return converter.convert_spreadsheet(url, formats)


# ============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ / EXAMPLE USAGE
# ============================================================================

def main():
    """Пример использования модульного конвертера"""

    if len(sys.argv) > 1:
        # CLI режим
        url = sys.argv[1]
        formats = ['csv', 'json', 'xlsx', 'yaml']

        print("🚀 Запуск в CLI режиме")
        result = quick_convert(url, formats, enable_cache=True)

        if result['summary']['processed_sheets'] > 0:
            print("🎉 Успешно завершено!")
        else:
            print("💥 Ошибки при обработке")
            sys.exit(1)

    else:
        # Интерактивный режим
        url = input("📝 Введите URL Google Таблицы: ").strip()

        if not url:
            url = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit"
            print(f"🧪 Используем тестовую таблицу: {url}")

        # Выбор форматов
        print("\nДоступные форматы: csv, json, xlsx, yaml")
        formats_input = input("Выберите форматы (через запятую): ").strip()

        if formats_input:
            formats = [f.strip() for f in formats_input.split(',')]
        else:
            formats = ['csv', 'json']

        print(f"✅ Выбраны форматы: {formats}")

        # Запуск конвертации
        result = quick_convert(url, formats, enable_cache=True)

        print("\n🎉 Конвертация завершена!")
        print(f"📁 Файлы сохранены в: output/")


if __name__ == "__main__":
    main()
