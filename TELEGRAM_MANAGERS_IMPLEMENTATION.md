# Система уведомления Telegram менеджеров - Полная реализация

## 🎯 Обзор системы

Реализованная система обеспечивает:

- **Автоматические уведомления менеджеров** о новых клиентах с прямыми ссылками `tg://user?id=123456`
- **Объединенную SQLite базу данных** для управления менеджерами и истории диалогов
- **Telegram интерфейс** для просмотра истории сообщений с фильтрацией
- **Админскую панель** для управления менеджерами
- **Полную интеграцию** с основным ботом

## 📁 Структура проекта

```
src/managers/
├── models.py                    # Объединенная SQLite база данных
├── notification_system.py       # Система уведомлений менеджеров
├── admin_panel.py              # Админская панель управления
├── integration.py              # Интеграция с основным ботом
└── main_bot_integration.py     # Пример полной интеграции

src/bot/handlers/
└── history.py                  # Telegram интерфейс для истории

Документация:
├── PREMIUM_AUTOMATION_STRATEGY.md   # Стратегия автоматизации
├── TELEGRAM_MANAGERS_SYSTEM.md     # Техническая спецификация
└── TELEGRAM_MANAGERS_IMPLEMENTATION.md  # Этот файл
```

## 🗄️ База данных

### Схема SQLite `./data/unified_system.db`

```sql
-- Менеджеры
CREATE TABLE managers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    username TEXT,
    status TEXT DEFAULT 'offline',

    work_days TEXT DEFAULT 'monday,tuesday,wednesday,thursday,friday',
    work_start TEXT DEFAULT '09:00',
    work_end TEXT DEFAULT '18:00',

    total_clients INTEGER DEFAULT 0,
    active_chats INTEGER DEFAULT 0,
    last_activity DATETIME,

    notifications_enabled BOOLEAN DEFAULT TRUE,
    notification_sound BOOLEAN DEFAULT TRUE,
    max_active_chats INTEGER DEFAULT 10
);

-- Активные чаты
CREATE TABLE active_chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_telegram_id INTEGER NOT NULL,
    manager_telegram_id INTEGER NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',

    client_name TEXT,
    client_username TEXT,
    initial_query TEXT
);

-- История сообщений (расширенная)
CREATE TABLE conversation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message_type TEXT NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Метаданные для поиска и анализа
    category TEXT,
    has_upselling BOOLEAN DEFAULT FALSE,
    search_type TEXT,
    relevance_score REAL,
    response_time_ms INTEGER,

    -- Контекст обработки
    manager_id INTEGER,
    is_auto_response BOOLEAN DEFAULT FALSE,
    file_info TEXT -- JSON с информацией о файлах
);

-- Статистика пользователей (для быстрых запросов)
CREATE TABLE user_stats (
    user_id INTEGER PRIMARY KEY,
    first_message_date DATETIME,
    last_message_date DATETIME,
    total_messages INTEGER DEFAULT 0,
    total_responses INTEGER DEFAULT 0,
    avg_response_time_ms REAL,
    favorite_category TEXT,
    has_uploaded_files BOOLEAN DEFAULT FALSE
);
```

## 🔔 Система уведомлений

### Основные возможности

1. **Уведомления о новых клиентах** с адаптивным приоритетом
2. **Обработка файлов макетов** с автоматическим анализом
3. **Высокоприоритетные уведомления** для сложных запросов
4. **Прямые ссылки** `tg://user?id=123456` для быстрого перехода
5. **История клиента** прямо в уведомлении

### Пример уведомления менеджеру

```
📞 Новый клиент ждет ответ!

👤 Клиент: Иван Петров
📱 Username: @ivan_petrov
🆔 ID: 123456789

💬 Сообщение:
Сколько стоят визитки на 500 штук?

🕐 Время: 14:25

📊 Статистика клиента:
• Всего сообщений: 5
• Последнее обращение: 12.03
• Чаще спрашивает о: визитки

⚡ Нажмите "Ответить" для перехода к диалогу

[💬 Ответить клиенту] [✅ Взял в работу]
[📊 История клиента] [🔇 Пауза 1ч]
```

## 📋 Интерфейс истории диалогов

### Команды для пользователей

- `/history` - просмотр истории диалогов
- Фильтрация по дате, типу сообщений, категориям
- Поиск по содержимому сообщений
- Детальная статистика пользователя

### Пример интерфейса

```
📋 Ваша история диалогов

📊 Статистика:
• Всего сообщений: 25
• Ваших вопросов: 12
• Получено ответов: 13
• Предложений с upselling: 3

📝 Последние сообщения:

1. 15.07 14:25
❓ Сколько стоят визитки на 500 штук?
✅ Визитки 500 шт на бумаге 300г/м² - от 250 грн...
💰 С предложениями

2. 14.07 10:30
❓ Можете сделать макет?
✅ Да, наши дизайнеры создадут макет...
👤 Менеджер ID: 987654321

[🔍 Фильтры] [🔎 Поиск]
[📊 Подробная статистика] [📄 Больше записей]
```

## 🎛️ Админская панель

### Команды для администраторов

- `/admin_managers` - главная админ-панель
- Управление менеджерами (добавление, редактирование)
- Просмотр статистики системы
- Мониторинг активных чатов

### Команды для менеджеров

- `/manager_start` - активация менеджера
- `/manager_status` - просмотр статуса и статистики
- Смена статуса через inline-клавиатуру

## 🔧 Интеграция с основным ботом

### Пример подключения

```python
from src.managers.integration import setup_manager_system, get_manager_router
from src.managers.main_bot_integration import initialize_bot_with_managers

async def main():
    # Создаем бота
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Инициализируем систему менеджеров
    if await initialize_bot_with_managers(bot, dp):
        print("✅ Система менеджеров подключена")
    else:
        print("❌ Ошибка подключения системы менеджеров")

    # Запускаем бота
    await dp.start_polling(bot)
```

### Обработка сообщений

```python
from src.managers.integration import process_client_message, save_conversation_message

@router.message(F.text)
async def handle_message(message: types.Message):
    # Ваша логика обработки
    response_text = await generate_ai_response(message.text)

    # Отправляем ответ
    await message.answer(response_text)

    # Интегрируем с системой менеджеров
    await process_client_message(
        message=message,
        response_text=response_text,
        metadata={
            'confidence': 0.85,
            'category': 'pricing',
            'has_upselling': True
        }
    )
```

## 📊 Аналитика и мониторинг

### Системная статистика

```python
from src.managers.integration import get_manager_statistics, health_check

# Получение статистики
stats = await get_manager_statistics()
print(f"Всего менеджеров: {stats['total_managers']}")
print(f"Активных чатов: {stats['active_chats']}")

# Проверка состояния системы
health = await health_check()
print(f"Статус системы: {health['status']}")
```

### Команды мониторинга

- `/system_stats` - системная статистика (для админов)
- `/system_health` - проверка состояния системы

## 🚀 Развертывание

### 1. Настройка конфигурации

```python
# В config.py добавить:
class Config:
    # ID администраторов
    ADMIN_USER_IDS = [123456789, 987654321]

    # Настройки базы данных
    DATABASE_PATH = "./data/unified_system.db"

    # Настройки уведомлений
    NOTIFICATIONS_ENABLED = True
```

### 2. Создание необходимых директорий

```bash
mkdir -p data
mkdir -p logs
```

### 3. Инициализация базы данных

База данных создается автоматически при первом запуске.

### 4. Добавление первого менеджера

```bash
# Запустить бота и выполнить команду от админа:
/admin_managers

# В админ-панели:
➕ Добавить менеджера
```

## 💡 Особенности реализации

### Прямые ссылки на диалоги

```python
# Создание прямой ссылки на клиента
deep_link = f"tg://user?id={client_telegram_id}"

# В клавиатуре уведомления
types.InlineKeyboardButton(
    text="💬 Ответить клиенту",
    url=deep_link
)
```

### Умное определение приоритетов

```python
def _determine_message_urgency(message: types.Message, metadata: Dict) -> str:
    # Высокий приоритет для файлов
    if message.document or message.photo:
        return "high"

    # Низкая уверенность = высокий приоритет
    if metadata.get('confidence', 0) < 0.7:
        return "high"

    # Ключевые слова срочности
    urgent_keywords = ['срочно', 'быстро', 'немедленно']
    if any(word in message.text.lower() for word in urgent_keywords):
        return "high"

    return "normal"
```

### Автоматическая статистика клиентов

```python
# В уведомлении автоматически показывается:
client_stats = self._get_client_brief_stats(client_id)

if client_stats['total_messages'] > 1:
    message += f"\n\n📊 Статистика клиента:"
    message += f"\n• Всего сообщений: {client_stats['total_messages']}"
    message += f"\n• Любимая категория: {client_stats['favorite_category']}"
```

## ⚠️ Важные моменты

### Безопасность

1. **Проверка прав доступа** во всех админских функциях
2. **Валидация данных** при добавлении менеджеров
3. **Логирование** всех важных операций

### Производительность

1. **Индексы БД** для быстрых запросов
2. **Пагинация** в интерфейсах истории
3. **Кэширование** статистики пользователей

### Масштабируемость

1. **Балансировка нагрузки** между менеджерами
2. **Лимиты активных чатов** на менеджера
3. **Гибкие настройки** рабочего времени

## 🔧 Расширение функционала

### Добавление новых типов уведомлений

```python
# В ManagerNotificationSystem
async def notify_vip_client(self, client_message: types.Message):
    # Логика VIP-уведомлений
    pass
```

### Интеграция с внешними системами

```python
# Webhook для CRM
async def send_to_crm(client_info: Dict):
    # Отправка данных в CRM
    pass
```

### Добавление ботов-помощников

```python
# Отдельный бот для менеджеров
manager_bot = Bot(token=MANAGER_BOT_TOKEN)
```

## 📞 Поддержка

Система полностью задокументирована и готова к использованию. Все компоненты протестированы и интегрируются друг с другом.

**Ключевые файлы для изучения:**
1. `src/managers/models.py` - структура базы данных
2. `src/managers/notification_system.py` - логика уведомлений
3. `src/managers/main_bot_integration.py` - пример интеграции
4. `src/bot/handlers/history.py` - интерфейс истории

**Готово к использованию:** ✅
**Протестировано:** ✅
**Задокументировано:** ✅
