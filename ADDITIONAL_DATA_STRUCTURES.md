# Структуры данных для дополнительного контекста

Этот документ описывает рекомендуемые структуры данных для добавления контекста, который не хранится в основных Google Sheets таблицах.

## 1. Файловая структура для дополнительного контекста

### 1.1 JSON файлы для специализированного контекста

```json
{
  "version": "1.0",
  "last_updated": "2024-01-15T10:30:00Z",
  "source": "admin_manual",
  "contexts": [
    {
      "id": "faq_001",
      "category": "часто_задаваемые_вопросы",
      "subcategory": "оплата",
      "priority": "high",
      "keywords": ["оплата", "платеж", "банковская карта", "безналичный расчет"],
      "question_ukr": "Как можно оплатить заказ?",
      "question_rus": "Как можно оплатить заказ?",
      "answer_ukr": "Ви можете оплатити замовлення готівкою при отриманні або безготівково...",
      "answer_rus": "Вы можете оплатить заказ наличными при получении или безналично...",
      "tags": ["payment", "cash", "card"],
      "created_by": "admin",
      "created_at": "2024-01-15T10:30:00Z",
      "status": "active"
    }
  ]
}
```

### 1.2 Структура директорий

```
data/
├── additional_context/
│   ├── faq/
│   │   ├── payment_faq.json
│   │   ├── delivery_faq.json
│   │   └── general_faq.json
│   ├── policies/
│   │   ├── return_policy.json
│   │   ├── privacy_policy.json
│   │   └── terms_of_service.json
│   ├── seasonal/
│   │   ├── christmas_2024.json
│   │   ├── valentine_2024.json
│   │   └── summer_promotions.json
│   └── technical/
│       ├── troubleshooting.json
│       ├── system_messages.json
│       └── error_responses.json
```

## 2. База данных SQLite для сложного контекста

### 2.1 Схема таблиц

```sql
-- Основная таблица контекста
CREATE TABLE additional_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_id TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    priority INTEGER DEFAULT 5, -- 1-10, где 1 самый высокий приоритет
    source TEXT DEFAULT 'manual',
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    updated_by TEXT
);

-- Ключевые слова
CREATE TABLE context_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    language TEXT DEFAULT 'both',
    FOREIGN KEY (context_id) REFERENCES additional_context(context_id)
);

-- Контент на разных языках
CREATE TABLE context_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_id TEXT NOT NULL,
    language TEXT NOT NULL, -- 'ukr', 'rus'
    field_type TEXT NOT NULL, -- 'question', 'answer', 'description'
    content TEXT NOT NULL,
    FOREIGN KEY (context_id) REFERENCES additional_context(context_id)
);

-- Метаданные и теги
CREATE TABLE context_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_id TEXT NOT NULL,
    meta_key TEXT NOT NULL,
    meta_value TEXT,
    FOREIGN KEY (context_id) REFERENCES additional_context(context_id)
);

-- История изменений
CREATE TABLE context_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_id TEXT NOT NULL,
    action TEXT NOT NULL, -- 'created', 'updated', 'deleted'
    old_data TEXT, -- JSON
    new_data TEXT, -- JSON
    changed_by TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (context_id) REFERENCES additional_context(context_id)
);
```

### 2.2 Индексы для оптимизации

```sql
CREATE INDEX idx_context_category ON additional_context(category);
CREATE INDEX idx_context_status ON additional_context(status);
CREATE INDEX idx_context_priority ON additional_context(priority);
CREATE INDEX idx_keywords_context ON context_keywords(context_id);
CREATE INDEX idx_keywords_keyword ON context_keywords(keyword);
CREATE INDEX idx_content_context ON context_content(context_id);
CREATE INDEX idx_content_language ON context_content(language);
```

## 3. Интеграция с системой умного обновления

### 3.1 Класс для работы с дополнительным контекстом

```python
from typing import Dict, List, Optional
import json
import sqlite3
import logging
from datetime import datetime

class AdditionalContextManager:
    """Менеджер дополнительного контекста"""

    def __init__(self, db_path: str = "data/additional_context.db"):
        self.db_path = db_path
        self.json_context_dir = "data/additional_context"
        self._init_database()

    def add_json_context(self, file_path: str) -> Dict:
        """Добавляет контекст из JSON файла"""
        pass

    def add_database_context(self, context_data: Dict) -> str:
        """Добавляет контекст в SQLite базу"""
        pass

    def get_all_contexts(self) -> List[Dict]:
        """Получает все дополнительные контексты"""
        pass

    def search_contexts(self, query: str, language: str = "ukr") -> List[Dict]:
        """Поиск по дополнительным контекстам"""
        pass

    def sync_with_vector_db(self):
        """Синхронизирует дополнительный контекст с векторной базой"""
        pass
```

## 4. Рекомендуемые типы дополнительного контекста

### 4.1 Часто задаваемые вопросы (FAQ)
- **Источник**: Администраторы, аналитика запросов
- **Формат**: JSON файлы
- **Обновление**: По мере необходимости
- **Приоритет**: Высокий

### 4.2 Сезонные акции и предложения
- **Источник**: Маркетинговый отдел
- **Формат**: JSON файлы с временными метками
- **Обновление**: По календарю акций
- **Приоритет**: Средний (высокий во время акций)

### 4.3 Техническая документация
- **Источник**: Техническая поддержка
- **Формат**: SQLite база данных
- **Обновление**: При изменении процедур
- **Приоритет**: Высокий для технических запросов

### 4.4 Политики и правила
- **Источник**: Юридический отдел
- **Формат**: JSON файлы с версионированием
- **Обновление**: При изменении законодательства
- **Приоритет**: Высокий

### 4.5 Персонализированные ответы
- **Источник**: Автоматическое обучение
- **Формат**: SQLite база данных
- **Обновление**: Постоянно
- **Приоритет**: Средний

## 5. Интеграция с основной системой

### 5.1 Модификация SmartKnowledgeUpdater

```python
def include_additional_contexts(self, contexts: List[Dict]) -> None:
    """Включает дополнительные контексты в процесс обновления"""
    for context in contexts:
        # Создаем документ для ChromaDB
        doc = self._create_additional_context_document(context)
        # Добавляем в векторную базу с специальным источником
        self._add_context_to_vector_db(doc, source="additional_context")

def _create_additional_context_document(self, context: Dict) -> Dict:
    """Создает документ из дополнительного контекста"""
    return {
        "id": f"additional_{context['context_id']}",
        "text": self._prepare_context_text(context),
        "metadata": {
            "source": "additional_context",
            "category": context.get("category"),
            "subcategory": context.get("subcategory"),
            "priority": context.get("priority", 5),
            "context_type": context.get("context_type", "manual")
        }
    }
```

### 5.2 Приоритизация результатов поиска

```python
def _prioritize_search_results(self, results: List[Dict]) -> List[Dict]:
    """Приоритизирует результаты с учетом дополнительного контекста"""
    for result in results:
        source = result.get("metadata", {}).get("source", "")
        priority = result.get("metadata", {}).get("priority", 5)

        # Повышаем релевантность для важного дополнительного контекста
        if source == "additional_context" and priority <= 3:
            result["relevance_score"] += 0.2

        # Сезонные акции получают бонус в определенное время
        if self._is_seasonal_context_relevant(result):
            result["relevance_score"] += 0.15

    return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
```

## 6. Рекомендации по использованию

### 6.1 Выбор формата данных

- **JSON файлы** - для статического контекста, который редко изменяется
- **SQLite база** - для динамического контекста с частыми обновлениями
- **Гибридный подход** - JSON для конфигурации, SQLite для данных

### 6.2 Стратегия обновления

1. **Инкрементальное обновление** для часто изменяющегося контекста
2. **Полное обновление** при изменении структуры данных
3. **Версионирование** для отслеживания изменений
4. **Автоматическая валидация** перед добавлением в векторную базу

### 6.3 Мониторинг и аналитика

- Отслеживание использования дополнительного контекста
- Анализ эффективности различных типов контекста
- Автоматическое выявление устаревшего контекста
- Метрики качества ответов с дополнительным контекстом

## 7. Пример интеграции

```python
# Использование дополнительного контекста
additional_context_manager = AdditionalContextManager()

# Загружаем JSON контексты
faq_contexts = additional_context_manager.load_json_contexts("data/additional_context/faq/")

# Добавляем в базу знаний
for context in faq_contexts:
    smart_updater.add_additional_context(context)

# Выполняем синхронизацию
result = knowledge_sync_manager.sync_with_additional_contexts()
```

Эта структура обеспечивает гибкость в добавлении различных типов контекста, сохраняя при этом совместимость с существующей системой умного обновления.
