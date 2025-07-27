# 🤖 Claude Context - Полный контекст приложения

## 📋 КРАТКИЙ ОБЗОР ПРОЕКТА

**Проект:** Telegram бот для типографии "Яскравий друк" с системой менеджеров
**Основная задача:** Автоматические ответы + уведомления менеджеров с прямыми ссылками + SQLite для истории
**Статус:** ✅ ПОЛНОСТЬЮ РЕАЛИЗОВАН
**Сложность:** ВЫСОКАЯ (Enterprise-уровень)

## 🎯 ЧТО БЫЛО ЗАПРОШЕНО ПОЛЬЗОВАТЕЛЕМ

### Исходный запрос (переведен с украинского):
```
"также в эту систему нужно обязательно добавить telegram менеджеров,
которые работают сегодня и активны и которые будут получать уведомление
что клиент ждет ответ и получать прямую ссылку на диалог в телеграм...
это возможно?"

"начинай, также реализуй использование SQLlite из предыдущего моего
запроса для удобного хранение и фильтрации запросов и просмотра
истории запросов и наших ответов"
```

### Ключевые требования:
1. **Telegram менеджеры** - система уведомлений
2. **Прямые ссылки** - `tg://user?id=123456` для быстрого перехода к клиенту
3. **SQLite интеграция** - удобное хранение и фильтрация
4. **История запросов** - просмотр диалогов с фильтрацией
5. **Активные менеджеры** - определение кто работает сегодня

## 📁 СТРУКТУРА РЕАЛИЗОВАННОЙ СИСТЕМЫ

```
/Volumes/work/TG_bots/Bot-answers/
├── src/managers/                           # 🔥 ОСНОВНАЯ СИСТЕМА
│   ├── models.py                          # SQLite база данных (638 строк)
│   ├── notification_system.py             # Уведомления менеджеров (596 строк)
│   ├── admin_panel.py                     # Админка (400+ строк)
│   ├── integration.py                     # Интеграция с ботом (300+ строк)
│   └── main_bot_integration.py            # Пример полной интеграции
├── src/bot/handlers/
│   └── history.py                         # Telegram интерфейс истории (586 строк)
├── PREMIUM_AUTOMATION_STRATEGY.md         # Стратегия автоматизации (756 строк)
├── TELEGRAM_MANAGERS_SYSTEM.md            # Техническая спецификация
└── TELEGRAM_MANAGERS_IMPLEMENTATION.md    # Документация реализации
```

## 🗄️ АРХИТЕКТУРА БАЗЫ ДАННЫХ

### SQLite Schema: `./data/unified_system.db`

```sql
-- 🧑‍💼 МЕНЕДЖЕРЫ
CREATE TABLE managers (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE,     -- Telegram ID менеджера
    name TEXT,                      -- Имя менеджера
    status TEXT,                    -- active/busy/offline/vacation
    work_days TEXT,                 -- Рабочие дни
    work_start/work_end TEXT,       -- Рабочие часы
    active_chats INTEGER,           -- Количество активных чатов
    notifications_enabled BOOLEAN   -- Получать уведомления
);

-- 💬 АКТИВНЫЕ ЧАТЫ (связь клиент-менеджер)
CREATE TABLE active_chats (
    client_telegram_id INTEGER,     -- ID клиента
    manager_telegram_id INTEGER,    -- ID менеджера
    started_at DATETIME,            -- Когда начат чат
    status TEXT,                    -- active/completed
    client_name TEXT,               -- Имя клиента
    initial_query TEXT              -- Первоначальный запрос
);

-- 📝 ИСТОРИЯ ВСЕХ СООБЩЕНИЙ
CREATE TABLE conversation_history (
    user_id INTEGER,                -- ID пользователя
    message_type TEXT,              -- 'user'/'assistant'/'system'
    content TEXT,                   -- Содержимое сообщения
    timestamp DATETIME,             -- Время сообщения
    category TEXT,                  -- Категория (цены/сроки/макеты)
    has_upselling BOOLEAN,          -- Есть ли предложения
    manager_id INTEGER,             -- ID менеджера (если отвечал)
    is_auto_response BOOLEAN,       -- Автоматический ответ
    file_info TEXT                  -- JSON с информацией о файлах
);

-- 📊 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ (для быстрого доступа)
CREATE TABLE user_stats (
    user_id INTEGER PRIMARY KEY,
    total_messages INTEGER,         -- Всего сообщений
    favorite_category TEXT,         -- Любимая категория
    first_message_date DATETIME,    -- Первое сообщение
    last_message_date DATETIME      -- Последнее сообщение
);
```

## 🔔 СИСТЕМА УВЕДОМЛЕНИЙ МЕНЕДЖЕРОВ

### Ключевые особенности:
```python
# 1. ПРЯМЫЕ ССЫЛКИ НА КЛИЕНТОВ
deep_link = f"tg://user?id={client_telegram_id}"

# 2. УМНЫЕ ПРИОРИТЕТЫ
urgency = "high" if message.document else "normal"

# 3. СТАТИСТИКА КЛИЕНТА В УВЕДОМЛЕНИИ
client_stats = db.get_user_stats_summary(client_id)

# 4. CALLBACK ОБРАБОТКА
callback_data = f"manager:take:{client_id}"
```

### Пример уведомления:
```
📞 Новый клиент ждет ответ!

👤 Клиент: Иван Петров
📱 Username: @ivan_petrov
🆔 ID: 123456789

💬 Сообщение:
Сколько стоят визитки на 500 штук?

📊 Статистика клиента:
• Всего сообщений: 5
• Чаще спрашивает о: визитки

[💬 Ответить клиенту] - ссылка tg://user?id=123456789
[✅ Взял в работу] [📊 История клиента]
```

## 📋 ИНТЕРФЕЙС ИСТОРИИ ДИАЛОГОВ

### Команда `/history` предоставляет:
- ✅ Просмотр всех диалогов пользователя
- ✅ Фильтрация по дате (сегодня/неделя/месяц)
- ✅ Фильтрация по типу (вопросы/ответы/автоответы/с upselling)
- ✅ Поиск по содержимому сообщений
- ✅ Детальная статистика пользователя
- ✅ Группировка сообщений по парам вопрос-ответ

## 🎛️ АДМИНСКАЯ ПАНЕЛЬ

### Команды:
- `/admin_managers` - главная админ-панель
- `/manager_start` - активация менеджера
- `/manager_status` - статус и статистика менеджера
- `/system_stats` - системная статистика

### Функции админки:
- ➕ Добавление новых менеджеров
- 📊 Просмотр статистики всех менеджеров
- 🔄 Управление статусами (активен/занят/оффлайн)
- 📋 Мониторинг активных чатов
- 🗂️ Информация о базе данных

## 🔧 ИНТЕГРАЦИЯ С ОСНОВНЫМ БОТОМ

### Главные функции интеграции:
```python
# 1. ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ
from src.managers.integration import setup_manager_system
await setup_manager_system(bot)

# 2. ОБРАБОТКА СООБЩЕНИЙ КЛИЕНТОВ
from src.managers.integration import process_client_message
await process_client_message(message, response_text, metadata)

# 3. СОХРАНЕНИЕ В ИСТОРИЮ
from src.managers.integration import save_conversation_message
await save_conversation_message(user_id, 'user', message.text)

# 4. ПРОВЕРКА ДОСТУПНОСТИ МЕНЕДЖЕРОВ
from src.managers.integration import is_manager_available
if is_manager_available():
    # Менеджеры онлайн
```

### Middleware для автоматического логирования:
```python
class ManagerIntegrationMiddleware:
    async def __call__(self, handler, event, data):
        # Автоматически сохраняет все сообщения в историю
        if event.text:
            await save_conversation_message(...)
        return await handler(event, data)
```

## 🎯 КЛЮЧЕВЫЕ КЛАССЫ И МЕТОДЫ

### 🗄️ UnifiedDatabase (models.py)
```python
class UnifiedDatabase:
    # Менеджеры
    def add_manager(self, manager: Manager) -> int
    def get_active_managers(self) -> List[Manager]
    def get_available_managers_now(self) -> List[Manager]

    # Чаты
    def assign_chat_to_manager(self, client_id, manager_id, info)
    def get_active_chat(self, client_id) -> ActiveChat

    # История
    def save_message(self, message: ConversationMessage) -> int
    def get_user_history(self, user_id, limit=50) -> List
    def search_user_history(self, user_id, search_text) -> List
    def get_user_stats_summary(self, user_id) -> Dict
```

### 🔔 ManagerNotificationSystem (notification_system.py)
```python
class ManagerNotificationSystem:
    async def notify_new_client(self, message, urgency="normal")
    async def notify_file_upload(self, message, file_analysis)
    async def notify_high_priority(self, message, reason)
    async def handle_manager_callback(self, callback)
    async def save_assistant_response(self, user_id, response, metadata)
```

## 🚀 КАК ЗАПУСТИТЬ СИСТЕМУ

### 1. Инициализация в main.py:
```python
from src.managers.integration import setup_manager_system, get_manager_router

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Подключаем систему менеджеров
    await setup_manager_system(bot)
    dp.include_router(get_manager_router())

    await dp.start_polling(bot)
```

### 2. Добавление первого менеджера:
```python
# От админа в боте:
/admin_managers → ➕ Добавить менеджера

# Или программно:
manager = Manager(
    telegram_id=123456789,
    name="Иван Менеджер",
    status=ManagerStatus.ACTIVE
)
unified_db.add_manager(manager)
```

### 3. Интеграция с обработчиками:
```python
@router.message(F.text)
async def handle_message(message: types.Message):
    # Ваша логика ответа
    response = await generate_response(message.text)
    await message.answer(response)

    # Интеграция с менеджерами
    await process_client_message(message, response, {
        'category': 'pricing',
        'confidence': 0.85
    })
```

## 📊 СТАТИСТИКА СИСТЕМЫ

### Реализованные метрики:
- 👥 Общее количество менеджеров
- 🟢 Активных менеджеров сейчас
- 💬 Активных чатов
- 📝 Всего сообщений в истории
- 👤 Уникальных пользователей
- 📈 Статистика по пользователям (сообщения, категории, активность)
- 🔍 Health check системы

## ⚠️ ВАЖНЫЕ ОСОБЕННОСТИ

### 1. Прямые ссылки Telegram:
```python
# Создает ссылку для прямого перехода к пользователю
url = f"tg://user?id={user_telegram_id}"
# При нажатии открывает диалог с пользователем
```

### 2. Умная маршрутизация уведомлений:
```python
# Высокий приоритет: файлы, низкая уверенность, срочные слова
# Обычный приоритет: стандартные вопросы
# Автоматическая балансировка нагрузки между менеджерами
```

### 3. Рабочее время менеджеров:
```python
# Проверка рабочих дней и часов
# Если никого нет - уведомляет всех активных
# Гибкие настройки рабочего времени для каждого менеджера
```

## 🔄 WORKFLOW СИСТЕМЫ

### 1. Клиент отправляет сообщение
### 2. Бот обрабатывает и отвечает
### 3. Система сохраняет в историю (SQLite)
### 4. Определяется приоритет сообщения
### 5. Находятся доступные менеджеры
### 6. Отправляются уведомления с прямыми ссылками
### 7. Менеджер может взять в работу или получить историю клиента
### 8. Все действия логируются в базу данных

## 🎯 ТЕКУЩИЙ СТАТУС

✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО:**
- SQLite база данных с полной схемой
- Система уведомлений менеджеров
- Интерфейс просмотра истории
- Админская панель управления
- Полная интеграция с основным ботом
- Документация и примеры

✅ **ГОТОВО К ПРОДАКШЕНУ:**
- Все модули протестированы
- Обработка ошибок реализована
- Логирование настроено
- Безопасность учтена

## 🔧 ЕСЛИ НУЖНО РАСШИРИТЬ

### Легко добавить:
```python
# Новые типы уведомлений
async def notify_vip_client(self, message): pass

# Новые фильтры истории
async def filter_by_price_range(self, user_id, min_price, max_price): pass

# Интеграции с внешними системами
async def send_to_crm(self, client_data): pass

# Новые команды админки
@router.message(Command("export_data"))
async def export_data(message): pass
```

## 💡 ФИЛОСОФИЯ АРХИТЕКТУРЫ

**Принципы:**
- 🔀 **Модульность** - каждый файл отвечает за одну область
- 🔗 **Слабая связанность** - модули независимы
- 📈 **Масштабируемость** - легко добавлять новый функционал
- 🛡️ **Надежность** - обработка ошибок и логирование
- 📚 **Документированность** - каждая функция описана

**Результат:** Enterprise-уровень система, готовая к расширению и долгосрочному использованию.

---

## 🎯 ДЛЯ CLAUDE: КАК ИСПОЛЬЗОВАТЬ ЭТОТ КОНТЕКСТ

Прочитав этот файл, ты получишь полное понимание:
1. **Что реализовано** - вся система готова
2. **Как это работает** - архитектура и компоненты
3. **Где что лежит** - структура файлов
4. **Как расширять** - точки расширения системы
5. **Ключевые особенности** - прямые ссылки, SQLite, уведомления

## 🔘 ВАЛИДАЦИЯ BUTTON_TEXT (НОВАЯ ФУНКЦИЯ)

### Обновленная логика обработки Google Sheets:
- **Валидный button_text** → создается пункт меню + база знаний
- **Невалидный button_text** → только база знаний (доступно через поиск/AI)

### Критерии валидности:
```python
def _is_valid_button_text(self, button_text: str) -> bool:
    # Длина от 2 до 100 символов
    # Исключает: "", "-", "_", ".", "todo", "tbd", "null", "none", "empty"
    # Все невалидные шаблоны идут только в базу знаний
```

### Новые методы:
```python
template_manager.get_menu_templates(category)  # Только для меню
template_manager.get_knowledge_base_templates()  # Все для поиска
```

### Обновленная модель:
```python
@dataclass
class Template:
    # ... существующие поля
    has_menu_button: bool = True  # Новое поле
```

### Логирование:
```
INFO - Всего загружено шаблонов: 79
INFO -   • В меню: 71
INFO -   • Только в базе знаний: 8
INFO - Шаблоны без button_text будут доступны через поиск и AI-режим
```

**Система готова к использованию и расширению!** 🚀
