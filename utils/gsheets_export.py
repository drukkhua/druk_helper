#!/usr/bin/env python3
"""
Universal Google Sheets to Multiple Formats Converter
Универсальный конвертер Google Таблиц в различные форматы
"""

import re

import json
import os
import pandas as pd
import requests
import sys
import yaml
from datetime import datetime
from typing import Any, Dict, List, Tuple

from config import GOOGLE_SHEETS_API_KEY

# Опциональные импорты
try:
    import openpyxl

    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

# Константы
URL_TEST = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit?usp=sharing"
FILE_PATH = "../converted-data"


class UniversalSheetsConverter:
    def __init__(self, formats=["csv", "json", "txt"], transliterate=True):
        self.enabled_formats = set(formats)
        self.transliterate_names = transliterate
        self.output_dir = FILE_PATH
        self.api_key = GOOGLE_SHEETS_API_KEY

        # Доступные форматы (убрали PDF)
        self.available_formats = {
            "csv": {"name": "CSV файлы (для парсеров)", "ext": "csv", "folder": "csv"},
            "json": {
                "name": "JSON файлы (структурированные данные)",
                "ext": "json",
                "folder": "json",
            },
            "txt": {"name": "TXT файлы (для просмотра)", "ext": "txt", "folder": "txt"},
            "xlsx": {
                "name": "Excel файлы (редактирование)",
                "ext": "xlsx",
                "folder": "excel",
            },
            "md": {
                "name": "Markdown документы (документация)",
                "ext": "md",
                "folder": "markdown",
            },
            "html": {
                "name": "HTML страницы (браузер)",
                "ext": "html",
                "folder": "html",
            },
            "yaml": {
                "name": "YAML конфигурации (DevOps)",
                "ext": "yml",
                "folder": "yaml",
            },
        }

        # Статистика для отчета
        self.stats = {
            "start_time": datetime.now(),
            "end_time": None,
            "total_sheets": 0,
            "processed_sheets": 0,
            "skipped_sheets": 0,
            "formats_used": list(self.enabled_formats),
            "transliteration_enabled": self.transliterate_names,
            "sheets_details": [],
            "files_created": [],
        }

        # Проверяем доступность форматов
        self._check_format_availability()

    def _check_format_availability(self):
        """Проверяет доступность форматов и предупреждает о недостающих библиотеках"""
        if "xlsx" in self.enabled_formats and not XLSX_AVAILABLE:
            print(
                "⚠️ Для Excel формата нужна библиотека openpyxl: pip install openpyxl"
            )
            self.enabled_formats.discard("xlsx")

    def create_output_directories(self):
        """Создает выходные директории для всех форматов"""
        for format_key in self.enabled_formats:
            if format_key in self.available_formats:
                folder_path = os.path.join(
                    self.output_dir, self.available_formats[format_key]["folder"]
                )
                os.makedirs(folder_path, exist_ok=True)

        print(f"📁 Рабочая директория: {self.output_dir}/")
        print(f"📋 Активные форматы: {', '.join(self.enabled_formats)}")

    def extract_sheet_id(self, url: str) -> str:
        """Извлекает ID таблицы из URL"""
        pattern = r"/spreadsheets/d/([a-zA-Z0-9-_]+)"
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
                params["key"] = self.api_key
                print(f"🔑 Используем API key: {self.api_key[:20]}...")

            headers = {"User-Agent": "UniversalSheetsConverter/1.0"}
            response = requests.get(api_url, params=params, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                sheets_info = []

                sheets = data.get("sheets", [])
                for sheet in sheets:
                    sheet_properties = sheet.get("properties", {})
                    sheet_id_num = sheet_properties.get("sheetId", 0)
                    sheet_title = sheet_properties.get("title", f"Sheet{sheet_id_num}")

                    sheets_info.append({"gid": str(sheet_id_num), "name": sheet_title})

                if sheets_info:
                    print(f"📄 Найдено страниц через API: {len(sheets_info)}")
                    for i, sheet in enumerate(sheets_info, 1):
                        print(f"   {i}. '{sheet['name']}' (gid: {sheet['gid']})")
                    return sheets_info
                else:
                    print("⚠️ API вернул пустой список листов")
                    return [{"gid": "0", "name": "Sheet1"}]

            elif response.status_code == 403:
                print(f"❌ Ошибка доступа (HTTP 403)")
                print(
                    "💡 Проверьте правильность API ключа и настройки доступа к таблице"
                )
                return [{"gid": "0", "name": "Sheet1"}]

            elif response.status_code == 404:
                print(f"❌ Таблица не найдена (HTTP 404)")
                print("💡 Проверьте правильность ID таблицы")
                return [{"gid": "0", "name": "Sheet1"}]

            else:
                print(f"❌ API вернул ошибку HTTP {response.status_code}")
                return [{"gid": "0", "name": "Sheet1"}]

        except requests.RequestException as e:
            print(f"❌ Ошибка сети при обращении к API: {e}")
            return [{"gid": "0", "name": "Sheet1"}]

        except Exception as e:
            print(f"❌ Неожиданная ошибка при работе с API: {e}")
            return [{"gid": "0", "name": "Sheet1"}]

    def get_csv_url(self, sheet_id: str, gid: str) -> str:
        """Формирует URL для экспорта страницы в CSV"""
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    def load_sheet_data(
        self, sheet_id: str, gid: str, sheet_name: str
    ) -> Tuple[pd.DataFrame, bool]:
        """Загружает данные одной страницы"""
        try:
            csv_url = self.get_csv_url(sheet_id, gid)
            print(f"📥 Загружаем страницу: {sheet_name}")

            df = pd.read_csv(csv_url)

            # Удаляем полностью пустые строки
            df = df.dropna(how="all")

            # Показываем структуру данных
            print(
                f"📊 [{sheet_name}] Загружено {len(df)} строк, {len(df.columns)} колонок"
            )

            return df, True

        except Exception as e:
            print(f"❌ [{sheet_name}] Ошибка загрузки: {e}")
            return pd.DataFrame(), False

    def detect_text_columns(self, df: pd.DataFrame) -> List[str]:
        """Автоматически определяет текстовые колонки для обработки переносов строк"""
        text_columns = []

        for column in df.columns:
            # Проверяем несколько строк на наличие переносов
            sample_data = df[column].dropna().astype(str).head(10)
            has_newlines = any("\n" in str(value) for value in sample_data)

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
                    df_processed[column] = (
                        df_processed[column]
                        .astype(str)
                        .str.replace("\r", "", regex=False)
                    )

        return df_processed

    def transliterate_russian(self, text: str) -> str:
        """Транслитерирует русский текст в латиницу"""
        if not self.transliterate_names:
            return text

        translit_dict = {
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "д": "d",
            "е": "e",
            "ё": "yo",
            "ж": "zh",
            "з": "z",
            "и": "i",
            "й": "y",
            "к": "k",
            "л": "l",
            "м": "m",
            "н": "n",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "у": "u",
            "ф": "f",
            "х": "h",
            "ц": "ts",
            "ч": "ch",
            "ш": "sh",
            "щ": "sch",
            "ъ": "",
            "ы": "y",
            "ь": "",
            "э": "e",
            "ю": "yu",
            "я": "ya",
            "А": "A",
            "Б": "B",
            "В": "V",
            "Г": "G",
            "Д": "D",
            "Е": "E",
            "Ё": "Yo",
            "Ж": "Zh",
            "З": "Z",
            "И": "I",
            "Й": "Y",
            "К": "K",
            "Л": "L",
            "М": "M",
            "Н": "N",
            "О": "O",
            "П": "P",
            "Р": "R",
            "С": "S",
            "Т": "T",
            "У": "U",
            "Ф": "F",
            "Х": "H",
            "Ц": "Ts",
            "Ч": "Ch",
            "Ш": "Sh",
            "Щ": "Sch",
            "Ъ": "",
            "Ы": "Y",
            "Ь": "",
            "Э": "E",
            "Ю": "Yu",
            "Я": "Ya",
        }

        result = ""
        for char in text:
            result += translit_dict.get(char, char)

        return result

    def clean_filename(self, sheet_name: str) -> str:
        """Очищает имя листа для использования в имени файла"""
        # Транслитерируем если включено
        clean_name = self.transliterate_russian(sheet_name)

        # Заменяем небезопасные символы на подчеркивания
        clean_name = re.sub(r"[^a-zA-Z0-9\-]", "_", clean_name)
        clean_name = re.sub(r"_+", "_", clean_name)
        clean_name = clean_name.strip("_").lower()

        return clean_name if clean_name else "sheet"

    def save_csv(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в CSV"""
        if "csv" not in self.enabled_formats:
            return

        clean_name = self.clean_filename(sheet_name)
        filename = f"{clean_name}_page_{page_num:02d}.csv"
        filepath = os.path.join(self.output_dir, "csv", filename)

        df.to_csv(filepath, index=False, sep=";", encoding="utf-8", quoting=1)
        print(f"💾 CSV сохранен: csv/{filename}")

        # Добавляем в статистику
        self.stats["files_created"].append(
            {
                "format": "csv",
                "filename": f"csv/{filename}",
                "size_bytes": os.path.getsize(filepath),
            }
        )

    def save_json(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в JSON"""
        if "json" not in self.enabled_formats:
            return

        clean_name = self.clean_filename(sheet_name)
        filename = f"{clean_name}_page_{page_num:02d}.json"
        filepath = os.path.join(self.output_dir, "json", filename)

        data = df.to_dict("records")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"💾 JSON сохранен: json/{filename}")

        # Добавляем в статистику
        self.stats["files_created"].append(
            {
                "format": "json",
                "filename": f"json/{filename}",
                "size_bytes": os.path.getsize(filepath),
            }
        )

    def save_txt(
        self,
        df: pd.DataFrame,
        df_original: pd.DataFrame,
        sheet_name: str,
        page_num: int,
    ):
        """Сохраняет DataFrame в TXT для удобного просмотра"""
        if "txt" not in self.enabled_formats:
            return

        clean_name = self.clean_filename(sheet_name)
        filename = f"{clean_name}_page_{page_num:02d}.txt"
        filepath = os.path.join(self.output_dir, "txt", filename)

        with open(filepath, "w", encoding="utf-8") as f:
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
        self.stats["files_created"].append(
            {
                "format": "txt",
                "filename": f"txt/{filename}",
                "size_bytes": os.path.getsize(filepath),
            }
        )

    def save_xlsx(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в Excel"""
        if "xlsx" not in self.enabled_formats or not XLSX_AVAILABLE:
            return

        clean_name = self.clean_filename(sheet_name)
        filename = f"{clean_name}_page_{page_num:02d}.xlsx"
        filepath = os.path.join(self.output_dir, "excel", filename)

        # Excel нативно поддерживает переносы строк, используем данные как есть
        df.to_excel(filepath, index=False, engine="openpyxl")
        print(f"📊 Excel сохранен: excel/{filename}")

        # Добавляем в статистику
        self.stats["files_created"].append(
            {
                "format": "xlsx",
                "filename": f"excel/{filename}",
                "size_bytes": os.path.getsize(filepath),
            }
        )

    def save_markdown(
        self,
        df: pd.DataFrame,
        df_original: pd.DataFrame,
        sheet_name: str,
        page_num: int,
    ):
        """Сохраняет DataFrame в Markdown"""
        if "md" not in self.enabled_formats:
            return

        clean_name = self.clean_filename(sheet_name)
        filename = f"{clean_name}_page_{page_num:02d}.md"
        filepath = os.path.join(self.output_dir, "markdown", filename)

        with open(filepath, "w", encoding="utf-8") as f:
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
                        value = str(value).replace("|", "\\|").replace("\n", "<br>")
                        row_data.append(value)
                    f.write("| " + " | ".join(row_data) + " |\n")

        print(f"📝 Markdown сохранен: markdown/{filename}")

        # Добавляем в статистику
        self.stats["files_created"].append(
            {
                "format": "md",
                "filename": f"markdown/{filename}",
                "size_bytes": os.path.getsize(filepath),
            }
        )

    def save_html(
        self,
        df: pd.DataFrame,
        df_original: pd.DataFrame,
        sheet_name: str,
        page_num: int,
    ):
        """Сохраняет DataFrame в HTML"""
        if "html" not in self.enabled_formats:
            return

        clean_name = self.clean_filename(sheet_name)
        filename = f"{clean_name}_page_{page_num:02d}.html"
        filepath = os.path.join(self.output_dir, "html", filename)

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
                    value = str(value).replace("\n", "<br>")
                    html_content += f"                    <td>{value}</td>\n"
                html_content += "                </tr>\n"

            html_content += "            </tbody>\n"

        html_content += """        </table>
    </div>
</body>
</html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"🌐 HTML сохранен: html/{filename}")

        # Добавляем в статистику
        self.stats["files_created"].append(
            {
                "format": "html",
                "filename": f"html/{filename}",
                "size_bytes": os.path.getsize(filepath),
            }
        )

    def save_yaml(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в YAML"""
        if "yaml" not in self.enabled_formats:
            return

        clean_name = self.clean_filename(sheet_name)
        filename = f"{clean_name}_page_{page_num:02d}.yml"
        filepath = os.path.join(self.output_dir, "yaml", filename)

        data = {
            "sheet_info": {
                "name": sheet_name,
                "page": page_num,
                "created": datetime.now().isoformat(),
                "rows_count": len(df),
            },
            "data": df.to_dict("records"),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)

        print(f"⚙️ YAML сохранен: yaml/{filename}")

        # Добавляем в статистику
        self.stats["files_created"].append(
            {
                "format": "yaml",
                "filename": f"yaml/{filename}",
                "size_bytes": os.path.getsize(filepath),
            }
        )

    def save_all_formats(
        self,
        df_processed: pd.DataFrame,
        df_original: pd.DataFrame,
        sheet_name: str,
        page_num: int,
    ):
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
        self.stats["end_time"] = datetime.now()
        duration = self.stats["end_time"] - self.stats["start_time"]

        # Группируем файлы по форматам
        files_by_format = {}
        total_size = 0

        for file_info in self.stats["files_created"]:
            format_name = file_info["format"]
            if format_name not in files_by_format:
                files_by_format[format_name] = {
                    "count": 0,
                    "total_size": 0,
                    "files": [],
                }

            files_by_format[format_name]["count"] += 1
            files_by_format[format_name]["total_size"] += file_info["size_bytes"]
            files_by_format[format_name]["files"].append(file_info["filename"])
            total_size += file_info["size_bytes"]

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
                    "Дата и время": self.stats["start_time"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "Время выполнения": str(duration).split(".")[0],
                    "Всего листов найдено": self.stats["total_sheets"],
                    "Успешно обработано": self.stats["processed_sheets"],
                    "Пропущено": self.stats["skipped_sheets"],
                    "Процент успеха": f"{(self.stats['processed_sheets'] / max(self.stats['total_sheets'], 1) * 100):.1f}%",
                },
                "⚙️ Настройки конвертации": {
                    "Форматы экспорта": self.stats["formats_used"],
                    "Транслитерация названий": (
                        "✅ Включена"
                        if self.stats["transliteration_enabled"]
                        else "❌ Отключена"
                    ),
                    "Всего форматов": len(self.stats["formats_used"]),
                },
                "📁 Результаты по форматам": {},
                "📋 Детали по листам": [],
                "📂 Созданные файлы": files_by_format,
                "💾 Размеры файлов": {
                    "Общий размер": format_size(total_size),
                    "По форматам": {
                        format_name: format_size(info["total_size"])
                        for format_name, info in files_by_format.items()
                    },
                },
                "📈 Производительность": {
                    "Файлов создано": len(self.stats["files_created"]),
                    "Скорость обработки": f"{self.stats['processed_sheets'] / max(duration.total_seconds(), 1):.2f} листов/сек",
                    "Средний размер файла": format_size(
                        total_size / max(len(self.stats["files_created"]), 1)
                    ),
                },
            }
        }

        # Добавляем результаты по форматам
        for format_name, info in files_by_format.items():
            format_display = self.available_formats.get(format_name, {}).get(
                "name", format_name
            )
            report["🎉 ОТЧЕТ О КОНВЕРТАЦИИ"]["📁 Результаты по форматам"][
                format_display
            ] = {
                "Файлов создано": info["count"],
                "Общий размер": format_size(info["total_size"]),
                "Средний размер": format_size(
                    info["total_size"] / max(info["count"], 1)
                ),
            }

        # Добавляем детали по листам
        for sheet_detail in self.stats["sheets_details"]:
            report["🎉 ОТЧЕТ О КОНВЕРТАЦИИ"]["📋 Детали по листам"].append(
                {
                    "Название": sheet_detail["name"],
                    "Статус": (
                        "✅ Обработан" if sheet_detail["processed"] else "❌ Пропущен"
                    ),
                    "Строк данных": sheet_detail.get("rows", 0),
                    "Колонок": sheet_detail.get("columns", 0),
                    "Причина пропуска": sheet_detail.get("skip_reason", ""),
                }
            )

        # Сохраняем отчет
        stats_filepath = os.path.join(self.output_dir, "stats.json")
        with open(stats_filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=4, default=str)

        print(f"\n📊 Отчет сохранен: stats.json")

        # Выводим краткую сводку
        print("\n" + "=" * 60)
        print("📊 КРАТКАЯ СВОДКА")
        print("=" * 60)
        print(f"⏱️  Время выполнения: {str(duration).split('.')[0]}")
        print(
            f"📄 Обработано листов: {self.stats['processed_sheets']}/{self.stats['total_sheets']}"
        )
        print(f"📁 Создано файлов: {len(self.stats['files_created'])}")
        print(f"💾 Общий размер: {format_size(total_size)}")
        print(f"🎯 Форматы: {', '.join(self.stats['formats_used'])}")

        return report

    def convert_all_sheets(self, url: str) -> bool:
        """Конвертирует все страницы таблицы"""
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

            print("\n" + "=" * 50)
            print("🚀 Начинаем обработку страниц")
            print("=" * 50)

            # Обрабатываем каждую страницу
            for page_num, sheet_info in enumerate(sheets_info, 1):
                gid = sheet_info["gid"]
                sheet_name = sheet_info["name"]

                print(f"\n📄 Обрабатываем страницу {page_num}: '{sheet_name}'")
                print("-" * 30)

                # Загружаем данные страницы
                df_original, load_success = self.load_sheet_data(
                    sheet_id, gid, sheet_name
                )

                if not load_success or df_original.empty:
                    print(f"⏭️ [{sheet_name}] Пропускаем - нет данных")
                    skipped_count += 1
                    # Добавляем в статистику
                    self.stats["sheets_details"].append(
                        {
                            "name": sheet_name,
                            "processed": False,
                            "skip_reason": "Нет данных",
                        }
                    )
                    continue

                # Обрабатываем текстовые поля (теперь только очистка, без замены переносов)
                df_processed = self.process_text_fields(df_original)

                # Сохраняем во всех выбранных форматах (используем одни и те же данные)
                self.save_all_formats(df_processed, df_processed, sheet_name, page_num)

                processed_count += 1
                print(f"✅ [{sheet_name}] Обработка завершена")

                # Добавляем в статистику
                self.stats["sheets_details"].append(
                    {
                        "name": sheet_name,
                        "processed": True,
                        "rows": len(df_original),
                        "columns": len(df_original.columns),
                    }
                )

            # Обновляем итоговую статистику
            self.stats["total_sheets"] = len(sheets_info)
            self.stats["processed_sheets"] = processed_count
            self.stats["skipped_sheets"] = skipped_count

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
            print(f"⏭️ Пропущено: {skipped_count} страниц")
            print(f"📁 Файлы сохранены в: {self.output_dir}/")

            if processed_count > 0:
                print("\n🎉 Конвертация завершена успешно!")
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
        "csv": "CSV файлы (для парсеров)",
        "json": "JSON файлы (структурированные данные)",
        "txt": "TXT файлы (для просмотра)",
        "xlsx": "Excel файлы (редактирование)",
        "md": "Markdown документы (документация)",
        "html": "HTML страницы (браузер)",
        "yaml": "YAML конфигурации (DevOps)",
    }

    print("\n📋 Выберите форматы для сохранения:")
    format_keys = list(available_formats.keys())

    for i, (key, desc) in enumerate(available_formats.items(), 1):
        print(f"  {i}. {desc}")

    print("\n📝 Введите номера через запятую (например: 1,2,3) или 'all' для всех:")
    choice = input("Выбор: ").strip()

    selected_formats = []

    if choice.lower() == "all":
        selected_formats = list(available_formats.keys())
        print("✅ Выбраны все форматы")
    else:
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
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
                selected_formats = ["csv", "json", "txt"]

        except ValueError:
            print("⚠️ Неверный ввод, используем базовые форматы")
            selected_formats = ["csv", "json", "txt"]

    # Выбор транслитерации
    print("\n🔤 Транслитерация русских названий файлов в латиницу?")
    print("  (визитки → vizitki)")
    transliterate_choice = input("Транслитерировать? (y/n): ").strip().lower()
    transliterate = transliterate_choice in ["y", "yes", "д", "да", "1"]

    if transliterate:
        print("✅ Транслитерация включена")
    else:
        print("✅ Оригинальные названия файлов")

    return selected_formats, transliterate


def main():
    """Точка входа в программу"""
    print("📋 Universal Google Sheets to Multiple Formats Converter")
    print("=" * 60)

    # Проверяем есть ли аргументы командной строки
    if len(sys.argv) >= 2:
        # CLI режим
        url = sys.argv[1]
        print("🚀 Запуск конвертера (CLI режим)")
        print(f"📋 URL: {url}")
        print("=" * 70)

        # В CLI режиме используем все форматы с транслитерацией (без PDF)
        converter = UniversalSheetsConverter(
            formats=["csv", "json", "txt", "xlsx", "md", "html", "yaml"],
            transliterate=True,
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
                print("\n1. Ввести URL таблицы (с выбором форматов)")
                print("2. Использовать тестовую таблицу (все форматы)")
                print("3. Выход")

                choice = input("\n📝 Выберите опцию (1-3): ").strip()

                if choice == "1":
                    url = input("\n📝 Введите URL Google Таблицы: ").strip()

                    if not url:
                        print("⚠️ Пустая строка. Введите корректный URL.")
                        continue

                    if "docs.google.com/spreadsheets" not in url:
                        print(
                            "⚠️ Некорректный URL. Должен содержать 'docs.google.com/spreadsheets'"
                        )
                        continue

                    # Интерактивный выбор форматов
                    formats, transliterate = select_formats_interactive()
                    converter = UniversalSheetsConverter(
                        formats=formats, transliterate=transliterate
                    )

                elif choice == "2":
                    url = URL_TEST
                    print(f"📝 Используем тестовую таблицу: {url}")

                    # Все форматы с транслитерацией для тестирования (без PDF)
                    converter = UniversalSheetsConverter(
                        formats=["csv", "json", "txt", "xlsx", "md", "html", "yaml"],
                        transliterate=True,
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
                    continue_choice = (
                        input("\n❓ Хотите обработать еще одну таблицу? (y/n): ")
                        .strip()
                        .lower()
                    )
                    if continue_choice in ["y", "yes", "д", "да"]:
                        break
                    elif continue_choice in ["n", "no", "н", "нет"]:
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
