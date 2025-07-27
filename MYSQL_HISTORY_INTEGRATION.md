# MySQL интеграция для истории запросов в Telegram боте

## Текущее состояние системы

### 📊 **Что у вас есть:**

1. **SQLite база для аналитики** (`src/analytics/models.py`)
   - Таблица `user_queries` - запросы пользователей
   - Таблица `feedback_entries` - обратная связь
   - Таблица `knowledge_gaps` - пробелы в знаниях

2. **Асинхронная архитектура**
   - Все обработчики используют `async/await`
   - aiogram 3.x с асинхронным подходом

3. **JSON система для диалогов** (`src/ai/conversation_memory.py`)
   - Хранение полных диалогов в файлах
   - Синхронные операции

### 🚫 **Что НЕ используется:**

- ❌ MySQL пока не подключен (нет в requirements.txt)
- ❌ Синхронный движок (система полностью асинхронная)

## Стратегия интеграции MySQL

### 🎯 **Вариант 1: Расширение существующей SQLite базы (РЕКОМЕНДУЕТСЯ)**

**Плюсы:**
- Быстрая реализация (1-2 дня)
- Использует существующую инфраструктуру
- SQLite отлично подходит для истории запросов
- Нет дополнительных зависимостей

**Реализация:**

```python
# Добавляем в src/analytics/models.py новую таблицу

def _create_tables(self):
    # ... существующие таблицы ...

    # Новая таблица для истории диалогов
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message_type VARCHAR(20) NOT NULL,  -- 'user' или 'assistant'
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

            -- Метаданные для поиска
            category VARCHAR(50),
            has_upselling BOOLEAN DEFAULT FALSE,
            search_type VARCHAR(20),
            relevance_score REAL,

            -- Индексы для быстрого поиска
            INDEX(user_id, timestamp),
            INDEX(category),
            INDEX(has_upselling)
        )
    """)
```

### 🎯 **Вариант 2: Добавление MySQL параллельно**

**Плюсы:**
- Лучшая производительность для больших объемов
- Более мощные возможности фильтрации
- Подготовка к масштабированию

**Минусы:**
- Дополнительная настройка и администрирование
- Нужна миграция данных

## Реализация функционала просмотра истории

### 📱 **Интерфейс в Telegram боте:**

```python
# src/bot/handlers/history.py

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.analytics.models import analytics_db

router = Router()

class HistoryStates(StatesGroup):
    browsing = State()
    filtering = State()

@router.message(Command("history"))
async def cmd_history(message: types.Message, state: FSMContext):
    """Команда просмотра истории запросов"""

    user_id = message.from_user.id

    # Получаем последние запросы пользователя
    recent_queries = analytics_db.get_user_history(user_id, limit=10)

    if not recent_queries:
        await message.answer("📭 У вас пока нет истории запросов")
        return

    # Формируем сообщение с историей
    history_text = "📋 **Ваши последние запросы:**\n\n"

    for i, query in enumerate(recent_queries, 1):
        date_str = query.timestamp.strftime("%d.%m %H:%M")
        query_preview = query.query_text[:50] + "..." if len(query.query_text) > 50 else query.query_text

        history_text += f"{i}. **{date_str}**\n"
        history_text += f"❓ {query_preview}\n"

        if query.is_answered:
            history_text += "✅ Получен ответ\n"
        else:
            history_text += "❌ Без ответа\n"

        history_text += "\n"

    # Кнопки для дополнительных действий
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🔍 Фильтры", callback_data="history:filters"),
            types.InlineKeyboardButton(text="📊 Статистика", callback_data="history:stats")
        ],
        [
            types.InlineKeyboardButton(text="🗑️ Очистить историю", callback_data="history:clear")
        ]
    ])

    await message.answer(history_text, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(HistoryStates.browsing)

@router.callback_query(lambda c: c.data.startswith("history:"))
async def process_history_action(callback: types.CallbackQuery, state: FSMContext):
    """Обработка действий с историей"""

    action = callback.data.split(":")[1]
    user_id = callback.from_user.id

    if action == "filters":
        await show_history_filters(callback, state)
    elif action == "stats":
        await show_user_stats(callback, user_id)
    elif action == "clear":
        await confirm_clear_history(callback, state)

async def show_history_filters(callback: types.CallbackQuery, state: FSMContext):
    """Показывает фильтры для истории"""

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📅 За сегодня", callback_data="filter:today"),
            types.InlineKeyboardButton(text="📅 За неделю", callback_data="filter:week")
        ],
        [
            types.InlineKeyboardButton(text="✅ Отвеченные", callback_data="filter:answered"),
            types.InlineKeyboardButton(text="❌ Без ответа", callback_data="filter:unanswered")
        ],
        [
            types.InlineKeyboardButton(text="🏷️ По категориям", callback_data="filter:category"),
            types.InlineKeyboardButton(text="💰 С upselling", callback_data="filter:upselling")
        ],
        [
            types.InlineKeyboardButton(text="🔙 Назад", callback_data="history:back")
        ]
    ])

    await callback.message.edit_text(
        "🔍 **Выберите фильтр для истории:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data.startswith("filter:"))
async def apply_history_filter(callback: types.CallbackQuery, state: FSMContext):
    """Применяет фильтр к истории"""

    filter_type = callback.data.split(":")[1]
    user_id = callback.from_user.id

    # Получаем отфильтрованные запросы
    filtered_queries = []

    if filter_type == "today":
        filtered_queries = analytics_db.get_user_history_by_date(user_id, days=1)
    elif filter_type == "week":
        filtered_queries = analytics_db.get_user_history_by_date(user_id, days=7)
    elif filter_type == "answered":
        filtered_queries = analytics_db.get_user_history_by_status(user_id, answered=True)
    elif filter_type == "unanswered":
        filtered_queries = analytics_db.get_user_history_by_status(user_id, answered=False)
    elif filter_type == "category":
        await show_category_filter(callback, state)
        return
    elif filter_type == "upselling":
        filtered_queries = analytics_db.get_user_history_with_upselling(user_id)

    # Показываем отфильтрованные результаты
    await show_filtered_history(callback, filtered_queries, filter_type)

async def show_user_stats(callback: types.CallbackQuery, user_id: int):
    """Показывает персональную статистику пользователя"""

    stats = analytics_db.get_user_stats(user_id)

    stats_text = f"""
📊 **Ваша статистика:**

🔢 Всего запросов: {stats['total_queries']}
✅ Получено ответов: {stats['answered_queries']}
❌ Без ответа: {stats['unanswered_queries']}
📈 Процент ответов: {stats['answer_rate']:.1f}%

🎯 Средняя уверенность: {stats['avg_confidence']:.2f}
💰 Запросов с upselling: {stats['upselling_queries']}
🏆 Любимая категория: {stats['top_category']}

📅 Первый запрос: {stats['first_query_date']}
🕒 Последний запрос: {stats['last_query_date']}
"""

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 К истории", callback_data="history:back")]
    ])

    await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode="Markdown")
```

### 🗄️ **Расширение базы данных:**

```python
# Добавляем методы в src/analytics/models.py

class AnalyticsDatabase:
    # ... существующие методы ...

    def get_user_history(self, user_id: int, limit: int = 50) -> List[UserQuery]:
        """Получает историю запросов пользователя"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM user_queries
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()

            return [self._row_to_user_query(row) for row in rows]

    def get_user_history_by_date(self, user_id: int, days: int) -> List[UserQuery]:
        """Получает историю за последние N дней"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM user_queries
                WHERE user_id = ?
                AND timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp DESC
            """.format(days), (user_id,)).fetchall()

            return [self._row_to_user_query(row) for row in rows]

    def get_user_history_by_status(self, user_id: int, answered: bool) -> List[UserQuery]:
        """Получает историю по статусу ответа"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM user_queries
                WHERE user_id = ? AND is_answered = ?
                ORDER BY timestamp DESC
            """, (user_id, answered)).fetchall()

            return [self._row_to_user_query(row) for row in rows]

    def get_user_history_with_upselling(self, user_id: int) -> List[UserQuery]:
        """Получает запросы с upselling предложениями"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM user_queries
                WHERE user_id = ?
                AND (ai_response LIKE '%✨%' OR ai_response LIKE '%Додаткові можливості%')
                ORDER BY timestamp DESC
            """, (user_id,)).fetchall()

            return [self._row_to_user_query(row) for row in rows]

    def get_user_stats(self, user_id: int) -> Dict:
        """Получает персональную статистику пользователя"""
        with self._get_connection() as conn:
            stats = {}

            # Основные метрики
            total = conn.execute("SELECT COUNT(*) as count FROM user_queries WHERE user_id = ?", (user_id,)).fetchone()
            answered = conn.execute("SELECT COUNT(*) as count FROM user_queries WHERE user_id = ? AND is_answered = TRUE", (user_id,)).fetchone()

            stats['total_queries'] = total['count']
            stats['answered_queries'] = answered['count']
            stats['unanswered_queries'] = total['count'] - answered['count']
            stats['answer_rate'] = (answered['count'] / total['count'] * 100) if total['count'] > 0 else 0

            # Средняя уверенность
            avg_conf = conn.execute("SELECT AVG(confidence) as avg FROM user_queries WHERE user_id = ? AND confidence > 0", (user_id,)).fetchone()
            stats['avg_confidence'] = avg_conf['avg'] or 0

            # Upselling запросы
            upselling = conn.execute("""
                SELECT COUNT(*) as count FROM user_queries
                WHERE user_id = ? AND (ai_response LIKE '%✨%' OR ai_response LIKE '%Додаткові можливості%')
            """, (user_id,)).fetchone()
            stats['upselling_queries'] = upselling['count']

            # Даты
            dates = conn.execute("""
                SELECT MIN(timestamp) as first, MAX(timestamp) as last
                FROM user_queries WHERE user_id = ?
            """, (user_id,)).fetchone()

            stats['first_query_date'] = dates['first'] or "Нет данных"
            stats['last_query_date'] = dates['last'] or "Нет данных"

            # Топ категория (если есть поле category)
            stats['top_category'] = "Общие вопросы"  # Заглушка

            return stats
```

## Оценка затрат на реализацию

### ⏱️ **Временные затраты:**

| Задача | Время | Сложность |
|--------|-------|-----------|
| **Расширение SQLite базы** | 4-6 часов | Низкая |
| **Telegram интерфейс** | 8-12 часов | Средняя |
| **Система фильтров** | 6-8 часов | Средняя |
| **Тестирование** | 4-6 часов | Низкая |
| **Документация** | 2-3 часа | Низкая |
| **ИТОГО** | **24-35 часов** | **2-3 дня** |

### 💰 **Ресурсные затраты:**

| Ресурс | SQLite (рекомендуется) | MySQL |
|--------|----------------------|-------|
| **Настройка** | 0 часов | 2-4 часа |
| **Зависимости** | Уже есть | +aiomysql |
| **Администрирование** | Минимальное | Требуется |
| **Производительность** | До 10К запросов/день | Безлимит |

## Рекомендации

### 🎯 **Рекомендуемая стратегия:**

1. **Этап 1 (сейчас):** Расширить SQLite базу
   - Быстрая реализация за 2-3 дня
   - Использует существующую инфраструктуру
   - Покрывает 95% потребностей

2. **Этап 2 (при росте):** Добавить MySQL
   - Когда SQLite станет узким местом
   - Для продвинутой аналитики
   - При > 50К пользователей

### 🚀 **Преимущества SQLite для истории:**

✅ **Отлично подходит потому что:**
- Полнотекстовый поиск встроен
- Быстрые запросы для одного пользователя
- JSON поля для метаданных
- Транзакции ACID
- Нет дополнительных зависимостей

### 📱 **Функции которые легко реализовать:**

- ✅ История запросов пользователя
- ✅ Фильтрация по дате/статусу/категории
- ✅ Персональная статистика
- ✅ Поиск по тексту запросов
- ✅ Экспорт истории
- ✅ Очистка старых данных

## Выводы

**MySQL НЕ нужен сейчас** - ваша система полностью асинхронная и использует SQLite, который идеально подходит для истории запросов.

**Реализация займет 2-3 дня** работы и даст мощный функционал просмотра истории прямо в Telegram боте.

**SQLite справится** с нагрузкой до 10-50К пользователей в день, после чего можно рассмотреть MySQL.

Хотите, чтобы я реализовал этот функционал на базе существующей SQLite системы?
