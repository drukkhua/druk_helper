#!/usr/bin/env python3
"""
Universal Google Sheets to Multiple Formats Converter
Универсальный конвертер Google Таблиц в различные форматы
ОПТИМИЗИРОВАННАЯ ВЕРСИЯ с batch запросами и кешированием
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests
import yaml
from config import GOOGLE_SHEETS_API_KEY

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

# Константы
URL_TEST = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit?usp=sharing"
FILE_PATH = "../converted-data"
CACHE_FILE = "../converted-data/.cache.json"


class UniversalSheetsConverter:
    def __init__(self, formats=['csv', 'json', 'txt'], transliterate=True, enable_caching=True):
        self.enabled_formats = set(formats)
        self.transliterate_names = transliterate
        self.output_dir = FILE_PATH
        self.api_key = GOOGLE_SHEETS_API_KEY
        self.enable_caching = enable_caching
        self.cache = {}

        # Доступные форматы
        self.available_formats = {
            'csv': {'name': 'CSV файлы (для парсеров)', 'ext': 'csv', 'folder': 'csv'},
            'json': {'name': 'JSON файлы (структурированные данные)', 'ext': 'json', 'folder': 'json'},
            'txt': {'name': 'TXT файлы (для просмотра)', 'ext': 'txt', 'folder': 'txt'},
            'xlsx': {'name': 'Excel файлы (редактирование)', 'ext': 'xlsx', 'folder': 'excel'},
            'md': {'name': 'Markdown документы (документация)', 'ext': 'md', 'folder': 'markdown'},
            'html': {'name': 'HTML страницы (браузер)', 'ext': 'html', 'folder': 'html'},
            'yaml': {'name': 'YAML конфигурации (DevOps)', 'ext': 'yml', 'folder': 'yaml'}
        }

        # Статистика для отчета
        self.stats = {
            'start_time': datetime.now(),
            'end_time': None,
            'total_sheets': 0,
            'processed_sheets': 0,
            'skipped_sheets': 0,
            'cached_sheets': 0,
            'batch_requests_used': 0,
            'formats_used': list(self.enabled_formats),
            'transliteration_enabled': self.transliterate_names,
            'caching_enabled': self.enable_caching,
            'sheets_details': [],
            'files_created': []
        }

        # Проверяем доступность форматов и загружаем кеш
        self._check_format_availability()
        self._load_cache()

    def _check_format_availability(self):
        """Проверяет доступность форматов и предупреждает о недостающих библиотеках"""
        if 'xlsx' in self.enabled_formats and not XLSX_AVAILABLE:
            print("⚠️ Для Excel формата нужна библиотека openpyxl: pip install openpyxl")
            self.enabled_formats.discard('xlsx')

        if self.transliterate_names and not SLUGIFY_AVAILABLE:
            print("⚠️ Для универсальной транслитерации рекомендуется: pip install python-slugify")
            print("📝 Будет использована базовая транслитерация")

    def _load_cache(self):
        """Загружает кеш из файла"""
        if not self.enable_caching:
            return

        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                print(f"📂 Загружен кеш: {len(self.cache)} записей")
            else:
                self.cache = {}
        except Exception as e:
            print(f"⚠️ Ошибка загрузки кеша: {e}")
            self.cache = {}

    def _save_cache(self):
        """Сохраняет кеш в файл"""
        if not self.enable_caching:
            return

        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            print(f"💾 Кеш сохранен: {len(self.cache)} записей")
        except Exception as e:
            print(f"⚠️ Ошибка сохранения кеша: {e}")

    def _get_sheet_hash(self, sheet_data: str) -> str:
        """Создает хеш данных листа для проверки изменений"""
        return hashlib.md5(sheet_data.encode('utf-8')).hexdigest()

    def _is_sheet_changed(self, sheet_id: str, sheet_name: str, sheet_data: str) -> bool:
        """Проверяет, изменился ли лист с последнего раза"""
        if not self.enable_caching:
            return True

        cache_key = f"{sheet_id}:{sheet_name}"
        current_hash = self._get_sheet_hash(sheet_data)

        if cache_key in self.cache:
            cached_hash = self.cache[cache_key].get('hash')
            if cached_hash == current_hash:
                print(f"📋 [{sheet_name}] Не изменился, используем кеш")
                return False

        # Обновляем кеш
        self.cache[cache_key] = {
            'hash': current_hash,
            'last_updated': datetime.now().isoformat()
        }
        return True

    def create_output_directories(self):
        """Создает выходные директории для всех форматов"""
        for format_key in self.enabled_formats:
            if format_key in self.available_formats:
                folder_path = os.path.join(self.output_dir, self.available_formats[format_key]['folder'])
                os.makedirs(folder_path, exist_ok=True)

        print(f"📁 Рабочая директория: {self.output_dir}/")
        print(f"📋 Активные форматы: {', '.join(self.enabled_formats)}")
        if self.enable_caching:
            print("🚀 Кеширование включено")

    def extract_sheet_id(self, url: str) -> str:
        """Извлекает ID таблицы из URL"""
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        if not match:
            raise ValueError("Неверная ссылка на Google Таблицу")
        return match.group(1)

    def get_all_sheets_info(self, sheet_id: str) -> List[Dict[str, Any]]:
        """Получает информацию о всех страницах через официальный Google Sheets API"""
        print("🔍 Получаем информацию о листах через Google Sheets API...")

        try:
            api_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
            params = {}
            if self.api_key:
                params['key'] = self.api_key
                print(f"🔑 Используем API key: {self.api_key[:20]}...")

            headers = {'User-Agent': 'UniversalSheetsConverter/1.0'}
            response = requests.get(api_url, params=params, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                sheets_info = []

                sheets = data.get('sheets', [])
                for sheet in sheets:
                    sheet_properties = sheet.get('properties', {})
                    sheet_id_num = sheet_properties.get('sheetId', 0)
                    sheet_title = sheet_properties.get('title', f'Sheet{sheet_id_num}')

                    sheets_info.append({
                        'gid': str(sheet_id_num),
                        'name': sheet_title
                    })

                if sheets_info:
                    print(f"📄 Найдено страниц через API: {len(sheets_info)}")
                    for i, sheet in enumerate(sheets_info, 1):
                        print(f"   {i}. '{sheet['name']}' (gid: {sheet['gid']})")
                    return sheets_info
                else:
                    print("⚠️ API вернул пустой список листов")
                    return [{'gid': '0', 'name': 'Sheet1'}]

            elif response.status_code == 403:
                print(f"❌ Ошибка доступа (HTTP 403)")
                print("💡 Проверьте правильность API ключа и настройки доступа к таблице")
                return [{'gid': '0', 'name': 'Sheet1'}]

            elif response.status_code == 404:
                print(f"❌ Таблица не найдена (HTTP 404)")
                print("💡 Проверьте правильность ID таблицы")
                return [{'gid': '0', 'name': 'Sheet1'}]

            else:
                print(f"❌ API вернул ошибку HTTP {response.status_code}")
                return [{'gid': '0', 'name': 'Sheet1'}]

        except requests.RequestException as e:
            print(f"❌ Ошибка сети при обращении к API: {e}")
            return [{'gid': '0', 'name': 'Sheet1'}]

        except Exception as e:
            print(f"❌ Неожиданная ошибка при работе с API: {e}")
            return [{'gid': '0', 'name': 'Sheet1'}]

    def load_all_sheets_batch(self, sheet_id: str, sheets_info: List[Dict]) -> Dict[str, Tuple[pd.DataFrame, bool, str]]:
        """
        🚀 НОВЫЙ МЕТОД: Загружает ВСЕ листы одним batch запросом через Google Sheets API
        Возвращает: Dict[sheet_name, (DataFrame, success, raw_data)]
        """
        results = {}

        try:
            # Формируем ranges для batch запроса
            ranges = []
            sheet_mapping = {}

            for sheet_info in sheets_info:
                sheet_name = sheet_info['name']
                # Экранируем имена листов с пробелами и спецсимволами
                escaped_name = f"'{sheet_name}'" if any(c in sheet_name for c in " '\"!@#$%^&*()") else sheet_name
                range_name = f"{escaped_name}!A:ZZ"  # Берем все данные до колонки ZZ
                ranges.append(range_name)
                sheet_mapping[len(ranges) - 1] = sheet_name

            print(f"🚀 Batch загрузка {len(ranges)} листов одним запросом...")

            # ГЛАВНЫЙ BATCH ЗАПРОС через Google Sheets API v4
            api_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchGet"
            params = {
                'ranges': ranges,
                'valueRenderOption': 'UNFORMATTED_VALUE',
                'key': self.api_key
            }

            headers = {'User-Agent': 'UniversalSheetsConverter/1.0'}
            response = requests.get(api_url, params=params, headers=headers, timeout=60)

            if response.status_code == 429:  # Rate limit
                print("⏳ Достигнут лимит API, переключаемся на CSV fallback...")
                return self._load_sheets_csv_fallback(sheet_id, sheets_info)

            if response.status_code != 200:
                print(f"❌ Batch API ошибка: HTTP {response.status_code}")
                print("🔄 Переключаемся на CSV fallback...")
                return self._load_sheets_csv_fallback(sheet_id, sheets_info)

            batch_data = response.json()
            value_ranges = batch_data.get('valueRanges', [])

            # Обрабатываем результаты
            for i, value_range in enumerate(value_ranges):
                sheet_name = sheet_mapping[i]

                try:
                    values = value_range.get('values', [])
                    raw_data = json.dumps(values, ensure_ascii=False)  # Для кеширования

                    if not values:
                        results[sheet_name] = (pd.DataFrame(), False, raw_data)
                        continue

                    # Создаем DataFrame
                    headers = values[0] if values else []
                    data_rows = values[1:] if len(values) > 1 else []

                    df = pd.DataFrame(data_rows, columns=headers)
                    df = df.dropna(how='all')  # Удаляем пустые строки

                    print(f"✅ [{sheet_name}] {len(df)} строк, {len(df.columns)} колонок")
                    results[sheet_name] = (df, True, raw_data)

                except Exception as e:
                    print(f"❌ [{sheet_name}] Ошибка обработки: {e}")
                    results[sheet_name] = (pd.DataFrame(), False, "")

            self.stats['batch_requests_used'] += 1
            print(f"🎉 Batch загрузка завершена за 1 API запрос! (экономия: {len(ranges) - 1} запросов)")
            return results

        except Exception as e:
            print(f"❌ Ошибка batch загрузки: {e}")
            print("🔄 Переключаемся на CSV fallback...")
            return self._load_sheets_csv_fallback(sheet_id, sheets_info)

    def _load_sheets_csv_fallback(self, sheet_id: str, sheets_info: List[Dict]) -> Dict[str, Tuple[pd.DataFrame, bool, str]]:
        """Fallback метод: загрузка через CSV export (оригинальный способ)"""
        results = {}

        print(f"📥 CSV fallback для {len(sheets_info)} листов...")

        for sheet_info in sheets_info:
            gid = sheet_info['gid']
            sheet_name = sheet_info['name']

            try:
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
                print(f"📥 Загружаем: {sheet_name}")

                df = pd.read_csv(csv_url)
                df = df.dropna(how='all')

                # Создаем raw_data для кеширования
                raw_data = df.to_csv(index=False)

                print(f"✅ [{sheet_name}] {len(df)} строк, {len(df.columns)} колонок")
                results[sheet_name] = (df, True, raw_data)

            except Exception as e:
                print(f"❌ [{sheet_name}] Ошибка: {e}")
                results[sheet_name] = (pd.DataFrame(), False, "")

        return results

    def detect_text_columns(self, df: pd.DataFrame) -> List[str]:
        """Автоматически определяет текстовые колонки для обработки переносов строк"""
        text_columns = []

        for column in df.columns:
            # Проверяем несколько строк на наличие переносов
            sample_data = df[column].dropna().astype(str).head(10)
            has_newlines = any('\n' in str(value) for value in sample_data)

            # Если есть переносы строк или длинный текст, считаем текстовой колонкой
            avg_length = sample_data.str.len().mean() if len(sample_data) > 0 else 0

            if has_newlines or avg_length > 50:  # Порог длины текста
                text_columns.append(column)

        return text_columns

    def process_text_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Обрабатывает текстовые поля - очищает лишние символы, но сохраняет нативные переносы"""
        df_processed = df.copy()
        text_columns = self.detect_text_columns(df)

        if text_columns:
            print(f"🔤 Обрабатываем текстовые колонки: {', '.join(text_columns)}")

            for column in text_columns:
                if column in df_processed.columns:
                    # Убираем только лишние \r символы, оставляем нативные \n
                    df_processed[column] = df_processed[column].astype(str).str.replace('\r', '', regex=False)

        return df_processed

    def create_safe_filename(self, sheet_name: str, page_num: int) -> str:
        """
        🌍 УНИВЕРСАЛЬНАЯ ТРАНСЛИТЕРАЦИЯ: Создает безопасное имя файла из названия листа любого языка
        Поддерживает: русский, китайский, японский, арабский, корейский, хинди, тайский и др.
        """
        if not self.transliterate_names:
            # Если транслитерация отключена, используем базовую очистку
            clean_name = re.sub(r'[^a-zA-Z0-9\-\u0400-\u04FF]', '_', sheet_name)  # Разрешаем кириллицу
            clean_name = re.sub(r'_+', '_', clean_name).strip('_').lower()
            safe_name = clean_name if clean_name else 'sheet'
        else:
            if SLUGIFY_AVAILABLE:
                # 🚀 Универсальная транслитерация с python-slugify
                safe_name = slugify(
                    sheet_name,
                    max_length=50,  # Ограничиваем длину
                    word_boundary=True,  # Обрезаем по границам слов
                    separator='_',  # Используем подчеркивания вместо дефисов
                    lowercase=True,  # Нижний регистр
                    replacements=[  # Дополнительные замены
                        ('№', 'no'),
                        ('§', 'section'),
                        ('&', 'and'),
                        ('%', 'percent'),
                        ('$', 'dollar'),
                        ('€', 'euro'),
                        ('₽', 'rub'),
                        ('£', 'pound'),
                        ('¥', 'yen'),
                        ('₩', 'won'),
                        ('₴', 'hrn'),
                        ('₸', 'tenge'),
                        ('₦', 'naira'),
                        ('₹', 'rupee'),
                        ('©', 'copyright'),
                        ('®', 'registered'),
                        ('™', 'trademark'),
                        ('°', 'degree'),
                        ('±', 'plus_minus'),
                        ('×', 'multiply'),
                        ('÷', 'divide'),
                        ('≈', 'approximately'),
                        ('≤', 'less_equal'),
                        ('≥', 'greater_equal'),
                        ('≠', 'not_equal'),
                        ('∞', 'infinity'),
                        ('√', 'sqrt'),
                        ('²', 'squared'),
                        ('³', 'cubed'),
                        ('¼', 'quarter'),
                        ('½', 'half'),
                        ('¾', 'three_quarters'),
                        ('→', 'arrow'),
                        ('←', 'left_arrow'),
                        ('↑', 'up_arrow'),
                        ('↓', 'down_arrow'),
                        ('⚡', 'lightning'),
                        ('☀', 'sun'),
                        ('☁', 'cloud'),
                        ('☂', 'umbrella'),
                        ('★', 'star'),
                        ('♠', 'spades'),
                        ('♥', 'hearts'),
                        ('♦', 'diamonds'),
                        ('♣', 'clubs')
                    ]
                )
                # Если после обработки получилась пустая строка
                safe_name = safe_name if safe_name else 'sheet'
            else:
                # Fallback: базовая русская транслитерация (как было раньше)
                safe_name = self._basic_russian_transliterate(sheet_name)

        # Добавляем номер страницы в формате _01, _02, ..., _99
        return f"{safe_name}_{page_num:02d}"

    def _basic_russian_transliterate(self, text: str) -> str:
        """Базовая транслитерация русского текста (fallback метод)"""
        translit_dict = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
            'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }

        result = ''
        for char in text:
            result += translit_dict.get(char, char)

        # Очищаем небезопасные символы
        clean_name = re.sub(r'[^a-zA-Z0-9\-]', '_', result)
        clean_name = re.sub(r'_+', '_', clean_name)
        clean_name = clean_name.strip('_').lower()

        return clean_name if clean_name else 'sheet'

    def save_csv(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в CSV"""
        if 'csv' not in self.enabled_formats:
            return

        filename = f"{self.create_safe_filename(sheet_name, page_num)}.csv"
        filepath = os.path.join(self.output_dir, 'csv', filename)

        df.to_csv(filepath, index=False, sep=';', encoding='utf-8', quoting=1)
        print(f"💾 CSV сохранен: csv/{filename}")

        # Добавляем в статистику
        self.stats['files_created'].append({
            'format': 'csv',
            'filename': f"csv/{filename}",
            'size_bytes': os.path.getsize(filepath)
        })

    def save_json(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в JSON"""
        if 'json' not in self.enabled_formats:
            return

        filename = f"{self.create_safe_filename(sheet_name, page_num)}.json"
        filepath = os.path.join(self.output_dir, 'json', filename)

        data = df.to_dict('records')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"💾 JSON сохранен: json/{filename}")

        # Добавляем в статистику
        self.stats['files_created'].append({
            'format': 'json',
            'filename': f"json/{filename}",
            'size_bytes': os.path.getsize(filepath)
        })

    def save_txt(self, df: pd.DataFrame, df_original: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в TXT для удобного просмотра"""
        if 'txt' not in self.enabled_formats:
            return

        filename = f"{self.create_safe_filename(sheet_name, page_num)}.txt"
        filepath = os.path.join(self.output_dir, 'txt', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"📋 {sheet_name} - Страница {page_num}\n")
            f.write("=" * 60 + "\n\n")

            for index, row in df_original.iterrows():
                f.write(f"🔸 Запись #{index + 1}\n")
                f.write("-" * 30 + "\n")

                for column in df_original.columns:
                    value = row[column]
                    if pd.notna(value):
                        # Используем нативные переносы строк как есть
                        display_value = str(value)
                        f.write(f"📌 {column}: {display_value}\n")

                f.write("\n" + "=" * 60 + "\n\n")

        print(f"📄 TXT сохранен: txt/{filename}")

        # Добавляем в статистику
        self.stats['files_created'].append({
            'format': 'txt',
            'filename': f"txt/{filename}",
            'size_bytes': os.path.getsize(filepath)
        })

    def save_xlsx(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в Excel"""
        if 'xlsx' not in self.enabled_formats or not XLSX_AVAILABLE:
            return

        filename = f"{self.create_safe_filename(sheet_name, page_num)}.xlsx"
        filepath = os.path.join(self.output_dir, 'excel', filename)

        # Excel нативно поддерживает переносы строк, используем данные как есть
        df.to_excel(filepath, index=False, engine='openpyxl')
        print(f"📊 Excel сохранен: excel/{filename}")

        # Добавляем в статистику
        self.stats['files_created'].append({
            'format': 'xlsx',
            'filename': f"excel/{filename}",
            'size_bytes': os.path.getsize(filepath)
        })

    def save_markdown(self, df: pd.DataFrame, df_original: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в Markdown"""
        if 'md' not in self.enabled_formats:
            return

        filename = f"{self.create_safe_filename(sheet_name, page_num)}.md"
        filepath = os.path.join(self.output_dir, 'markdown', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 📋 {sheet_name} - Страница {page_num}\n\n")
            f.write(f"*Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

            # Создаем таблицу
            if not df_original.empty:
                # Заголовки
                headers = df_original.columns.tolist()
                f.write("| " + " | ".join(headers) + " |\n")
                f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")

                # Данные
                for _, row in df_original.iterrows():
                    row_data = []
                    for column in headers:
                        value = row[column] if pd.notna(row[column]) else ""
                        # Экранируем только специальные символы Markdown, переносы заменяем на <br>
                        value = str(value).replace('|', '\\|').replace('\n', '<br>')
                        row_data.append(value)
                    f.write("| " + " | ".join(row_data) + " |\n")

        print(f"📝 Markdown сохранен: markdown/{filename}")

        # Добавляем в статистику
        self.stats['files_created'].append({
            'format': 'md',
            'filename': f"markdown/{filename}",
            'size_bytes': os.path.getsize(filepath)
        })

    def save_html(self, df: pd.DataFrame, df_original: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в HTML"""
        if 'html' not in self.enabled_formats:
            return

        filename = f"{self.create_safe_filename(sheet_name, page_num)}.html"
        filepath = os.path.join(self.output_dir, 'html', filename)

        # Создаем HTML с красивым стилем
        html_content = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{sheet_name} - Страница {page_num}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
            vertical-align: top;
        }}
        th {{
            background-color: #007bff;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .meta {{
            color: #666;
            font-style: italic;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 {sheet_name} - Страница {page_num}</h1>
        <div class="meta">Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

        <table>
"""

        if not df_original.empty:
            # Заголовки
            html_content += "            <thead><tr>\n"
            for column in df_original.columns:
                html_content += f"                <th>{column}</th>\n"
            html_content += "            </tr></thead>\n            <tbody>\n"

            # Данные
            for _, row in df_original.iterrows():
                html_content += "                <tr>\n"
                for column in df_original.columns:
                    value = row[column] if pd.notna(row[column]) else ""
                    # Заменяем переносы на <br> для HTML
                    value = str(value).replace('\n', '<br>')
                    html_content += f"                    <td>{value}</td>\n"
                html_content += "                </tr>\n"

            html_content += "            </tbody>\n"

        html_content += """        </table>
    </div>
</body>
</html>"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"🌐 HTML сохранен: html/{filename}")

        # Добавляем в статистику
        self.stats['files_created'].append({
            'format': 'html',
            'filename': f"html/{filename}",
            'size_bytes': os.path.getsize(filepath)
        })

    def save_yaml(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в YAML"""
        if 'yaml' not in self.enabled_formats:
            return

        filename = f"{self.create_safe_filename(sheet_name, page_num)}.yml"
        filepath = os.path.join(self.output_dir, 'yaml', filename)

        data = {
            'sheet_info': {
                'name': sheet_name,
                'page': page_num,
                'created': datetime.now().isoformat(),
                'rows_count': len(df)
            },
            'data': df.to_dict('records')
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)

        print(f"⚙️ YAML сохранен: yaml/{filename}")

        # Добавляем в статистику
        self.stats['files_created'].append({
            'format': 'yaml',
            'filename': f"yaml/{filename}",
            'size_bytes': os.path.getsize(filepath)
        })

    def save_all_formats(self, df_processed: pd.DataFrame, df_original: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет данные во всех выбранных форматах"""
        self.save_csv(df_processed, sheet_name, page_num)
        self.save_json(df_processed, sheet_name, page_num)
        self.save_txt(df_processed, df_original, sheet_name, page_num)
        self.save_xlsx(df_processed, sheet_name, page_num)
        self.save_markdown(df_processed, df_original, sheet_name, page_num)
        self.save_html(df_processed, df_original, sheet_name, page_num)
        self.save_yaml(df_processed, sheet_name, page_num)

    def save_stats_report(self):
        """Сохраняет красивый отчет о проведенной конвертации"""
        self.stats['end_time'] = datetime.now()
        duration = self.stats['end_time'] - self.stats['start_time']

        # Группируем файлы по форматам
        files_by_format = {}
        total_size = 0

        for file_info in self.stats['files_created']:
            format_name = file_info['format']
            if format_name not in files_by_format:
                files_by_format[format_name] = {
                    'count': 0,
                    'total_size': 0,
                    'files': []
                }

            files_by_format[format_name]['count'] += 1
            files_by_format[format_name]['total_size'] += file_info['size_bytes']
            files_by_format[format_name]['files'].append(file_info['filename'])
            total_size += file_info['size_bytes']

        # Функция для форматирования размера
        def format_size(size_bytes):
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.1f} MB"

        # Создаем подробный отчет
        report = {
            "🎉 ОТЧЕТ О КОНВЕРТАЦИИ": {
                "📊 Общая статистика": {
                    "Дата и время": self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    "Время выполнения": str(duration).split('.')[0],
                    "Всего листов найдено": self.stats['total_sheets'],
                    "Успешно обработано": self.stats['processed_sheets'],
                    "Пропущено": self.stats['skipped_sheets'],
                    "Использовано из кеша": self.stats['cached_sheets'],
                    "Процент успеха": f"{(self.stats['processed_sheets'] / max(self.stats['total_sheets'], 1) * 100):.1f}%"
                },

                "⚙️ Настройки конвертации": {
                    "Форматы экспорта": self.stats['formats_used'],
                    "Транслитерация названий": "✅ Включена" if self.stats['transliteration_enabled'] else "❌ Отключена",
                    "Кеширование": "✅ Включено" if self.stats['caching_enabled'] else "❌ Отключено",
                    "Batch запросы использованы": self.stats['batch_requests_used'],
                    "Всего форматов": len(self.stats['formats_used'])
                },

                "📁 Результаты по форматам": {},

                "📋 Детали по листам": [],

                "📂 Созданные файлы": files_by_format,

                "💾 Размеры файлов": {
                    "Общий размер": format_size(total_size),
                    "По форматам": {
                        format_name: format_size(info['total_size'])
                        for format_name, info in files_by_format.items()
                    }
                },

                "📈 Производительность": {
                    "Файлов создано": len(self.stats['files_created']),
                    "Скорость обработки": f"{self.stats['processed_sheets'] / max(duration.total_seconds(), 1):.2f} листов/сек",
                    "Средний размер файла": format_size(total_size / max(len(self.stats['files_created']), 1)),
                    "API запросов сэкономлено": max(0, self.stats['total_sheets'] - self.stats['batch_requests_used'] - 1)
                }
            }
        }

        # Добавляем результаты по форматам
        for format_name, info in files_by_format.items():
            format_display = self.available_formats.get(format_name, {}).get('name', format_name)
            report["🎉 ОТЧЕТ О КОНВЕРТАЦИИ"]["📁 Результаты по форматам"][format_display] = {
                "Файлов создано": info['count'],
                "Общий размер": format_size(info['total_size']),
                "Средний размер": format_size(info['total_size'] / max(info['count'], 1))
            }

        # Добавляем детали по листам
        for sheet_detail in self.stats['sheets_details']:
            report["🎉 ОТЧЕТ О КОНВЕРТАЦИИ"]["📋 Детали по листам"].append({
                "Название": sheet_detail['name'],
                "Статус": "✅ Обработан" if sheet_detail['processed'] else "❌ Пропущен",
                "Строк данных": sheet_detail.get('rows', 0),
                "Колонок": sheet_detail.get('columns', 0),
                "Из кеша": "✅" if sheet_detail.get('from_cache', False) else "❌",
                "Причина пропуска": sheet_detail.get('skip_reason', '')
            })

        # Сохраняем отчет
        stats_filepath = os.path.join(self.output_dir, 'stats.json')
        with open(stats_filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=4, default=str)

        print(f"\n📊 Отчет сохранен: stats.json")

        # Выводим краткую сводку
        print("\n" + "=" * 60)
        print("📊 КРАТКАЯ СВОДКА")
        print("=" * 60)
        print(f"⏱️  Время выполнения: {str(duration).split('.')[0]}")
        print(f"📄 Обработано листов: {self.stats['processed_sheets']}/{self.stats['total_sheets']}")
        print(f"📂 Из кеша: {self.stats['cached_sheets']}")
        print(f"🚀 Batch запросов: {self.stats['batch_requests_used']}")
        print(f"📁 Создано файлов: {len(self.stats['files_created'])}")
        print(f"💾 Общий размер: {format_size(total_size)}")
        print(f"🎯 Форматы: {', '.join(self.stats['formats_used'])}")

        return report

    def convert_all_sheets(self, url: str) -> bool:
        """
        🚀 ОБНОВЛЕННЫЙ ГЛАВНЫЙ МЕТОД: Конвертирует все страницы таблицы с batch загрузкой и кешированием
        """
        try:
            # Создаем выходные директории
            self.create_output_directories()

            # Извлекаем ID таблицы
            sheet_id = self.extract_sheet_id(url)
            print(f"🔍 ID таблицы: {sheet_id}")

            # Получаем информацию о всех страницах через API
            sheets_info = self.get_all_sheets_info(sheet_id)

            if not sheets_info:
                print("❌ Не найдено ни одной страницы для обработки")
                return False

            # Статистика обработки
            processed_count = 0
            skipped_count = 0
            cached_count = 0

            print("\n" + "=" * 50)
            print("🚀 Начинаем batch загрузку и обработку")
            print("=" * 50)

            # 🎯 ГЛАВНОЕ ИЗМЕНЕНИЕ: загружаем ВСЕ листы одним batch запросом
            sheets_data = self.load_all_sheets_batch(sheet_id, sheets_info)

            print("\n" + "=" * 50)
            print("🔄 Обрабатываем загруженные данные")
            print("=" * 50)

            # Обрабатываем каждый лист (данные уже загружены)
            for page_num, sheet_info in enumerate(sheets_info, 1):
                sheet_name = sheet_info['name']

                print(f"\n📄 Обрабатываем лист {page_num}: '{sheet_name}'")
                print("-" * 30)

                # Получаем предзагруженные данные
                sheet_result = sheets_data.get(sheet_name, (pd.DataFrame(), False, ""))
                df_original, load_success, raw_data = sheet_result

                if not load_success or df_original.empty:
                    print(f"⏭️ [{sheet_name}] Пропускаем - нет данных")
                    skipped_count += 1
                    # Добавляем в статистику
                    self.stats['sheets_details'].append({
                        'name': sheet_name,
                        'processed': False,
                        'skip_reason': 'Нет данных',
                        'from_cache': False
                    })
                    continue

                # 📂 КЕШИРОВАНИЕ: проверяем, изменился ли лист
                if not self._is_sheet_changed(sheet_id, sheet_name, raw_data):
                    print(f"📋 [{sheet_name}] Используем кешированную версию")
                    cached_count += 1
                    # Добавляем в статистику
                    self.stats['sheets_details'].append({
                        'name': sheet_name,
                        'processed': True,
                        'rows': len(df_original),
                        'columns': len(df_original.columns),
                        'from_cache': True
                    })
                    continue

                # Обрабатываем текстовые поля
                df_processed = self.process_text_fields(df_original)

                # Сохраняем во всех выбранных форматах
                self.save_all_formats(df_processed, df_processed, sheet_name, page_num)

                processed_count += 1
                print(f"✅ [{sheet_name}] Обработка завершена")

                # Добавляем в статистику
                self.stats['sheets_details'].append({
                    'name': sheet_name,
                    'processed': True,
                    'rows': len(df_original),
                    'columns': len(df_original.columns),
                    'from_cache': False
                })

            # Обновляем итоговую статистику
            self.stats['total_sheets'] = len(sheets_info)
            self.stats['processed_sheets'] = processed_count
            self.stats['skipped_sheets'] = skipped_count
            self.stats['cached_sheets'] = cached_count

            # Сохраняем кеш
            self._save_cache()

            # Сохраняем отчет
            try:
                self.save_stats_report()
            except Exception as e:
                print(f"⚠️ Ошибка создания отчета: {e}")
                # Продолжаем без отчета

            # Итоговый отчет
            print("\n" + "=" * 50)
            print("📊 ИТОГОВЫЙ ОТЧЕТ")
            print("=" * 50)
            print(f"✅ Успешно обработано: {processed_count} страниц")
            print(f"📂 Из кеша: {cached_count} страниц")
            print(f"⏭️ Пропущено: {skipped_count} страниц")
            print(f"📁 Файлы сохранены в: {self.output_dir}/")

            if processed_count > 0 or cached_count > 0:
                print("\n🎉 Конвертация завершена успешно!")
                if cached_count > 0:
                    print(f"⚡ Ускорение благодаря кешу: {cached_count} листов пропущено")
                return True
            else:
                print("\n💥 Ни одна страница не была успешно обработана")
                return False

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            print("Детали ошибки:")
            traceback.print_exc()
            return False


def select_formats_interactive():
    """Интерактивный выбор форматов"""
    available_formats = {
        'csv': 'CSV файлы (для парсеров)',
        'json': 'JSON файлы (структурированные данные)',
        'txt': 'TXT файлы (для просмотра)',
        'xlsx': 'Excel файлы (редактирование)',
        'md': 'Markdown документы (документация)',
        'html': 'HTML страницы (браузер)',
        'yaml': 'YAML конфигурации (DevOps)'
    }

    print("\n📋 Выберите форматы для сохранения:")
    format_keys = list(available_formats.keys())

    for i, (key, desc) in enumerate(available_formats.items(), 1):
        print(f"  {i}. {desc}")

    print("\n📝 Введите номера через запятую (например: 1,2,3) или 'all' для всех:")
    choice = input("Выбор: ").strip()

    selected_formats = []

    if choice.lower() == 'all':
        selected_formats = list(available_formats.keys())
        print("✅ Выбраны все форматы")
    else:
        try:
            indices = [int(x.strip()) for x in choice.split(',')]
            for idx in indices:
                if 1 <= idx <= len(format_keys):
                    selected_formats.append(format_keys[idx - 1])
                else:
                    print(f"⚠️ Неверный номер: {idx}")

            if selected_formats:
                format_names = [available_formats[f] for f in selected_formats]
                print(f"✅ Выбраны форматы: {', '.join(format_names)}")
            else:
                print("⚠️ Не выбрано ни одного формата, используем базовые")
                selected_formats = ['csv', 'json', 'txt']

        except ValueError:
            print("⚠️ Неверный ввод, используем базовые форматы")
            selected_formats = ['csv', 'json', 'txt']

    # Выбор транслитерации
    print("\n🌍 Универсальная транслитерация названий файлов?")
    print("  Поддерживает: русский, китайский, японский, арабский, корейский и др.")
    print("  (Визитки → vizitki_01, 访问卡 → fang_wen_ka_01, 名刺 → ming_ci_01)")
    transliterate_choice = input("Включить транслитерацию? (y/n): ").strip().lower()
    transliterate = transliterate_choice in ['y', 'yes', 'д', 'да', '1']

    if transliterate:
        if SLUGIFY_AVAILABLE:
            print("✅ Универсальная транслитерация включена (python-slugify)")
        else:
            print("✅ Базовая транслитерация включена (только русский)")
    else:
        print("✅ Оригинальные названия файлов (с базовой очисткой)")

    # Выбор кеширования
    print("\n📂 Включить кеширование для ускорения повторных запросов?")
    print("  (будет сохранять хеши данных и пропускать неизмененные листы)")
    cache_choice = input("Включить кеш? (y/n): ").strip().lower()
    enable_cache = cache_choice in ['y', 'yes', 'д', 'да', '1']

    if enable_cache:
        print("✅ Кеширование включено")
    else:
        print("✅ Кеширование отключено")

    return selected_formats, transliterate, enable_cache


def main():
    """Точка входа в программу"""
    print("📋 Universal Google Sheets to Multiple Formats Converter")
    print("🚀 ОПТИМИЗИРОВАННАЯ ВЕРСИЯ с batch запросами и кешированием")
    print("=" * 70)

    # Проверяем есть ли аргументы командной строки
    if len(sys.argv) >= 2:
        # CLI режим
        url = sys.argv[1]
        print("🚀 Запуск конвертера (CLI режим)")
        print(f"📋 URL: {url}")
        print("=" * 70)

        # В CLI режиме используем все форматы с транслитерацией и кешированием
        converter = UniversalSheetsConverter(
            formats=['csv', 'json', 'txt', 'xlsx', 'md', 'html', 'yaml'],
            transliterate=True,
            enable_caching=True
        )

        success = converter.convert_all_sheets(url)

        if success:
            print("\n🎉 Программа завершена успешно!")
        else:
            print("\n💥 Программа завершена с ошибками.")
            sys.exit(1)
    else:
        # Интерактивный режим
        print("🔧 Интерактивный режим")
        print(f"\n🧪 Тестовая таблица: {URL_TEST}")
        print("-" * 60)

        while True:
            try:
                print("\n1. Ввести URL таблицы (с выбором настроек)")
                print("2. Использовать тестовую таблицу (все форматы)")
                print("3. Выход")

                choice = input("\n📝 Выберите опцию (1-3): ").strip()

                if choice == "1":
                    url = input("\n📝 Введите URL Google Таблицы: ").strip()

                    if not url:
                        print("⚠️ Пустая строка. Введите корректный URL.")
                        continue

                    if 'docs.google.com/spreadsheets' not in url:
                        print("⚠️ Некорректный URL. Должен содержать 'docs.google.com/spreadsheets'")
                        continue

                    # Интерактивный выбор форматов и настроек
                    formats, transliterate, enable_cache = select_formats_interactive()
                    converter = UniversalSheetsConverter(
                        formats=formats,
                        transliterate=transliterate,
                        enable_caching=enable_cache
                    )

                elif choice == "2":
                    url = URL_TEST
                    print(f"📝 Используем тестовую таблицу: {url}")

                    # Все форматы с оптимизациями для тестирования
                    converter = UniversalSheetsConverter(
                        formats=['csv', 'json', 'txt', 'xlsx', 'md', 'html', 'yaml'],
                        transliterate=True,
                        enable_caching=True
                    )

                elif choice in ["3", "exit", "quit", "выход"]:
                    print("👋 До свидания!")
                    break

                else:
                    print("⚠️ Неверный выбор. Введите 1, 2 или 3.")
                    continue

                print("\n🚀 Запуск конвертера (интерактивный режим)")
                print(f"📋 URL: {url}")
                print("=" * 70)

                success = converter.convert_all_sheets(url)

                if success:
                    print("\n🎉 Конвертация завершена успешно!")
                else:
                    print("\n💥 Конвертация завершена с ошибками.")

                # Предлагаем обработать еще одну таблицу
                while True:
                    continue_choice = input("\n❓ Хотите обработать еще одну таблицу? (y/n): ").strip().lower()
                    if continue_choice in ['y', 'yes', 'д', 'да']:
                        break
                    elif continue_choice in ['n', 'no', 'н', 'нет']:
                        print("👋 До свидания!")
                        return
                    else:
                        print("⚠️ Введите 'y' для продолжения или 'n' для выхода")

            except KeyboardInterrupt:
                print("\n\n👋 Программа прервана пользователем. До свидания!")
                break
            except Exception as e:
                print(f"\n❌ Неожиданная ошибка: {e}")
                print("Попробуйте еще раз или введите '3' для выхода.")


if __name__ == "__main__":
    main()