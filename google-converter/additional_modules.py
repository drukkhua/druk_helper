# ============================================================================
# ДОПОЛНИТЕЛЬНЫЕ ЭКСПОРТЕРЫ / ADDITIONAL EXPORTERS
# ============================================================================

class TXTExporter(BaseExporter):
    """Экспортер в читаемый TXT формат"""
    
    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'txt')
    
    def get_extension(self) -> str:
        return 'txt'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"📋 Данные таблицы\n")
            f.write("=" * 60 + "\n\n")
            
            for index, row in data.iterrows():
                f.write(f"🔸 Запись #{index + 1}\n")
                f.write("-" * 30 + "\n")
                
                for column in data.columns:
                    value = row[column]
                    if pd.notna(value):
                        f.write(f"📌 {column}: {value}\n")
                
                f.write("\n" + "=" * 60 + "\n\n")


class HTMLExporter(BaseExporter):
    """Экспортер в HTML с красивым стилем"""
    
    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'html')
    
    def get_extension(self) -> str:
        return 'html'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        title = kwargs.get('title', 'Google Sheets Data')
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
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
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 {title}</h1>
        <div>Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        <table>
"""
        
        if not data.empty:
            # Заголовки
            html_content += "            <thead><tr>\n"
            for column in data.columns:
                html_content += f"                <th>{column}</th>\n"
            html_content += "            </tr></thead>\n            <tbody>\n"
            
            # Данные
            for _, row in data.iterrows():
                html_content += "                <tr>\n"
                for column in data.columns:
                    value = row[column] if pd.notna(row[column]) else ""
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


class ParquetExporter(BaseExporter):
    """Экспортер в Parquet формат"""
    
    def __init__(self, output_dir: str):
        super().__init__(output_dir, 'parquet')
    
    def get_extension(self) -> str:
        return 'parquet'
    
    def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        try:
            import pyarrow.parquet as pq
            compression = kwargs.get('compression', 'snappy')
            data.to_parquet(filepath, compression=compression)
        except ImportError:
            raise ImportError("pyarrow required for Parquet export")


# ============================================================================
# РАСШИРЕННЫЕ ОБРАБОТЧИКИ / ADVANCED PROCESSORS
# ============================================================================

class HeaderValidator:
    """Валидатор заголовков таблицы"""
    
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
                    raise ValueError(
                        f"Header mismatch at position {i}: '{actual}' != '{expected}'"
                    )
        
        # Нормализуем заголовки
        data.columns = [col.strip().lower() for col in data.columns]
        return data


class DataCleaner:
    """Очиститель данных"""
    
    def __init__(self, 
                 remove_empty_rows: bool = True,
                 remove_empty_cols: bool = False,
                 fill_na_value: Any = ''):
        self.remove_empty_rows = remove_empty_rows
        self.remove_empty_cols = remove_empty_cols
        self.fill_na_value = fill_na_value
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Очищает данные"""
        df = data.copy()
        
        if self.remove_empty_rows:
            df = df.dropna(how='all')
        
        if self.remove_empty_cols:
            df = df.dropna(axis=1, how='all')
        
        if self.fill_na_value is not None:
            df = df.fillna(self.fill_na_value)
        
        return df


class DataTransformer:
    """Трансформер данных с кастомными функциями"""
    
    def __init__(self, transformations: Dict[str, callable]):
        self.transformations = transformations
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Применяет трансформации к колонкам"""
        df = data.copy()
        
        for column, transform_func in self.transformations.items():
            if column in df.columns:
                df[column] = df[column].apply(transform_func)
        
        return df


# ============================================================================
# УЛУЧШЕННАЯ СИСТЕМА КЕШИРОВАНИЯ / ADVANCED CACHING
# ============================================================================

class MemoryCache:
    """Кеш в памяти (для тестирования)"""
    
    def __init__(self):
        self.cache_data = {}
    
    def get(self, key: str) -> Optional[Any]:
        return self.cache_data.get(key)
    
    def set(self, key: str, value: Any) -> None:
        self.cache_data[key] = value
    
    def is_changed(self, key: str, data: str) -> bool:
        current_hash = hashlib.md5(data.encode('utf-8')).hexdigest()
        cached_entry = self.get(key)
        
        if cached_entry and cached_entry.get('hash') == current_hash:
            return False
        
        self.set(key, {
            'hash': current_hash,
            'last_updated': datetime.now().isoformat()
        })
        return True


class RedisCache:
    """Кеш на базе Redis (для production)"""
    
    def __init__(self, redis_client, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        try:
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None
    
    def set(self, key: str, value: Any) -> None:
        try:
            self.redis.setex(key, self.ttl, json.dumps(value, default=str))
        except Exception:
            pass
    
    def is_changed(self, key: str, data: str) -> bool:
        current_hash = hashlib.md5(data.encode('utf-8')).hexdigest()
        cached_entry = self.get(key)
        
        if cached_entry and cached_entry.get('hash') == current_hash:
            return False
        
        self.set(key, {
            'hash': current_hash,
            'last_updated': datetime.now().isoformat()
        })
        return True


# ============================================================================
# ФАБРИКИ ДЛЯ УДОБНОГО СОЗДАНИЯ / FACTORIES
# ============================================================================

class ConverterFactory:
    """Фабрика для создания конвертеров с разными конфигурациями"""
    
    @staticmethod
    def create_basic_converter(output_dir: str = "output", 
                             api_key: Optional[str] = None) -> ModularSheetsConverter:
        """Создает базовый конвертер"""
        config = Config(api_key=api_key, output_dir=output_dir)
        cache = FileCache(config.cache_file)
        
        converter = ModularSheetsConverter(config=config, cache=cache)
        
        # Базовые экспортеры
        converter.register_exporter('csv', CSVExporter(output_dir))
        converter.register_exporter('json', JSONExporter(output_dir))
        converter.register_exporter('txt', TXTExporter(output_dir))
        
        # Базовые обработчики
        converter.add_processor(DataCleaner())
        converter.add_processor(TextFieldProcessor(auto_detect=True))
        
        return converter
    
    @staticmethod
    def create_full_converter(output_dir: str = "output",
                            api_key: Optional[str] = None,
                            enable_redis: bool = False) -> ModularSheetsConverter:
        """Создает полнофункциональный конвертер"""
        config = Config(api_key=api_key, output_dir=output_dir, batch_size=100)
        
        # Выбираем тип кеша
        if enable_redis:
            try:
                import redis
                redis_client = redis.Redis(host='localhost', port=6379, db=0)
                cache = RedisCache(redis_client)
            except ImportError:
                print("⚠️ Redis недоступен, используем файловый кеш")
                cache = FileCache(config.cache_file)
        else:
            cache = FileCache(config.cache_file)
        
        converter = ModularSheetsConverter(config=config, cache=cache)
        
        # Все доступные экспортеры
        converter.register_exporter('csv', CSVExporter(output_dir))
        converter.register_exporter('json', JSONExporter(output_dir))
        converter.register_exporter('txt', TXTExporter(output_dir))
        converter.register_exporter('html', HTMLExporter(output_dir))
        converter.register_exporter('yaml', YAMLExporter(output_dir))
        
        if XLSX_AVAILABLE:
            converter.register_exporter('xlsx', ExcelExporter(output_dir))
        
        try:
            converter.register_exporter('parquet', ParquetExporter(output_dir))
        except ImportError:
            pass
        
        # Продвинутые обработчики
        converter.add_processor(DataCleaner(remove_empty_rows=True))
        converter.add_processor(TextFieldProcessor(auto_detect=True))
        
        return converter


# ============================================================================
# ТЕСТЫ / TESTS
# ============================================================================

def test_basic_functionality():
    """Базовые тесты функциональности"""
    print("🧪 Запуск базовых тестов...")
    
    # Тест конфигурации
    config = Config(api_key="test_key", output_dir="test_output")
    assert config.api_key == "test_key"
    assert config.output_dir == "test_output"
    print("✅ Тест конфигурации пройден")
    
    # Тест кеша
    cache = MemoryCache()
    cache.set("test_key", {"value": "test"})
    assert cache.get("test_key")["value"] == "test"
    print("✅ Тест кеша пройден")
    
    # Тест обработчиков данных
    df = pd.DataFrame({
        'col1': ['value1', 'value2\nwith\nnewlines'],
        'col2': [1, 2]
    })
    
    processor = TextFieldProcessor(auto_detect=True)
    processed_df = processor.process(df)
    assert processed_df is not None
    print("✅ Тест обработчика текста пройден")
    
    # Тест экспортеров
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        csv_exporter = CSVExporter(temp_dir)
        filepath = csv_exporter.export(df, "test")
        assert os.path.exists(filepath)
        print("✅ Тест CSV экспортера пройден")
        
        json_exporter = JSONExporter(temp_dir)
        filepath = json_exporter.export(df, "test")
        assert os.path.exists(filepath)
        print("✅ Тест JSON экспортера пройден")
    
    print("🎉 Все базовые тесты пройдены!")


def test_integration():
    """Интеграционный тест с реальной таблицей"""
    print("🧪 Запуск интеграционного теста...")
    
    url = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit"
    
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем конвертер для тестирования
            converter = ConverterFactory.create_basic_converter(output_dir=temp_dir)
            
            # Тестируем извлечение ID
            client = GoogleSheetsClient(Config())
            sheet_id = client.extract_sheet_id(url)
            assert len(sheet_id) > 10
            print("✅ Извлечение ID пройдено")
            
            # Тестируем получение метаданных
            sheets_info = client.get_sheets_metadata(sheet_id)
            assert len(sheets_info) > 0
            print("✅ Получение метаданных пройдено")
            
            print("🎉 Интеграционный тест пройден!")
            
    except Exception as e:
        print(f"❌ Интеграционный тест неудачен: {e}")


def test_performance():
    """Тест производительности"""
    print("🧪 Тест производительности...")
    
    # Создаем большой DataFrame для тестирования
    large_df = pd.DataFrame({
        f'col_{i}': [f'value_{j}_{i}' for j in range(1000)]
        for i in range(10)
    })
    
    import time
    start_time = time.time()
    
    # Тестируем обработку
    processor = TextFieldProcessor(auto_detect=True)
    processed_df = processor.process(large_df)
    
    processing_time = time.time() - start_time
    print(f"⏱️ Время обработки 10,000 ячеек: {processing_time:.3f} сек")
    
    # Тестируем экспорт
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        start_time = time.time()
        
        csv_exporter = CSVExporter(temp_dir)
        csv_exporter.export(processed_df, "performance_test")
        
        export_time = time.time() - start_time
        print(f"⏱️ Время CSV экспорта: {export_time:.3f} сек")
    
    print("🎉 Тест производительности завершен!")


# ============================================================================
# РАСШИРЕННЫЕ ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ / ADVANCED USAGE EXAMPLES
# ============================================================================

def example_custom_processor():
    """Пример создания кастомного обработчика"""
    
    class EmailMaskProcessor:
        """Маскирует email адреса в данных"""
        
        def process(self, data: pd.DataFrame) -> pd.DataFrame:
            df = data.copy()
            
            for column in df.columns:
                if 'email' in column.lower():
                    df[column] = df[column].astype(str).str.replace(
                        r'(\w+)@(\w+\.\w+)',
                        r'\1@***.\2',
                        regex=True
                    )
            
            return df
    
    # Использование
    converter = ConverterFactory.create_basic_converter()
    converter.add_processor(EmailMaskProcessor())
    
    print("✅ Кастомный обработчик создан")


def example_custom_exporter():
    """Пример создания кастомного экспортера"""
    
    class SQLExporter(BaseExporter):
        """Экспортер в SQL INSERT statements"""
        
        def __init__(self, output_dir: str, table_name: str = "data"):
            super().__init__(output_dir, 'sql')
            self.table_name = table_name
        
        def get_extension(self) -> str:
            return 'sql'
        
        def export_data(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"-- SQL export for {self.table_name}\n")
                f.write(f"CREATE TABLE IF NOT EXISTS {self.table_name} (\n")
                
                # Создаем схему
                columns = []
                for col in data.columns:
                    columns.append(f"    {col} TEXT")
                f.write(",\n".join(columns))
                f.write("\n);\n\n")
                
                # Создаем INSERT statements
                for _, row in data.iterrows():
                    values = []
                    for value in row:
                        if pd.isna(value):
                            values.append("NULL")
                        else:
                            escaped_value = str(value).replace("'", "''")
                            values.append(f"'{escaped_value}'")
                    
                    f.write(f"INSERT INTO {self.table_name} VALUES ({', '.join(values)});\n")
    
    # Использование
    converter = ConverterFactory.create_basic_converter()
    converter.register_exporter('sql', SQLExporter(converter.config.output_dir, 'my_table'))
    
    print("✅ Кастомный экспортер создан")


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ ДЛЯ ДЕМОНСТРАЦИИ / MAIN DEMO FUNCTION
# ============================================================================

def demo_modular_converter():
    """Демонстрация всех возможностей модульного конвертера"""
    
    print("🚀 Демонстрация модульного Google Sheets конвертера")
    print("=" * 60)
    
    url = "https://docs.google.com/spreadsheets/d/1RagVK40gWitjfQE-_wBD8HnSaeDGGMZJ2uWfICLRqFQ/edit"
    
    # 1. Простая конвертация
    print("\n1️⃣ Простая конвертация:")
    result = quick_convert(url, formats=['csv', 'json'], output_dir="demo_output")
    print(f"✅ Обработано листов: {result['summary']['processed_sheets']}")
    
    # 2. Полнофункциональная конвертация
    print("\n2️⃣ Полнофункциональная конвертация:")
    converter = ConverterFactory.create_full_converter(output_dir="demo_full")
    
    # Добавляем кастомные обработчики
    converter.add_processor(DataTransformer({
        'sort_order': lambda x: int(x) if pd.notna(x) and str(x).isdigit() else 0
    }))
    
    formats = ['csv', 'json', 'txt', 'html', 'yaml']
    if XLSX_AVAILABLE:
        formats.append('xlsx')
    
    result = converter.convert_spreadsheet(url, formats)
    print(f"✅ Создано файлов: {result['summary']['files_created']}")
    
    # 3. Тестирование
    print("\n3️⃣ Запуск тестов:")
    test_basic_functionality()
    test_integration()
    test_performance()
    
    print("\n🎉 Демонстрация завершена!")


if __name__ == "__main__":
    # Запуск демонстрации
    demo_modular_converter()
