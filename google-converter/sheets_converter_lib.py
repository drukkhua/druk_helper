#!/usr/bin/env python3
"""
Universal Google Sheets Converter Library
Модульная, расширяемая библиотека для конвертации Google Sheets в любые форматы
"""

import json
import os
import re
from abc import ABC, abstractmethod
from io import StringIO
from typing import Any, Dict, List, Optional, Protocol
from urllib.parse import urlparse, parse_qs

import pandas as pd
import requests


# ============================================================================
# CORE INTERFACES / БАЗОВЫЕ ИНТЕРФЕЙСЫ
# ============================================================================

class DataExporter(Protocol):
    """Протокол для экспортеров данных"""
    def export(self, data: pd.DataFrame, filename: str, **kwargs) -> str:
        """Экспортирует данные в файл"""
        ...

class DataProcessor(Protocol):
    """Протокол для обработчиков данных"""
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Обрабатывает данные"""
        ...


# ============================================================================
# CORE CLIENT / ОСНОВНОЙ КЛИЕНТ
# ============================================================================

class GoogleSheetsClient:
    """Простой клиент для работы с Google Sheets Export API"""
    
    BASE_EXPORT_URL = "https://docs.google.com/spreadsheets/d/{sheet_id}/export"
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'UniversalSheetsConverter/2.0'
        })
    
    @staticmethod
    def extract_sheet_id(url: str) -> str:
        """Извлекает ID таблицы из URL"""
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"Invalid Google Sheets URL: {url}")
        return match.group(1)
    
    def get_csv_data(self, sheet_id: str, gid: Optional[str] = None) -> str:
        """Получает CSV данные листа"""
        url = self.BASE_EXPORT_URL.format(sheet_id=sheet_id)
        params = {'format': 'csv'}
        
        if gid is not None:
            params['gid'] = gid
            
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        
        return response.content.decode('utf-8')
    
    def get_available_formats(self) -> List[str]:
        """Возвращает список доступных форматов экспорта"""
        return ['csv', 'xlsx', 'ods', 'pdf', 'tsv', 'zip']
    
    def export_raw(self, sheet_id: str, format_type: str, gid: Optional[str] = None) -> bytes:
        """Экспортирует лист в указанном формате"""
        if format_type not in self.get_available_formats():
            raise ValueError(f"Unsupported format: {format_type}")
            
        url = self.BASE_EXPORT_URL.format(sheet_id=sheet_id)
        params = {'format': format_type}
        
        if gid is not None:
            params['gid'] = gid
            
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        
        return response.content


# ============================================================================
# DATA PROCESSORS / ОБРАБОТЧИКИ ДАННЫХ
# ============================================================================

class BaseDataProcessor:
    """Базовый класс для обработчиков данных"""
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Переопределите этот метод в подклассах"""
        return data


class TextFieldProcessor(BaseDataProcessor):
    """Обработчик текстовых полей"""
    
    def __init__(self, text_fields: List[str]):
        self.text_fields = text_fields
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Обрабатывает переносы строк в текстовых полях"""
        df = data.copy()
        
        for field in self.text_fields:
            if field in df.columns:
                df[field] = df[field].astype(str).str.replace('\n', '\\n', regex=False)
                df[field] = df[field].str.replace('\r', '', regex=False)
        
        return df


class HeaderValidator(BaseDataProcessor):
    """Валидатор заголовков"""
    
    def __init__(self, expected_headers: List[str], strict: bool = True):
        self.expected_headers = expected_headers
        self.strict = strict
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Проверяет и нормализует заголовки"""
        if self.strict:
            actual_headers = data.columns.tolist()
            if len(actual_headers) != len(self.expected_headers):
                raise ValueError(
                    f"Header count mismatch: {len(actual_headers)} != {len(self.expected_headers)}"
                )
            
            for i, (actual, expected) in enumerate(zip(actual_headers, self.expected_headers)):
                if actual.strip().lower() != expected.lower():
                    raise ValueError(f"Header mismatch at position {i}: '{actual}' != '{expected}'")
        
        # Нормализуем заголовки
        data.columns = [col.strip().lower() for col in data.columns]
        return data


# ============================================================================
# DATA EXPORTERS / ЭКСПОРТЕРЫ ДАННЫХ
# ============================================================================

class BaseExporter(ABC):
    """Базовый класс для экспортеров"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
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
    """Экспортер в CSV формат"""
    
    def get_extension(self) -> str:
        return 'csv'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        separator = kwargs.get('separator', ';')
        encoding = kwargs.get('encoding', 'utf-8')
        
        data.to_csv(filepath, sep=separator, encoding=encoding, index=False, quoting=1)


class JSONExporter(BaseExporter):
    """Экспортер в JSON формат"""
    
    def get_extension(self) -> str:
        return 'json'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        orient = kwargs.get('orient', 'records')
        indent = kwargs.get('indent', 4)
        
        data_dict = data.to_dict(orient)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=indent)


class ExcelExporter(BaseExporter):
    """Экспортер в Excel формат"""
    
    def get_extension(self) -> str:
        return 'xlsx'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        sheet_name = kwargs.get('sheet_name', 'Sheet1')
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            data.to_excel(writer, sheet_name=sheet_name, index=False)


class XMLExporter(BaseExporter):
    """Экспортер в XML формат"""
    
    def get_extension(self) -> str:
        return 'xml'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        root_name = kwargs.get('root_name', 'data')
        row_name = kwargs.get('row_name', 'record')
        
        data.to_xml(filepath, root_name=root_name, row_name=row_name)


class ParquetExporter(BaseExporter):
    """Экспортер в Parquet формат"""
    
    def get_extension(self) -> str:
        return 'parquet'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        compression = kwargs.get('compression', 'snappy')
        
        data.to_parquet(filepath, compression=compression)


# ============================================================================
# MAIN CONVERTER / ОСНОВНОЙ КОНВЕРТЕР
# ============================================================================

class UniversalSheetsConverter:
    """Универсальный конвертер Google Sheets"""
    
    def __init__(self, output_dir: str = "output"):
        self.client = GoogleSheetsClient()
        self.output_dir = output_dir
        self.processors: List[DataProcessor] = []
        self.exporters: Dict[str, BaseExporter] = {}
        self._register_default_exporters()
    
    def _register_default_exporters(self):
        """Регистрирует экспортеры по умолчанию"""
        self.register_exporter('csv', CSVExporter(self.output_dir))
        self.register_exporter('json', JSONExporter(self.output_dir))
        self.register_exporter('xlsx', ExcelExporter(self.output_dir))
        self.register_exporter('xml', XMLExporter(self.output_dir))
        self.register_exporter('parquet', ParquetExporter(self.output_dir))
    
    def register_exporter(self, name: str, exporter: BaseExporter) -> None:
        """Регистрирует новый экспортер"""
        self.exporters[name] = exporter
    
    def add_processor(self, processor: DataProcessor) -> None:
        """Добавляет обработчик данных"""
        self.processors.append(processor)
    
    def load_sheet(self, url_or_id: str, gid: Optional[str] = None) -> pd.DataFrame:
        """Загружает данные листа"""
        # Определяем ID таблицы
        if url_or_id.startswith('http'):
            sheet_id = self.client.extract_sheet_id(url_or_id)
        else:
            sheet_id = url_or_id
        
        # Получаем CSV данные
        csv_data = self.client.get_csv_data(sheet_id, gid)
        
        # Загружаем в DataFrame
        df = pd.read_csv(StringIO(csv_data))
        
        # Убираем пустые строки
        df = df.dropna(how='all')
        
        # Применяем обработчики
        for processor in self.processors:
            df = processor.process(df)
        
        return df
    
    def convert(self, url_or_id: str, formats: List[str], 
                filename_base: str = "sheet", gid: Optional[str] = None, 
                **export_kwargs) -> Dict[str, str]:
        """Конвертирует лист в указанные форматы"""
        
        # Загружаем данные
        data = self.load_sheet(url_or_id, gid)
        
        # Экспортируем в каждый формат
        exported_files = {}
        
        for format_name in formats:
            if format_name not in self.exporters:
                raise ValueError(f"Unknown format: {format_name}. Available: {list(self.exporters.keys())}")
            
            exporter = self.exporters[format_name]
            kwargs = export_kwargs.get(format_name, {})
            
            filepath = exporter.export(data, filename_base, **kwargs)
            exported_files[format_name] = filepath
        
        return exported_files


# ============================================================================
# CONVENIENCE FUNCTIONS / ФУНКЦИИ УДОБСТВА
# ============================================================================

def quick_convert(url: str, formats: List[str] = None, filename: str = "sheet") -> Dict[str, str]:
    """Быстрая конвертация с настройками по умолчанию"""
    if formats is None:
        formats = ['csv', 'json']
    
    converter = UniversalSheetsConverter()
    return converter.convert(url, formats, filename)


def convert_with_validation(url: str, expected_headers: List[str], 
                          text_fields: List[str] = None,
                          formats: List[str] = None) -> Dict[str, str]:
    """Конвертация с валидацией и обработкой текста"""
    if formats is None:
        formats = ['csv', 'json']
    if text_fields is None:
        text_fields = []
    
    converter = UniversalSheetsConverter()
    
    # Добавляем валидатор заголовков
    converter.add_processor(HeaderValidator(expected_headers))
    
    # Добавляем обработчик текстовых полей
    if text_fields:
        converter.add_processor(TextFieldProcessor(text_fields))
    
    return converter.convert(url, formats, "validated_sheet")


# ============================================================================
# EXAMPLE USAGE / ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ============================================================================

if __name__ == "__main__":
    # Пример 1: Простая конвертация
    url = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit"
    
    files = quick_convert(url, formats=['csv', 'json', 'xlsx'])
    print("Экспортированные файлы:", files)
    
    # Пример 2: Конвертация с валидацией (как в вашем скрипте)
    expected_headers = ['category', 'subcategory', 'button_text', 'keywords', 'answer_ukr', 'answer_rus', 'sort_order']
    text_fields = ['answer_ukr', 'answer_rus', 'keywords']
    
    files = convert_with_validation(
        url, 
        expected_headers=expected_headers,
        text_fields=text_fields,
        formats=['csv', 'json', 'xml']
    )
    print("Валидированные файлы:", files)
    
    # Пример 3: Расширенное использование
    converter = UniversalSheetsConverter()
    
    # Добавляем кастомный обработчик
    class CustomProcessor(BaseDataProcessor):
        def process(self, data: pd.DataFrame) -> pd.DataFrame:
            # Ваша логика обработки
            return data.fillna('')
    
    converter.add_processor(CustomProcessor())
    
    # Конвертируем с дополнительными параметрами
    files = converter.convert(
        url, 
        formats=['csv', 'json'], 
        filename_base="custom_export",
        csv={'separator': ',', 'encoding': 'utf-8'},
        json={'orient': 'index', 'indent': 2}
    )
    print("Кастомные файлы:", files)