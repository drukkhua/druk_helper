# Telegram Bot "Яскравий друк" 🤖

[![CI/CD Pipeline](https://github.com/username/Bot-answers/actions/workflows/ci.yml/badge.svg)](https://github.com/username/Bot-answers/actions/workflows/ci.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Telegram-бот для типографии "Яскравий друк" - автоматизированная система обслуживания клиентов с шаблонными ответами и интеграцией с Google Sheets.

## 🚀 Особенности

- **Автоматические ответы** на основе ключевых слов
- **Интеграция с Google Sheets** для управления контентом
- **Поддержка двух языков** (украинский, русский)
- **Система поиска** по шаблонам
- **Статистика использования** и мониторинг
- **Безопасность** с валидацией ввода
- **Админ-панель** для управления

## 📋 Требования

- Python 3.9+
- Google Sheets API доступ
- Telegram Bot Token

## 🛠️ Установка

### Быстрый старт

```bash
# Клонирование репозитория
git clone https://github.com/username/Bot-answers.git
cd Bot-answers

# Установка зависимостей
make install

# Установка для разработки
make dev

# Установка pre-commit hooks
make pre-commit
```

### Ручная установка

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Установка в режиме разработки
pip install -e .[dev]
```

## ⚙️ Конфигурация

Создайте файл `.env` в корне проекта:

```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token
BOT_NAME=YaskravyiDrukBot

# Администраторы (через запятую)
ADMIN_USER_IDS=123456789,987654321

# Google Sheets API
GOOGLE_SHEETS_API_KEY=your_google_sheets_api_key

# Компания
COMPANY_NAME=Яскравий друк
PORTFOLIO_LINK=https://t.me/druk_portfolio

# Разработка
DEBUG=False
LOG_LEVEL=INFO
```

## 🏃‍♂️ Запуск

```bash
# Запуск бота
make run

# Запуск в режиме разработки
make dev-run

# Или напрямую
python main.py
```

## 🧪 Тестирование

```bash
# Запуск всех тестов
make test

# Запуск с покрытием
pytest tests/ -v --cov=. --cov-report=html

# Запуск конкретного теста
pytest tests/test_template_manager.py -v
```

## 🔍 Линтинг и форматирование

```bash
# Проверка кода
make lint

# Форматирование кода
make format

# Проверка типов
make typecheck

# Все проверки
make check
```

## 🔒 Безопасность

```bash
# Проверка безопасности
make security

# Проверка уязвимостей
safety check

# Проверка кода на потенциальные проблемы
bandit -r .
```

## 📁 Структура проекта

```
Bot-answers/
├── .github/workflows/     # GitHub Actions
├── data/                  # CSV файлы с шаблонами
├── tests/                 # Тесты
├── venv/                  # Виртуальное окружение
├── bot_api.py            # API для управления ботом
├── bot_factory.py        # Фабрика создания бота
├── bot_lifecycle.py      # Управление жизненным циклом
├── config.py             # Конфигурация
├── error_handler.py      # Обработка ошибок
├── exceptions.py         # Кастомные исключения
├── handlers.py           # Обработчики сообщений
├── keyboards.py          # Клавиатуры
├── main.py               # Точка входа
├── models.py             # Модели данных
├── stats.py              # Статистика
├── template_manager.py   # Менеджер шаблонов
├── validation.py         # Валидация данных
├── pyproject.toml        # Конфигурация проекта
├── requirements.txt      # Зависимости
└── Makefile             # Команды для разработки
```

## 🎯 Основные команды бота

- `/start` - Начать работу с ботом
- `/reload` - Перезагрузить шаблоны из Google Sheets (админ)
- `/stats` - Статистика использования (админ)
- `/health` - Проверка состояния системы (админ)
- `/help` - Помощь

## 📊 Мониторинг

Бот включает систему мониторинга с:
- Отслеживанием ошибок
- Статистикой использования
- Health checks
- Логированием

## 🔧 Разработка

### Стиль кода

Проект использует современные стандарты Python:
- **Black** для форматирования (длина строки: 88 символов)
- **isort** для сортировки импортов
- **flake8** для проверки кода
- **mypy** для проверки типов

### Pre-commit hooks

Автоматические проверки при коммите:
```bash
# Установка hooks
pre-commit install

# Запуск вручную
pre-commit run --all-files
```

### CI/CD

GitHub Actions автоматически:
- Запускает тесты на Python 3.9-3.12
- Проверяет качество кода
- Выполняет security scan
- Собирает пакет
- Деплоит на staging

## 🐛 Отладка

```bash
# Логи бота
tail -f bot.log

# Проверка здоровья системы
python -c "from bot_api import BotAPI; print(BotAPI().get_health_status())"

# Тестирование шаблонов
python -c "from template_manager import TemplateManager; tm = TemplateManager(); print(len(tm.templates))"
```

## 📝 Логи

Система логирования настроена на:
- Ротацию логов
- Структурированный вывод
- Различные уровни (INFO, WARNING, ERROR)
- Сохранение в файл `bot.log`

## 🤝 Вклад в проект

1. Форк проекта
2. Создание ветки для новой функции
3. Коммит изменений
4. Пуш в ветку
5. Создание Pull Request

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 🆘 Поддержка

- Создайте issue в GitHub
- Проверьте документацию
- Просмотрите логи в `bot.log`

## 🏆 Команда

- **Основной разработчик**: [Aleksieiev Valentyn]
- **Дизайн**: [Aleksieiev Valentyn]
- **Тестирование**: [Aleksieiev Valentyn]

---

Made with ❤️ for "Яскравий друк"
