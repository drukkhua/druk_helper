# АНАЛИЗ АРХИТЕКТУРНЫХ ПРОБЛЕМ

# ❌ ПРОБЛЕМА 1: Нарушение Single Responsibility Principle
class UniversalSheetsConverter:
    """
    Этот класс делает ВСЁ:
    - Загрузка данных из API ✓
    - Кеширование ✓  
    - Валидация данных ✓
    - Обработка текста ✓
    - Транслитерация ✓
    - Сохранение в 7 форматов ✓
    - Создание отчетов ✓
    - UI логика ✓
    - Статистика ✓
    """
    pass

# ❌ ПРОБЛЕМА 2: Код дублирование в методах save_*
def save_csv(self, df, sheet_name, page_num):
    if 'csv' not in self.enabled_formats:
        return
    filename = f"{self.create_safe_filename(sheet_name, page_num)}.csv"
    filepath = os.path.join(self.output_dir, 'csv', filename)
    # Уникальная логика CSV
    self.stats['files_created'].append({...})  # Дублирование

def save_json(self, df, sheet_name, page_num):
    if 'json' not in self.enabled_formats:
        return
    filename = f"{self.create_safe_filename(sheet_name, page_num)}.json"
    filepath = os.path.join(self.output_dir, 'json', filename)
    # Уникальная логика JSON
    self.stats['files_created'].append({...})  # Дублирование

def save_xlsx(self, df, sheet_name, page_num):
    if 'xlsx' not in self.enabled_formats:
        return
    filename = f"{self.create_safe_filename(sheet_name, page_num)}.xlsx"
    filepath = os.path.join(self.output_dir, 'excel', filename)
    # Уникальная логика Excel
    self.stats['files_created'].append({...})  # Дублирование

# И так далее для 7 форматов...

# ❌ ПРОБЛЕМА 3: Тестируемость
# Как протестировать отдельные части? Класс монолитный.

# ❌ ПРОБЛЕМА 4: Расширяемость  
# Новый формат = добавление метода в класс + изменение save_all_formats()

# ❌ ПРОБЛЕМА 5: Конфигурация захардкожена
GOOGLE_SHEETS_API_KEY = "AIzaSyDzDspWPn07MQxNm3iJ1ZXPlJruWO1tzK4"
FILE_PATH = "../converted-data"
CACHE_FILE = "../converted-data/.cache.json"

# ❌ ПРОБЛЕМА 6: Смешение уровней абстракции
def convert_all_sheets(self, url: str) -> bool:
    # Высокий уровень: общая логика
    sheet_id = self.extract_sheet_id(url)
    sheets_info = self.get_all_sheets_info(sheet_id)
    
    # Средний уровень: обработка данных
    sheets_data = self.load_all_sheets_batch(sheet_id, sheets_info)
    
    # Низкий уровень: сохранение файлов
    self.save_all_formats(df_processed, df_original, sheet_name, page_num)
    
    # Детали реализации: создание отчетов
    self.save_stats_report()

# ❌ ПРОБЛЕМА 7: Зависимости не инжектятся
class UniversalSheetsConverter:
    def __init__(self, formats=['csv', 'json', 'txt'], transliterate=True, enable_caching=True):
        # Все зависимости создаются внутри класса
        # Нельзя подменить для тестирования
        self.api_key = GOOGLE_SHEETS_API_KEY  # Хардкод
        self.output_dir = FILE_PATH           # Хардкод

# ✅ ПРАВИЛЬНОЕ РЕШЕНИЕ: Разделение ответственности
class SheetsClient:
    """Только загрузка данных"""
    pass

class FormatExporter:
    """Только экспорт в один формат"""
    pass

class Cache:
    """Только кеширование"""
    pass

class Converter:
    """Только координация процесса"""
    def __init__(self, client, exporters, cache):
        self.client = client
        self.exporters = exporters  
        self.cache = cache