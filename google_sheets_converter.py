#!/usr/bin/env python3
"""
Google Sheets to CSV/JSON Converter
Конвертирует все страницы Google Таблицы в CSV и JSON с правильной обработкой переносов строк
"""

import re

import json
import os
import pandas as pd
import requests
import sys
from typing import Any, Dict, List, Tuple

from config import GOOGLE_SHEETS_API_KEY

URL_TEST = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit?usp=sharing"


class GoogleSheetsConverter:
    def __init__(self):
        self.expected_headers = [
            "category",
            "subcategory",
            "button_text",
            "keywords",
            "answer_ukr",
            "answer_rus",
            "sort_order",
        ]
        # Поля где ожидаем многострочный текст
        self.text_fields = ["answer_ukr", "answer_rus", "keywords"]
        self.output_dir = "data/converted-data/"
        self.api_key = GOOGLE_SHEETS_API_KEY

    def create_output_directory(self):
        """Создает выходную директорию если ее нет"""
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"📁 Рабочая директория: {self.output_dir}")

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
            # Официальный Google Sheets API v4 endpoint
            api_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"

            # Добавляем API key если он есть
            params = {}
            if self.api_key:
                params["key"] = self.api_key
                print(f"🔑 Используем API key: {self.api_key[:20]}...")

            headers = {"User-Agent": "GoogleSheetsConverter/1.0"}

            response = requests.get(api_url, params=params, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                sheets_info = []

                # Извлекаем информацию о листах из ответа API
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
                print(f"❌ Ошибка доступа (HTTP 403): {response.text}")
                if "API key" in response.text:
                    print("💡 Проверьте правильность API ключа и что Google Sheets API включен")
                else:
                    print("💡 Возможно таблица не публичная. Проверьте настройки доступа")
                return [{"gid": "0", "name": "Sheet1"}]

            elif response.status_code == 404:
                print(f"❌ Таблица не найдена (HTTP 404)")
                print("💡 Проверьте правильность ID таблицы")
                return [{"gid": "0", "name": "Sheet1"}]

            else:
                print(f"❌ API вернул ошибку HTTP {response.status_code}: {response.text}")
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

    def validate_headers(self, df: pd.DataFrame, sheet_name: str) -> bool:
        """Проверяет соответствие заголовков ожидаемому формату"""
        actual_headers = df.columns.tolist()

        # Проверяем точное соответствие
        if len(actual_headers) != len(self.expected_headers):
            print(
                f"❌ [{sheet_name}] Неверное количество колонок: {len(actual_headers)} вместо {len(self.expected_headers)}"
            )
            return False

        for i, (actual, expected) in enumerate(zip(actual_headers, self.expected_headers)):
            if actual.strip().lower() != expected.lower():
                print(
                    f"❌ [{sheet_name}] Неверный заголовок в колонке {i + 1}: '{actual}' вместо '{expected}'"
                )
                return False

        print(f"✅ [{sheet_name}] Формат заголовков корректный")
        return True

    def process_text_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Обрабатывает текстовые поля - заменяет переносы строк на \\n"""
        df_processed = df.copy()

        for field in self.text_fields:
            if field in df_processed.columns:
                # Заменяем реальные переносы строк на \\n
                df_processed[field] = (
                    df_processed[field].astype(str).str.replace("\n", "\\n", regex=False)
                )
                df_processed[field] = df_processed[field].str.replace("\r", "", regex=False)

        return df_processed

    def load_sheet_data(
        self, sheet_id: str, gid: str, sheet_name: str
    ) -> Tuple[pd.DataFrame, bool]:
        """Загружает данные одной страницы"""
        try:
            csv_url = self.get_csv_url(sheet_id, gid)
            print(f"📥 Загружаем страницу: {sheet_name}")

            df = pd.read_csv(csv_url)

            # Удаляем пустые строки
            df = df.dropna(how="all")

            print(f"📊 [{sheet_name}] Загружено {len(df)} строк")
            return df, True

        except Exception as e:
            print(f"❌ [{sheet_name}] Ошибка загрузки: {e}")
            return pd.DataFrame(), False

    def transliterate_russian(self, text: str) -> str:
        """Транслитерирует русский текст в латиницу"""
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
        # Сначала транслитерируем русские символы
        clean_name = self.transliterate_russian(sheet_name)

        # Заменяем все что НЕ латинские буквы, цифры, дефисы на подчеркивания
        clean_name = re.sub(r"[^a-zA-Z0-9\-]", "_", clean_name)

        # Убираем множественные подчеркивания
        clean_name = re.sub(r"_+", "_", clean_name)

        # Убираем подчеркивания в начале и конце
        clean_name = clean_name.strip("_").lower()

        return clean_name if clean_name else "sheet"

    def save_txt(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в TXT для удобного просмотра"""
        clean_name = self.clean_filename(sheet_name)
        filename = f"{clean_name}_page_{page_num:02d}.txt"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"📋 {sheet_name} - Страница {page_num}\n")
            f.write("=" * 60 + "\n\n")

            for index, row in df.iterrows():
                # Номер записи
                f.write(f"🔸 Запись #{index + 1}\n")
                f.write("-" * 30 + "\n")

                # Категория и подкатегория
                f.write(f"📂 Категория: {row.get('category', 'N/A')}\n")
                f.write(f"📁 Подкатегория: {row.get('subcategory', 'N/A')}\n")

                # Текст кнопки и ключевые слова
                f.write(f"🔘 Кнопка: {row.get('button_text', 'N/A')}\n")

                keywords = str(row.get("keywords", ""))
                if keywords and keywords != "nan":
                    # Заменяем \\n на реальные переносы для удобного чтения
                    keywords = keywords.replace("\\n", "\n")
                    f.write(f"🔍 Ключевые слова: {keywords}\n")

                f.write("\n")

                # Ответ на украинском
                answer_ukr = str(row.get("answer_ukr", ""))
                if answer_ukr and answer_ukr != "nan":
                    # Заменяем \\n на реальные переносы строк
                    answer_ukr = answer_ukr.replace("\\n", "\n")
                    f.write("🇺🇦 ОТВЕТ НА УКРАИНСКОМ:\n")
                    f.write(f"{answer_ukr}\n\n")

                # Ответ на русском
                answer_rus = str(row.get("answer_rus", ""))
                if answer_rus and answer_rus != "nan":
                    # Заменяем \\n на реальные переносы строк
                    answer_rus = answer_rus.replace("\\n", "\n")
                    f.write("🇷🇺 ОТВЕТ НА РУССКОМ:\n")
                    f.write(f"{answer_rus}\n\n")

                # Порядок сортировки
                f.write(f"📊 Порядок: {row.get('sort_order', 'N/A')}\n")
                f.write("\n" + "=" * 60 + "\n\n")

        print(f"📄 TXT сохранен: {filename}")

    def save_csv(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в CSV"""
        clean_name = self.clean_filename(sheet_name)
        filename = f"{clean_name}_page_{page_num:02d}.csv"
        filepath = os.path.join(self.output_dir, filename)

        df.to_csv(filepath, index=False, sep=",", encoding="utf-8", quoting=1)
        print(f"💾 CSV сохранен: {filename}")

    def save_json(self, df: pd.DataFrame, sheet_name: str, page_num: int):
        """Сохраняет DataFrame в JSON"""
        clean_name = self.clean_filename(sheet_name)
        filename = f"{clean_name}_page_{page_num:02d}.json"
        filepath = os.path.join(self.output_dir, filename)

        # Конвертируем DataFrame в список словарей
        data = df.to_dict("records")

        # Сохраняем с отступами в 4 пробела
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"💾 JSON сохранен: {filename}")

    def convert_all_sheets(self, url: str) -> bool:
        """Конвертирует все страницы таблицы"""
        try:
            # Создаем выходную директорию
            self.create_output_directory()

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
                df, load_success = self.load_sheet_data(sheet_id, gid, sheet_name)

                if not load_success:
                    print(f"⏭️ [{sheet_name}] Пропускаем из-за ошибки загрузки")
                    skipped_count += 1
                    continue

                # Проверяем заголовки
                if not self.validate_headers(df, sheet_name):
                    print(f"⏭️ [{sheet_name}] Пропускаем из-за несоответствия заголовков")
                    skipped_count += 1
                    continue

                # Обрабатываем текстовые поля
                df_processed = self.process_text_fields(df)

                # Сохраняем файлы в трех форматах
                self.save_csv(df_processed, sheet_name, page_num)
                self.save_json(df_processed, sheet_name, page_num)
                self.save_txt(df_processed, sheet_name, page_num)

                processed_count += 1
                print(f"✅ [{sheet_name}] Обработка завершена")

            # Итоговый отчет
            print("\n" + "=" * 50)
            print("📊 ИТОГОВЫЙ ОТЧЕТ")
            print("=" * 50)
            print(f"✅ Успешно обработано: {processed_count} страниц")
            print(f"⏭️ Пропущено: {skipped_count} страниц")
            print(f"📁 Файлы сохранены в: {self.output_dir}")

            if processed_count > 0:
                print("\n🎉 Конвертация завершена успешно!")
                return True
            else:
                print("\n💥 Ни одна страница не была успешно обработана")
                return False

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            return False


def main():
    """Точка входа в программу"""
    converter = GoogleSheetsConverter()

    # Проверяем есть ли аргументы командной строки
    if len(sys.argv) >= 2:
        # CLI режим
        url = sys.argv[1]
        print("🚀 Запуск конвертера Google Таблиц (CLI режим)")
        print(f"📋 URL: {url}")
        print("=" * 70)

        success = converter.convert_all_sheets(url)

        if success:
            print("\n🎉 Программа завершена успешно!")
        else:
            print("\n💥 Программа завершена с ошибками.")
            sys.exit(1)
    else:
        # Интерактивный режим
        print("📋 Google Sheets to CSV/JSON/TXT Converter")
        print("=" * 40)
        print("🔧 Интерактивный режим")
        print("\nОжидаемый формат заголовков:")
        print("  category;subcategory;button_text;keywords;answer_ukr;answer_rus;sort_order")
        print(f"\n🧪 Тестовая таблица: {URL_TEST}")
        print("-" * 40)

        while True:
            try:
                print("\n1. Ввести URL таблицы")
                print("2. Использовать тестовую таблицу")
                print("3. Выход")

                choice = input("\n📝 Выберите опцию (1-3): ").strip()

                if choice == "1":
                    url = input("\n📝 Введите URL Google Таблицы: ").strip()

                    if not url:
                        print("⚠️ Пустая строка. Введите корректный URL.")
                        continue

                    if "docs.google.com/spreadsheets" not in url:
                        print("⚠️ Некорректный URL. Должен содержать 'docs.google.com/spreadsheets'")
                        continue

                elif choice == "2":
                    url = URL_TEST
                    print(f"📝 Используем тестовую таблицу: {url}")

                elif choice in ["3", "exit", "quit", "выход"]:
                    print("👋 До свидания!")
                    break

                else:
                    print("⚠️ Неверный выбор. Введите 1, 2 или 3.")
                    continue

                print("\n🚀 Запуск конвертера Google Таблиц (интерактивный режим)")
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
                        input("\n❓ Хотите обработать еще одну таблицу? (y/n): ").strip().lower()
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
