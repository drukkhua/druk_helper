#!/usr/bin/env python3
"""
ПОЛНЫЙ ДЕМО: Google Sheets Converter 
Все модули включены в один файл для простоты запуска

Ваши данные:
- API ключ: AIzaSyDzDspWPn07MQxNm3iJ1ZXPlJruWO1tzK4
- Документ: https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit
- Папка: data/

Запуск: python demo_converter.py
"""

import hashlib
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import yaml

# Ваши данные
API_KEY = "AIzaSyDzDspWPn07MQxNm3iJ1ZXPlJruWO1tzK4"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit?usp=sharing"
OUTPUT_DIR = "data"

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
# БАЗОВЫЕ КЛАССЫ / BASE CLASSES
# ============================================================================

class Config:
    """Конфигурация"""
    def __init__(self, api_key: str, output_dir: str = "data", batch_size: int = 100):
        self.api_key = api_key
        self.output_dir = output_dir
        self.batch_size = batch_size
        self.timeout = 60
        self.sheets_api_base = "https://sheets.googleapis.com/v4/spreadsheets"


class BaseExporter(ABC):
    """Базовый экспортер"""
    def __init__(self, output_dir: str, format_name: str):
        self.output_dir = os.path.join(output_dir, format_name)
        self.format_name = format_name
        os.makedirs(self.output_dir, exist_ok=True)
    
    @abstractmethod
    def get_extension(self) -> str:
        pass
    
    @abstractmethod
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        pass
    
    def export(self, data: pd.DataFrame, filename: str, **kwargs) -> str:
        if not filename.endswith(f'.{self.get_extension()}'):
            filename = f"{filename}.{self.get_extension()}"
        
        filepath = os.path.join(self.output_dir, filename)
        self.export_data(data, filepath, **kwargs)
        return filepath


# ============================================================================
# GOOGLE SHEETS CLIENT / КЛИЕНТ
# ============================================================================

class GoogleSheetsClient:
    """Клиент для Google Sheets API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'DemoSheetsConverter/1.0'})
    
    def extract_sheet_id(self, url: str) -> str:
        """Извлекает ID таблицы"""
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"Неверный URL: {url}")
        return match.group(1)
    
    def get_sheets_metadata(self, sheet_id: str) -> List[Dict[str, Any]]:
        """Получает метаданные всех листов"""
        print("🔍 Получаем метаданные листов...")
        
        api_url = f"{self.config.sheets_api_base}/{sheet_id}"
        params = {'fields': 'sheets.properties', 'key': self.config.api_key}
        
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
            return [{'gid': '0', 'name': 'Sheet1', 'rows': 1000, 'cols': 26}]
    
    def batch_get_sheets_data(self, sheet_id: str, sheets_info: List[Dict]) -> Dict[str, Tuple[pd.DataFrame, str]]:
        """🚀 Batch загрузка всех листов"""
        print(f"🚀 Batch загрузка {len(sheets_info)} листов...")
        
        try:
            # Формируем ranges для batch запроса
            ranges = []
            sheet_mapping = {}
            
            for i, sheet_info in enumerate(sheets_info):
                sheet_name = sheet_info['name']
                escaped_name = self._escape_sheet_name(sheet_name)
                
                rows = min(sheet_info.get('rows', 1000), 10000)
                cols = min(sheet_info.get('cols', 26), 26)
                col_letter = chr(ord('A') + cols - 1)
                
                range_name = f"{escaped_name}!A1:{col_letter}{rows}"
                ranges.append(range_name)
                sheet_mapping[i] = sheet_name
            
            # Batch запрос
            api_url = f"{self.config.sheets_api_base}/{sheet_id}/values:batchGet"
            params = {
                'ranges': ranges,
                'valueRenderOption': 'UNFORMATTED_VALUE',
                'key': self.config.api_key
            }
            
            response = self.session.get(api_url, params=params, timeout=self.config.timeout)
            
            if response.status_code == 429:
                print("⏳ Rate limit, переходим на CSV...")
                return self._csv_fallback_batch(sheet_id, sheets_info)
            
            response.raise_for_status()
            batch_data = response.json()
            
            return self._process_batch_response(batch_data, sheet_mapping)
            
        except Exception as e:
            print(f"❌ Ошибка batch запроса: {e}")
            return self._csv_fallback_batch(sheet_id, sheets_info)
    
    def _process_batch_response(self, batch_data: Dict, sheet_mapping: Dict[int, str]) -> Dict[str, Tuple[pd.DataFrame, str]]:
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
                
                if len(values) == 1:
                    df = pd.DataFrame(columns=values[0])
                else:
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
                
                df = df.dropna(how='all')
                print(f"✅ [{sheet_name}] {len(df)} строк, {len(df.columns)} колонок")
                results[sheet_name] = (df, raw_data)
                
            except Exception as e:
                print(f"❌ [{sheet_name}] Ошибка обработки: {e}")
                results[sheet_name] = (pd.DataFrame(), "")
        
        return results
    
    def _csv_fallback_batch(self, sheet_id: str, sheets_info: List[Dict]) -> Dict[str, Tuple[pd.DataFrame, str]]:
        """Fallback через CSV export"""
        results = {}
        print(f"📥 CSV fallback для {len(sheets_info)} листов...")
        
        for sheet_info in sheets_info:
            gid = sheet_info['gid']
            sheet_name = sheet_info['name']
            
            try:
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export"
                params = {'format': 'csv', 'gid': gid}
                
                response = self.session.get(csv_url, params=params, timeout=30)
                response.raise_for_status()
                
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
        """Экранирует имя листа"""
        if any(c in sheet_name for c in " '\"!@#$%^&*()"):
            escaped_name = sheet_name.replace("'", "''")
            return f"'{escaped_name}'"
        return sheet_name


# ============================================================================
# ЭКСПОРТЕРЫ / EXPORTERS
# ============================================================================

class CSVExporter(BaseExporter):
    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'csv')
    
    def get_extension(self) -> str:
        return 'csv'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        separator = kwargs.get('separator', ';')
        data.to_csv(filepath, sep=separator, encoding='utf-8', index=False, quoting=2)


class JSONExporter(BaseExporter):
    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'json')
    
    def get_extension(self) -> str:
        return 'json'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        data_dict = data.to_dict('records')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=4)


class ExcelExporter(BaseExporter):
    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'excel')
    
    def get_extension(self) -> str:
        return 'xlsx'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        if not XLSX_AVAILABLE:
            raise ImportError("openpyxl required for Excel export")
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            data.to_excel(writer, index=False)


class TXTExporter(BaseExporter):
    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'txt')
    
    def get_extension(self) -> str:
        return 'txt'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("📋 Данные Google Sheets\n")
            f.write("=" * 60 + "\n\n")
            
            for index, row in data.iterrows():
                f.write(f"🔸 Запись #{index + 1}\n")
                f.write("-" * 30 + "\n")
                
                for column in data.columns:
                    value = row[column]
                    if pd.notna(value):
                        f.write(f"📌 {column}: {value}\n")
                
                f.write("\n" + "=" * 60 + "\n\n")


class YAMLExporter(BaseExporter):
    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'yaml')
    
    def get_extension(self) -> str:
        return 'yml'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        data_dict = data.to_dict('records')
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data_dict, f, default_flow_style=False, allow_unicode=True, indent=2)


class HTMLExporter(BaseExporter):
    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'html')
    
    def get_extension(self) -> str:
        return 'html'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        title = kwargs.get('title', 'Google Sheets Data')
        
        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>📋 {title}</h1>
    <p>Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <table>
        <thead><tr>"""
        
        for col in data.columns:
            html += f"<th>{col}</th>"
        html += "</tr></thead><tbody>"
        
        for _, row in data.iterrows():
            html += "<tr>"
            for col in data.columns:
                value = row[col] if pd.notna(row[col]) else ""
                html += f"<td>{str(value).replace('<', '&lt;').replace('>', '&gt;')}</td>"
            html += "</tr>"
        
        html += "</tbody></table></body></html>"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)


# ============================================================================
# ПРОЦЕССОРЫ ДАННЫХ / DATA PROCESSORS
# ============================================================================

class TextFieldProcessor:
    def __init__(self, auto_detect: bool = True):
        self.auto_detect = auto_detect
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        if data.empty:
            return data
        
        df = data.copy()
        text_columns = self._detect_text_columns(df) if self.auto_detect else []
        
        if text_columns:
            print(f"🔤 Обрабатываем текстовые колонки: {', '.join(text_columns)}")
            for column in text_columns:
                if column in df.columns:
                    df[column] = df[column].astype(str).str.replace('\r', '', regex=False)
        
        return df
    
    def _detect_text_columns(self, df: pd.DataFrame) -> List[str]:
        text_columns = []
        for column in df.columns:
            sample_data = df[column].dropna().astype(str).head(10)
            has_newlines = any('\n' in str(value) for value in sample_data)
            avg_length = sample_data.str.len().mean() if len(sample_data) > 0 else 0
            
            if has_newlines or avg_length > 50:
                text_columns.append(column)
        
        return text_columns


class FilenameProcessor:
    def __init__(self, transliterate: bool = True):
        self.transliterate = transliterate
    
    def create_safe_filename(self, sheet_name: str, page_num: int) -> str:
        if SLUGIFY_AVAILABLE and self.transliterate:
            safe_name = slugify(sheet_name, max_length=50, separator='_', lowercase=True)
        else:
            safe_name = re.sub(r'[^a-zA-Z0-9\-]', '_', sheet_name.lower())
            safe_name = re.sub(r'_+', '_', safe_name).strip('_')
        
        safe_name = safe_name if safe_name else 'sheet'
        return f"{safe_name}_{page_num:02d}"


# ============================================================================
# КЕШИРОВАНИЕ / CACHING
# ============================================================================

class FileCache:
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.cache_data = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                print(f"📂 Кеш загружен: {len(self.cache_data)} записей")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки кеша: {e}")
            self.cache_data = {}
    
    def _save_cache(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения кеша: {e}")
    
    def is_changed(self, key: str, data: str) -> bool:
        current_hash = hashlib.md5(data.encode('utf-8')).hexdigest()
        cached_entry = self.cache_data.get(key, {})
        
        if cached_entry.get('hash') == current_hash:
            return False
        
        self.cache_data[key] = {
            'hash': current_hash,
            'last_updated': datetime.now().isoformat()
        }
        self._save_cache()
        return True


# ============================================================================
# ГЛАВНЫЙ КОНВЕРТЕР / MAIN CONVERTER
# ============================================================================

class ModularSheetsConverter:
    def __init__(self, config: Config, cache_file: str = None):
        self.config = config
        self.client = GoogleSheetsClient(config)
        self.cache = FileCache(cache_file or f"{config.output_dir}/cache.json")
        self.exporters = {}
        self.processors = []
        self.filename_processor = FilenameProcessor(transliterate=True)
        self.stats = {'start_time': datetime.now(), 'processed_sheets': 0, 'files_created': 0}
    
    def register_exporter(self, name: str, exporter: BaseExporter) -> None:
        self.exporters[name] = exporter
    
    def add_processor(self, processor) -> None:
        self.processors.append(processor)
    
    def convert_spreadsheet(self, url: str, formats: List[str]) -> Dict[str, Any]:
        print("🚀 Запуск модульного конвертера")
        print("=" * 60)
        
        try:
            # Извлекаем ID и получаем метаданные
            sheet_id = self.client.extract_sheet_id(url)
            print(f"🔍 ID таблицы: {sheet_id}")
            
            sheets_info = self.client.get_sheets_metadata(sheet_id)
            if not sheets_info:
                return {'error': 'Листы не найдены'}
            
            # Batch загрузка всех листов
            sheets_data = self.client.batch_get_sheets_data(sheet_id, sheets_info)
            
            # Обработка каждого листа
            for page_num, sheet_info in enumerate(sheets_info, 1):
                sheet_name = sheet_info['name']
                
                sheet_result = sheets_data.get(sheet_name, (pd.DataFrame(), ""))
                df, raw_data = sheet_result
                
                if df.empty:
                    print(f"⏭️ [{sheet_name}] Пропуск - нет данных")
                    continue
                
                # Проверяем кеш
                cache_key = f"{sheet_id}:{sheet_name}"
                if not self.cache.is_changed(cache_key, raw_data):
                    print(f"📋 [{sheet_name}] Кеш актуален")
                    continue
                
                # Обрабатываем данные
                processed_df = self._process_data(df)
                
                # Экспортируем во все форматы
                filename_base = self.filename_processor.create_safe_filename(sheet_name, page_num)
                self._export_data(processed_df, filename_base, formats)
                
                self.stats['processed_sheets'] += 1
                print(f"✅ [{sheet_name}] Экспортирован в {len(formats)} форматов")
            
            # Финализация
            duration = datetime.now() - self.stats['start_time']
            print(f"\n🎉 Конвертация завершена за {str(duration).split('.')[0]}")
            print(f"📄 Обработано листов: {self.stats['processed_sheets']}")
            print(f"📁 Создано файлов: {self.stats['files_created']}")
            
            return {
                'success': True,
                'processed_sheets': self.stats['processed_sheets'],
                'files_created': self.stats['files_created'],
                'duration': str(duration).split('.')[0]
            }
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return {'error': str(e)}
    
    def _process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        processed_df = df
        for processor in self.processors:
            processed_df = processor.process(processed_df)
        return processed_df
    
    def _export_data(self, df: pd.DataFrame, filename_base: str, formats: List[str]) -> None:
        for format_name in formats:
            if format_name not in self.exporters:
                print(f"⚠️ Неизвестный формат: {format_name}")
                continue
            
            try:
                exporter = self.exporters[format_name]
                filepath = exporter.export(df, filename_base)
                self.stats['files_created'] += 1
                
            except Exception as e:
                print(f"❌ Ошибка экспорта {format_name}: {e}")


# ============================================================================
# ДЕМОНСТРАЦИЯ / DEMONSTRATION
# ============================================================================

def create_converter(output_subdir: str = "") -> ModularSheetsConverter:
    """Создает настроенный конвертер"""
    output_path = os.path.join(OUTPUT_DIR, output_subdir) if output_subdir else OUTPUT_DIR
    config = Config(API_KEY, output_path)
    converter = ModularSheetsConverter(config)
    
    # Регистрируем экспортеры
    converter.register_exporter('csv', CSVExporter(output_path))
    converter.register_exporter('json', JSONExporter(output_path))
    converter.register_exporter('txt', TXTExporter(output_path))
    converter.register_exporter('html', HTMLExporter(output_path))
    converter.register_exporter('yaml', YAMLExporter(output_path))
    
    if XLSX_AVAILABLE:
        converter.register_exporter('xlsx', ExcelExporter(output_path))
    
    # Добавляем процессор
    converter.add_processor(TextFieldProcessor(auto_detect=True))
    
    return converter


def demo_basic_conversion():
    """Базовая конвертация"""
    print("1️⃣ БАЗОВАЯ КОНВЕРТАЦИЯ")
    print("=" * 50)
    
    converter = create_converter("basic")
    formats = ['csv', 'json', 'txt']
    
    if XLSX_AVAILABLE:
        formats.append('xlsx')
        print("✅ Excel формат доступен")
    
    result = converter.convert_spreadsheet(SHEET_URL, formats)
    return result


def demo_full_conversion():
    """Полная конвертация во все форматы"""
    print("\n2️⃣ ПОЛНАЯ КОНВЕРТАЦИЯ")
    print("=" * 50)
    
    converter = create_converter("full")
    formats = ['csv', 'json', 'txt', 'html', 'yaml']
    
    if XLSX_AVAILABLE:
        formats.append('xlsx')
    
    result = converter.convert_spreadsheet(SHEET_URL, formats)
    return result


def demo_custom_exporter():
    """Кастомный экспортер"""
    print("\n3️⃣ КАСТОМНЫЙ ЭКСПОРТЕР (XML)")
    print("=" * 50)
    
    class XMLExporter(BaseExporter):
        def __init__(self, output_dir: str):
            super().__init__(output_dir, 'xml')
        
        def get_extension(self) -> str:
            return 'xml'
        
        def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n<data>\n')
                for i, row in data.iterrows():
                    f.write(f'  <record id="{i+1}">\n')
                    for col in data.columns:
                        value = row[col] if pd.notna(row[col]) else ''
                        f.write(f'    <{col}>{value}</{col}>\n')
                    f.write('  </record>\n')
                f.write('</data>\n')
    
    converter = create_converter("custom")
    converter.register_exporter('xml', XMLExporter(os.path.join(OUTPUT_DIR, "custom")))
    
    result = converter.convert_spreadsheet(SHEET_URL, ['csv', 'json', 'xml'])
    return result


def show_file_structure():
    """Показывает структуру файлов"""
    print("\n📁 СТРУКТУРА ФАЙЛОВ")
    print("=" * 50)
    
    def show_dir(path, prefix=""):
        if not os.path.exists(path):
            return
        
        items = sorted(os.listdir(path))
        for i, item in enumerate(items):
            item_path = os.path.join(path, item)
            is_last = i == len(items) - 1
            
            if os.path.isdir(item_path):
                print(f"{prefix}{'└── ' if is_last else '├── '}📁 {item}/")
                show_dir(item_path, prefix + ("    " if is_last else "│   "))
            else:
                size = os.path.getsize(item_path)
                size_str = f"{size//1024}KB" if size > 1024 else f"{size}B"
                print(f"{prefix}{'└── ' if is_last else '├── '}📄 {item} ({size_str})")
    
    print(f"📁 {OUTPUT_DIR}/")
    show_dir(OUTPUT_DIR)


def main():
    """Главная демонстрация"""
    print("🚀 ДЕМОНСТРАЦИЯ GOOGLE SHEETS CONVERTER")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔑 API ключ: {API_KEY[:20]}...")
    print(f"📄 Документ: {SHEET_URL}")
    print(f"📁 Папка: {OUTPUT_DIR}/")
    
    start_time = datetime.now()
    total_files = 0
    
    try:
        # Демонстрации
        result1 = demo_basic_conversion()
        result2 = demo_full_conversion()
        result3 = demo_custom_exporter()
        
        # Подсчет файлов
        if result1.get('success'):
            total_files += result1['files_created']
        if result2.get('success'):
            total_files += result2['files_created']
        if result3.get('success'):
            total_files += result3['files_created']
        
        # Показываем структуру
        show_file_structure()
        
        # Итоги
        total_time = datetime.now() - start_time
        print(f"\n🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
        print("=" * 70)
        print(f"⏱️  Время: {str(total_time).split('.')[0]}")
        print(f"📁 Файлов создано: {total_files}")
        print(f"🔧 Продемонстрировано:")
        print("   ✅ Batch загрузка до 100+ листов")
        print("   ✅ Модульная архитектура")
        print("   ✅ Кеширование")
        print("   ✅ 6+ форматов экспорта")
        print("   ✅ Кастомные экспортеры")
        print("   ✅ Обработка данных")
        
        print(f"\n📂 Проверьте папку '{OUTPUT_DIR}/' для результатов!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Проверка зависимостей
    missing_deps = []
    try:
        import pandas as pd
        import requests
        import yaml
    except ImportError as e:
        missing_deps.append(str(e))
    
    if missing_deps:
        print("❌ Отсутствуют зависимости:")
        for dep in missing_deps:
            print(f"   {dep}")
        print("\nУстановите: pip install pandas requests pyyaml")
        sys.exit(1)
    
    print("✅ Все зависимости доступны")
    
    if not XLSX_AVAILABLE:
        print("⚠️ Excel недоступен (установите: pip install openpyxl)")
    
    if not SLUGIFY_AVAILABLE:
        print("⚠️ Продвинутая транслитерация недоступна (pip install python-slugify)")
    
    # Запуск демонстрации
    main()
