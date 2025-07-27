# 📚 Система управления базой знаний

Комплексная система для просмотра, экспорта и переноса базы знаний ChromaDB на production сервер.

## 🎯 Возможности системы

### 📊 Просмотр базы знаний
- **Общий обзор**: статистика по документам, категориям, источникам
- **Поиск**: векторный поиск с показом релевантности
- **Фильтрация**: по категориям и источникам
- **Детальная информация**: ключевые слова, ответы на разных языках

### 📦 Экспорт данных
- **JSON формат**: для разработки и анализа
- **CSV формат**: совместимый с Google Sheets
- **BACKUP формат**: полный пакет для production

### 🚀 Развертывание на production
- **Автоматический импорт**: скрипт с проверкой валидности
- **Пошаговые инструкции**: в каждом бэкапе
- **Проверка целостности**: валидация данных

---

## 📱 Команды Telegram бота

### Для администраторов:

#### `/browse_kb` - Обзор базы знаний
```
📚 ОБЗОР БАЗЫ ЗНАНИЙ

📊 Общая статистика:
• Всего документов: 84
• Коллекция: bot_knowledge_base
• Обновлено: 2025-01-23 15:30

🗂 По категориям:
• визитки: 20 документов
• футболки: 18 документов
• листовки: 15 документов
• наклейки: 16 документов
• блокноты: 15 документов

🔗 По источникам:
• CSV файлы: 80
• Админские исправления: 3
• Админские добавления: 1

🌐 По языкам:
• Украинский: 84
• Русский: 84
```

#### `/search_kb [запрос]` - Поиск в базе знаний
```bash
/search_kb ламинированные визитки цена
```

**Результат:**
```
🔍 РЕЗУЛЬТАТЫ ПОИСКА
Запрос: «ламинированные визитки цена»
Найдено: 5 результатов

1. визитки (92% релевантность)
🔑 Ключевые слова: визитки, ламинация, цена, качество
🇺🇦 Украинский: Ламіновані візитки від 60 грн за 100 шт...
🇷🇺 Русский: Ламинированные визитки от 60 грн за 100 шт...
📄 Источник: csv
```

#### `/export_kb [формат]` - Экспорт базы знаний
```bash
# Для разработки
/export_kb json

# Для Google Sheets
/export_kb csv

# Для production
/export_kb backup
```

**Пример результата backup:**
```
✅ ЭКСПОРТ ЗАВЕРШЕН

📁 Формат: BACKUP
📄 Файл: knowledge_base_backup_20250123_153045.zip
📊 Записей: 84
💾 Размер: 2.34 MB
📦 Включает: JSON, CSV, Metadata, Instructions

🚀 Для развертывания на production:
1. Скачайте файл: knowledge_base_backup_20250123_153045.zip
2. Распакуйте на production сервере
3. Следуйте инструкциям в DEPLOYMENT_INSTRUCTIONS.md

💡 Бэкап содержит все необходимое для переноса базы знаний!
```

---

## 🛠 Развертывание на production

### Автоматический способ (рекомендуется):

1. **Скачайте бэкап** с development сервера
2. **Загрузите на production** сервер
3. **Запустите импорт**:
```bash
# Проверка бэкапа
python import_knowledge_base.py --backup-dir knowledge_base_backup_20250123.zip --verify-only

# Импорт с подтверждением
python import_knowledge_base.py --backup-dir knowledge_base_backup_20250123.zip

# Принудительный импорт (заменит существующую базу)
python import_knowledge_base.py --backup-dir knowledge_base_backup_20250123.zip --force
```

### Ручной способ:

1. **Через Google Sheets:**
   - Загрузите `knowledge_base.csv` в Google Sheets
   - Настройте существующую интеграцию
   - Выполните `/reload` в боте

2. **Прямой импорт в ChromaDB:**
```python
from src.admin.knowledge_base_manager import knowledge_base_manager

# Импорт из JSON
result = knowledge_base_manager.import_from_backup('exports/knowledge_base_export.json')

# Импорт из ZIP
result = knowledge_base_manager.import_from_backup('exports/backup.zip')
```

---

## 📋 Структура бэкапа

### Содержимое ZIP архива:
```
knowledge_base_backup_20250123/
├── knowledge_base.json          # Основные данные
├── knowledge_base.csv           # CSV для Google Sheets
├── backup_info.json             # Метаданные бэкапа
└── DEPLOYMENT_INSTRUCTIONS.md   # Инструкции по развертыванию
```

### Формат данных:

**knowledge_base.json:**
```json
[
  {
    "id": "item_1",
    "category": "визитки",
    "subcategory": "стандартные",
    "button_text": "Визитки - цены и сроки",
    "keywords": "визитки, цена, ламинация, качество",
    "answer_ukr": "Візитки від 45 грн за 100 шт...",
    "answer_rus": "Визитки от 45 грн за 100 шт...",
    "sort_order": "1",
    "source": "csv",
    "created_at": "2025-01-23T15:30:45"
  }
]
```

**backup_info.json:**
```json
{
  "created_at": "20250123_153045",
  "total_items": 84,
  "categories": {
    "визитки": 20,
    "футболки": 18,
    "листовки": 15,
    "наклейки": 16,
    "блокноты": 15
  },
  "sources": {
    "csv": 80,
    "admin_correction": 3,
    "admin_addition": 1
  },
  "backup_version": "1.0",
  "compatible_with": ["ChromaDB", "Google Sheets", "CSV import"]
}
```

---

## 🔧 API для разработчиков

### KnowledgeBaseManager

```python
from src.admin.knowledge_base_manager import knowledge_base_manager

# Получить обзор базы знаний
overview = knowledge_base_manager.get_knowledge_base_overview()

# Поиск в базе знаний
results = knowledge_base_manager.search_knowledge_base("визитки цена", limit=10)

# Просмотр с фильтрацией
items = knowledge_base_manager.browse_knowledge_base(
    category="визитки",
    source="csv",
    limit=20
)

# Экспорт
export_result = knowledge_base_manager.export_knowledge_base(
    export_format="backup",
    include_admin_additions=True
)

# Импорт
import_result = knowledge_base_manager.import_from_backup("path/to/backup.zip")
```

---

## ✅ Проверка после развертывания

1. **Команды бота:**
   - `/stats` - общая статистика
   - `/browse_kb` - проверка содержимого
   - `/analytics` - работа AI системы

2. **Тестирование AI:**
   - Включите AI режим в боте
   - Задайте тестовые вопросы
   - Проверьте релевантность ответов

3. **Логи:**
   - Проверьте логи на ошибки
   - Убедитесь в корректной инициализации ChromaDB

---

## 🚨 Устранение неполадок

### Частые проблемы:

1. **"База знаний не инициализирована"**
   - Проверьте установку ChromaDB: `pip install chromadb`
   - Убедитесь в корректности путей к данным

2. **"Коллекция не существует"**
   - Выполните полную переинициализацию: `/reload`
   - Проверьте права доступа к файлам

3. **"Импорт завершился с ошибками"**
   - Проверьте валидность бэкапа: `--verify-only`
   - Убедитесь в совместимости версий

4. **"Низкая релевантность поиска"**
   - Проверьте ключевые слова в базе знаний
   - Выполните `/search_kb` для диагностики

### Логи для анализа:
```bash
# Логи импорта
tail -f logs/import.log

# Логи ChromaDB
tail -f logs/chromadb.log

# Общие логи бота
tail -f logs/bot.log
```

---

## 📈 Мониторинг и оптимизация

### Регулярные задачи:

1. **Еженедельно:**
   - Создавайте бэкапы: `/export_kb backup`
   - Проверяйте аналитику: `/analytics`
   - Анализируйте пробелы в знаниях: `/suggestions`

2. **После изменений:**
   - Тестируйте поиск: `/search_kb`
   - Проверяйте AI ответы в реальном режиме
   - Обновляйте ключевые слова при необходимости

3. **Production deploy:**
   - Создайте полный бэкап перед обновлением
   - Тестируйте на staging окружении
   - Следуйте инструкциям в DEPLOYMENT_INSTRUCTIONS.md

---

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи системы
2. Выполните диагностические команды (`/browse_kb`, `/stats`)
3. Создайте issue с подробным описанием проблемы
4. Приложите релевантные логи и конфигурацию

**Система управления базой знаний готова к production использованию!** 🚀
