# Тесты для Telegram Bot "Яскравий друк"

## Обзор

Этот каталог содержит комплексный набор тестов для проверки функциональности Telegram-бота. Тесты написаны с использованием pytest и покрывают все основные компоненты системы.

## Структура тестов

```
tests/
├── __init__.py                 # Пакет тестов
├── conftest.py                 # Общие фикстуры и конфигурация
├── test_template_manager.py    # Тесты управления шаблонами
├── test_google_sheets_updater.py  # Тесты интеграции Google Sheets
├── test_handlers.py            # Тесты обработчиков команд
├── test_validation.py          # Тесты валидации и безопасности
├── test_config.py              # Тесты конфигурации
├── test_stats.py               # Тесты статистики
├── test_integration.py         # Интеграционные тесты
└── README.md                   # Эта документация
```

## Типы тестов

### 🔬 Юнит-тесты
- **test_template_manager.py** - Тестирование загрузки, валидации и поиска шаблонов
- **test_google_sheets_updater.py** - Тестирование интеграции с Google Sheets API
- **test_validation.py** - Тестирование валидации входных данных и безопасности
- **test_config.py** - Тестирование конфигурации и переменных окружения
- **test_stats.py** - Тестирование системы статистики

### 🔗 Интеграционные тесты
- **test_integration.py** - Тестирование взаимодействия между компонентами
- **test_handlers.py** - Тестирование обработчиков команд и callback'ов

## Установка зависимостей

```bash
pip install pytest pytest-asyncio pytest-mock
```

### Дополнительные зависимости (опционально)
```bash
pip install pytest-cov pytest-html pytest-xdist
```

## Запуск тестов

### Все тесты
```bash
pytest
```

### Конкретный файл тестов
```bash
pytest tests/test_template_manager.py
```

### Конкретный тест
```bash
pytest tests/test_template_manager.py::TestTemplateManager::test_load_csv_file_success
```

### По маркерам
```bash
# Только юнит-тесты
pytest -m unit

# Только быстрые тесты (исключить медленные)
pytest -m "not slow"

# Только тесты администратора
pytest -m admin
```

### С покрытием кода
```bash
pytest --cov=. --cov-report=html
```

### Параллельное выполнение
```bash
pytest -n auto  # Использует все доступные CPU
```

## Маркеры тестов

- `@pytest.mark.unit` - Юнит-тесты
- `@pytest.mark.integration` - Интеграционные тесты
- `@pytest.mark.slow` - Медленные тесты
- `@pytest.mark.external` - Тесты с внешними зависимостями
- `@pytest.mark.admin` - Тесты админской функциональности
- `@pytest.mark.user` - Тесты пользовательской функциональности

## Конфигурация

### pytest.ini
Основная конфигурация pytest находится в корне проекта в файле `pytest.ini`.

### conftest.py
Содержит общие фикстуры:
- `mock_config` - Мок конфигурации
- `temp_data_dir` - Временная директория
- `sample_csv_content` - Образец CSV данных
- `mock_telegram_user` - Мок Telegram пользователя
- `mock_telegram_message` - Мок Telegram сообщения
- `mock_callback_query` - Мок Telegram callback

## Примеры использования

### Тестирование нового компонента

```python
import pytest
from unittest.mock import Mock, patch

class TestNewComponent:
    def test_new_functionality(self):
        # Arrange
        component = NewComponent()
        
        # Act
        result = component.do_something()
        
        # Assert
        assert result is not None
```

### Асинхронное тестирование

```python
@pytest.mark.asyncio
async def test_async_handler(mock_telegram_message):
    # Мок async методов
    mock_telegram_message.answer = AsyncMock()
    
    # Тестируем async функцию
    await some_async_handler(mock_telegram_message)
    
    # Проверяем вызовы
    mock_telegram_message.answer.assert_called_once()
```

### Мокирование внешних зависимостей

```python
@patch('requests.get')
def test_external_api_call(mock_get):
    # Настраиваем мок ответа
    mock_response = Mock()
    mock_response.json.return_value = {'status': 'ok'}
    mock_get.return_value = mock_response
    
    # Тестируем функцию
    result = call_external_api()
    
    assert result['status'] == 'ok'
```

## Отчеты о покрытии

После запуска с `--cov-report=html` отчет будет доступен в `htmlcov/index.html`.

Целевое покрытие: **80%+**

## Continuous Integration

Тесты автоматически запускаются при:
- Push в main ветку
- Создании Pull Request
- Scheduled runs (ежедневно)

## Troubleshooting

### Ошибки импорта
```bash
# Убедитесь, что PYTHONPATH включает корень проекта
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Async тесты не работают
```bash
pip install pytest-asyncio
```

### Медленные тесты
```bash
# Исключить медленные тесты
pytest -m "not slow"
```

### Тесты Google Sheets API
Для тестов, требующих реального API:
```bash
# Установить переменные окружения
export GOOGLE_SHEETS_API_KEY=your_test_api_key
pytest -m external
```

## Добавление новых тестов

1. **Создайте новый файл** `test_new_module.py`
2. **Импортируйте нужные фикстуры** из `conftest.py`
3. **Добавьте соответствующие маркеры**
4. **Следуйте принципу AAA** (Arrange, Act, Assert)
5. **Добавьте docstring** с описанием теста

## Лучшие практики

### ✅ Делайте
- Используйте описательные имена тестов
- Группируйте связанные тесты в классы
- Мокируйте внешние зависимости
- Тестируйте граничные случаи
- Проверяйте обработку ошибок

### ❌ Не делайте
- Не создавайте тесты, зависящие друг от друга
- Не используйте реальные API в юнит-тестах
- Не забывайте очищать временные файлы
- Не пишите слишком сложные тесты

## Метрики качества

- **Покрытие кода**: 80%+
- **Время выполнения**: <60 секунд для всех тестов
- **Flaky tests**: 0% (тесты должны быть стабильными)

## Поддержка

При возникновении проблем с тестами:
1. Проверьте логи pytest
2. Убедитесь в правильности установки зависимостей
3. Проверьте переменные окружения
4. Запустите тесты в verbose режиме: `pytest -v`