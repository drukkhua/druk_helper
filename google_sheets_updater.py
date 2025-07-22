"""
Модуль для обновления CSV данных из Google Sheets прямо в папку data
Используется командой /reload для обновления шаблонов
"""

import re
from io import StringIO

import aiofiles
import aiohttp
import asyncio
import csv
import logging
import os
from typing import Dict, List, Optional

from config import GOOGLE_SHEETS_API_KEY

logger = logging.getLogger(__name__)


class GoogleSheetsUpdater:
    """Класс для обновления CSV данных из Google Sheets"""

    def __init__(self) -> None:
        self.api_key = GOOGLE_SHEETS_API_KEY
        self.output_dir = "./data"

        # Маппинг названий листов к именам файлов
        self.sheet_mapping = {
            "визитки": "visitki_templates.csv",
            "футболки": "futbolki_templates.csv",
            "листовки": "listovki_templates.csv",
            "наклейки": "nakleyki_templates.csv",
            "блокноты": "bloknoty_templates.csv",
        }

    def extract_sheet_id(self, url: str) -> Optional[str]:
        """Извлекает ID таблицы из URL"""
        pattern = r"/spreadsheets/d/([a-zA-Z0-9-_]+)"
        match = re.search(pattern, url)
        return match.group(1) if match else None

    async def get_all_sheets_info(self, sheet_id: str) -> List[Dict]:
        """Получает информацию о всех листах через Google Sheets API"""
        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
            params = {"key": self.api_key}

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()

            sheets_info = []

            for sheet in data.get("sheets", []):
                properties = sheet.get("properties", {})
                sheets_info.append(
                    {
                        "sheet_id": properties.get("sheetId"),
                        "title": properties.get("title"),
                        "gid": str(properties.get("sheetId")),
                    }
                )

            return sheets_info

        except Exception as e:
            logger.error(f"Ошибка получения информации о листах: {e}")
            return []

    async def download_csv_data(self, sheet_id: str, gid: str) -> Optional[str]:
        """Загружает CSV данные одного листа"""
        try:
            csv_url = (
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            )

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(csv_url) as response:
                    response.raise_for_status()
                    content_bytes = await response.read()

            # Декодируем данные
            content = content_bytes.decode("utf-8-sig")
            return content

        except Exception as e:
            logger.error(f"Ошибка загрузки CSV данных для gid {gid}: {e}")
            return None

    async def save_csv_to_data(self, csv_content: str, filename: str) -> bool:
        """Сохраняет CSV содержимое в файл в папке data с правильным разделителем"""
        try:
            # Создаем папку data если её нет
            os.makedirs(self.output_dir, exist_ok=True)

            file_path = os.path.join(self.output_dir, filename)

            # Конвертируем CSV с запятой в CSV с точкой с запятой
            converted_content = self._convert_csv_delimiter(csv_content)

            # Сохраняем файл асинхронно
            async with aiofiles.open(file_path, "w", encoding="utf-8", newline="") as f:
                await f.write(converted_content)

            logger.info(f"✅ Сохранен файл: {filename}")
            return True

        except Exception as e:
            logger.error(f"Ошибка сохранения файла {filename}: {e}")
            return False

    def _convert_csv_delimiter(self, csv_content: str) -> str:
        """Конвертирует CSV с запятыми в CSV с точками с запятой"""
        try:
            # Читаем CSV с запятыми
            input_reader = csv.reader(StringIO(csv_content))

            # Создаем выходной буфер
            output_buffer = StringIO()
            output_writer = csv.writer(output_buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)

            # Конвертируем каждую строку
            for row in input_reader:
                output_writer.writerow(row)

            return output_buffer.getvalue()

        except Exception as e:
            logger.error(f"Ошибка конвертации разделителя CSV: {e}")
            return csv_content

    def normalize_sheet_name(self, sheet_name: str) -> str:
        """Нормализует название листа для поиска в маппинге"""
        # Убираем лишние пробелы и приводим к нижнему регистру
        normalized = sheet_name.strip().lower()

        # Прямое сопоставление
        if normalized in self.sheet_mapping:
            return normalized

        return sheet_name

    async def update_templates_from_google_sheets(self, spreadsheet_url: str) -> bool:
        """
        Основная функция обновления шаблонов из Google Sheets
        Загружает только нужные листы и сохраняет их как CSV в папку data
        """
        try:
            logger.info("🔄 Начинаем обновление шаблонов из Google Sheets...")

            # Извлекаем ID таблицы
            sheet_id = self.extract_sheet_id(spreadsheet_url)
            if not sheet_id:
                logger.error("❌ Не удалось извлечь ID таблицы из URL")
                return False

            logger.info(f"🔍 ID таблицы: {sheet_id}")

            # Получаем информацию о всех листах
            sheets_info = await self.get_all_sheets_info(sheet_id)
            if not sheets_info:
                logger.error("❌ Не найдено ни одного листа в таблице")
                return False

            logger.info(f"📋 Найдено листов: {len(sheets_info)}")

            # Обрабатываем каждый лист
            updated_count = 0
            for sheet_info in sheets_info:
                sheet_title = sheet_info["title"]
                gid = sheet_info["gid"]

                # Нормализуем название листа
                normalized_name = self.normalize_sheet_name(sheet_title)

                # Проверяем, есть ли этот лист в нашем маппинге
                if normalized_name in self.sheet_mapping:
                    filename = self.sheet_mapping[normalized_name]

                    logger.info(f"📄 Обрабатываем лист: {sheet_title} -> {filename}")

                    # Загружаем CSV данные
                    csv_content = await self.download_csv_data(sheet_id, gid)
                    if csv_content:
                        # Сохраняем в папку data
                        if await self.save_csv_to_data(csv_content, filename):
                            updated_count += 1
                        else:
                            logger.warning(f"⚠️ Не удалось сохранить файл: {filename}")
                    else:
                        logger.warning(f"⚠️ Не удалось загрузить данные для листа: {sheet_title}")
                else:
                    logger.info(f"⏭️ Пропускаем лист: {sheet_title} (не найден в маппинге)")

            if updated_count > 0:
                logger.info(f"✅ Успешно обновлено файлов: {updated_count}")
                return True
            else:
                logger.warning("⚠️ Ни одного файла не было обновлено")
                return False

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при обновлении шаблонов: {e}")
            return False


# Глобальный экземпляр для использования в боте
sheets_updater = GoogleSheetsUpdater()


async def update_templates_from_sheets(spreadsheet_url: Optional[str] = None) -> bool:
    """
    Функция-обертка для обновления шаблонов
    Если URL не указан, используется URL по умолчанию
    """
    if not spreadsheet_url:
        # URL по умолчанию (можно вынести в .env)
        spreadsheet_url = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit?usp=sharing"

    return await sheets_updater.update_templates_from_google_sheets(spreadsheet_url)


if __name__ == "__main__":
    # Тестирование модуля
    async def test_module() -> None:
        test_url = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit?usp=sharing"
        success = await update_templates_from_sheets(test_url)
        print(f"Результат обновления: {'✅ Успешно' if success else '❌ Ошибка'}")

    asyncio.run(test_module())
