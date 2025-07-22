"""
Тесты для GoogleSheetsUpdater
Тестирование интеграции с Google Sheets API
"""

from io import StringIO

import aiohttp
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, mock_open, patch

from google_sheets_updater import GoogleSheetsUpdater


class TestGoogleSheetsUpdater:
    """Тесты для класса GoogleSheetsUpdater"""

    def test_init_google_sheets_updater(self):
        """Тест инициализации GoogleSheetsUpdater"""
        with patch("google_sheets_updater.GOOGLE_SHEETS_API_KEY", "test_key"):
            updater = GoogleSheetsUpdater()
            assert updater.api_key == "test_key"
            assert updater.output_dir == "./data"
            assert "визитки" in updater.sheet_mapping

    def test_extract_sheet_id_valid_url(self):
        """Тест извлечения ID из валидного URL"""
        updater = GoogleSheetsUpdater()
        url = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit"
        sheet_id = updater.extract_sheet_id(url)
        assert sheet_id == "1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ"

    def test_extract_sheet_id_invalid_url(self):
        """Тест извлечения ID из невалидного URL"""
        updater = GoogleSheetsUpdater()
        url = "https://invalid-url.com"
        sheet_id = updater.extract_sheet_id(url)
        assert sheet_id is None

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_get_all_sheets_info_success(self, mock_get):
        """Тест успешного получения информации о листах"""
        # Мок ответа API
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "sheets": [
                    {"properties": {"sheetId": 0, "title": "визитки"}},
                    {"properties": {"sheetId": 123456, "title": "футболки"}},
                ]
            }
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        updater = GoogleSheetsUpdater()
        sheets_info = await updater.get_all_sheets_info("test_sheet_id")

        assert len(sheets_info) == 2
        assert sheets_info[0]["title"] == "визитки"
        assert sheets_info[1]["sheet_id"] == 123456

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_get_all_sheets_info_error(self, mock_get):
        """Тест обработки ошибки при получении информации о листах"""
        mock_get.side_effect = aiohttp.ClientError("Network error")

        updater = GoogleSheetsUpdater()
        sheets_info = await updater.get_all_sheets_info("test_sheet_id")

        assert sheets_info == []

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_download_csv_data_success(self, mock_get):
        """Тест успешного скачивания CSV данных"""
        # Мок ответа с CSV данными
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.read = AsyncMock(
            return_value=b"\xef\xbb\xbfcategory,subcategory,button_text\ntest,1,Test Button"
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        updater = GoogleSheetsUpdater()
        csv_content = await updater.download_csv_data("test_sheet_id", "0")

        assert csv_content is not None
        assert "category,subcategory,button_text" in csv_content
        assert "test,1,Test Button" in csv_content

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_download_csv_data_error(self, mock_get):
        """Тест обработки ошибки при скачивании CSV"""
        mock_get.side_effect = aiohttp.ClientError("Download error")

        updater = GoogleSheetsUpdater()
        csv_content = await updater.download_csv_data("test_sheet_id", "0")

        assert csv_content is None

    def test_convert_csv_delimiter(self):
        """Тест конвертации разделителя CSV"""
        updater = GoogleSheetsUpdater()
        input_csv = "category,subcategory,button_text\ntest,1,Test Button"

        converted = updater._convert_csv_delimiter(input_csv)

        assert "category;subcategory;button_text" in converted
        assert "test;1;Test Button" in converted

    def test_convert_csv_delimiter_with_quotes(self):
        """Тест конвертации CSV с кавычками"""
        updater = GoogleSheetsUpdater()
        input_csv = 'category,subcategory,"button_text"\ntest,1,"Test, Button"'

        converted = updater._convert_csv_delimiter(input_csv)

        assert "category;subcategory;button_text" in converted
        assert "test;1;Test, Button" in converted

    def test_normalize_sheet_name(self):
        """Тест нормализации названий листов"""
        updater = GoogleSheetsUpdater()

        # Тест прямого сопоставления
        assert updater.normalize_sheet_name("визитки") == "визитки"
        assert updater.normalize_sheet_name("  ВИЗИТКИ  ") == "визитки"

        # Тест несуществующего листа
        assert updater.normalize_sheet_name("несуществует") == "несуществует"

    @pytest.mark.asyncio
    @patch("os.makedirs")
    @patch("aiofiles.open")
    async def test_save_csv_to_data_success(self, mock_file, mock_makedirs):
        """Тест успешного сохранения CSV файла"""
        # Мок контекстного менеджера
        mock_context = AsyncMock()
        mock_context.write = AsyncMock()
        mock_file.return_value.__aenter__.return_value = mock_context

        updater = GoogleSheetsUpdater()
        csv_content = "category,subcategory,button_text\ntest,1,Test Button"

        result = await updater.save_csv_to_data(csv_content, "test.csv")

        assert result is True
        mock_makedirs.assert_called_once_with("./data", exist_ok=True)
        mock_file.assert_called_once()

    @pytest.mark.asyncio
    @patch("os.makedirs")
    @patch("aiofiles.open", side_effect=IOError("Write error"))
    async def test_save_csv_to_data_error(self, mock_file, mock_makedirs):
        """Тест обработки ошибки при сохранении файла"""
        updater = GoogleSheetsUpdater()
        csv_content = "test content"

        result = await updater.save_csv_to_data(csv_content, "test.csv")

        assert result is False

    @pytest.mark.asyncio
    @patch.object(GoogleSheetsUpdater, "get_all_sheets_info")
    @patch.object(GoogleSheetsUpdater, "download_csv_data")
    @patch.object(GoogleSheetsUpdater, "save_csv_to_data")
    @patch.object(GoogleSheetsUpdater, "extract_sheet_id")
    async def test_update_templates_from_google_sheets_success(
        self, mock_extract_id, mock_save, mock_download, mock_get_info
    ):
        """Тест успешного обновления шаблонов из Google Sheets"""
        # Настройка моков
        mock_extract_id.return_value = "test_sheet_id"
        mock_get_info.return_value = [
            {"title": "визитки", "gid": "0"},
            {"title": "футболки", "gid": "123456"},
        ]
        mock_download.return_value = "csv content"
        mock_save.return_value = True

        updater = GoogleSheetsUpdater()
        result = await updater.update_templates_from_google_sheets("test_url")

        assert result is True
        assert mock_download.call_count == 2  # Два листа
        assert mock_save.call_count == 2

    @pytest.mark.asyncio
    @patch.object(GoogleSheetsUpdater, "extract_sheet_id")
    async def test_update_templates_invalid_url(self, mock_extract_id):
        """Тест обработки невалидного URL"""
        mock_extract_id.return_value = None

        updater = GoogleSheetsUpdater()
        result = await updater.update_templates_from_google_sheets("invalid_url")

        assert result is False

    @pytest.mark.asyncio
    @patch.object(GoogleSheetsUpdater, "extract_sheet_id")
    @patch.object(GoogleSheetsUpdater, "get_all_sheets_info")
    async def test_update_templates_no_sheets(self, mock_get_info, mock_extract_id):
        """Тест обработки случая когда нет листов"""
        mock_extract_id.return_value = "test_sheet_id"
        mock_get_info.return_value = []

        updater = GoogleSheetsUpdater()
        result = await updater.update_templates_from_google_sheets("test_url")

        assert result is False

    @pytest.mark.asyncio
    @patch("google_sheets_updater.sheets_updater")
    async def test_update_templates_from_sheets_function(self, mock_sheets_updater):
        """Тест функции-обертки update_templates_from_sheets"""
        from google_sheets_updater import update_templates_from_sheets

        # Мок асинхронного метода
        mock_sheets_updater.update_templates_from_google_sheets = AsyncMock(return_value=True)

        # Тест с URL
        result = await update_templates_from_sheets("test_url")
        assert result is True

        # Тест без URL (использует URL по умолчанию)
        result = await update_templates_from_sheets()
        assert result is True
