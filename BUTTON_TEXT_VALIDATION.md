# 🔘 Валидация button_text - Документация

## 📋 Обзор

Система валидации `button_text` обеспечивает, что только строки с валидным текстом кнопки создают пункты меню в Telegram боте. Строки без валидного `button_text` по-прежнему сохраняются в базе знаний и доступны через поиск и AI-режим.

## 🎯 Логика работы

### ✅ **Валидный button_text** - создается пункт меню + база знаний
- Длина от 2 до 100 символов
- Содержит осмысленный текст
- Исключает служебные значения

### ❌ **Невалидный button_text** - только база знаний
- Пустое значение `""`
- Служебные символы: `-`, `_`, `.`, `...`
- Служебные слова: `todo`, `tbd`, `null`, `none`, `empty`
- Слишком короткий текст (менее 2 символов)
- Слишком длинный текст (более 100 символов)

## 📊 Примеры валидации

### ✅ Валидные значения:
```csv
category;subcategory;button_text;keywords;answer_ukr;answer_rus;sort_order
визитки;price;💰 Цена визиток;цена,стоимость;Ответ укр;Ответ рус;1
визитки;sizes;📏 Размеры визиток;размер,формат;Ответ укр;Ответ рус;2
визитки;material;📄 Материалы;материал,бумага;Ответ укр;Ответ рус;3
```

### ❌ Невалидные значения:
```csv
category;subcategory;button_text;keywords;answer_ukr;answer_rus;sort_order
визитки;empty;;покрытие,ламинат;Ответ укр;Ответ рус;4
визитки;dash;-;качество,печать;Ответ укр;Ответ рус;5
визитки;underscore;_;доставка,время;Ответ укр;Ответ рус;6
визитки;todo;TODO;макет,дизайн;Ответ укр;Ответ рус;7
визитки;short;x;срок,готовность;Ответ укр;Ответ рус;8
```

## 🔧 Техническая реализация

### Метод валидации:
```python
def _is_valid_button_text(self, button_text: str) -> bool:
    """Проверяет, валиден ли button_text для создания пункта меню"""
    if not button_text:
        return False

    # Минимальная длина - 2 символа
    if len(button_text) < 2:
        return False

    # Максимальная длина - 100 символов (лимит Telegram)
    if len(button_text) > 100:
        return False

    # Исключаем очевидно невалидные значения
    invalid_values = ["-", "_", ".", "...", "тbd", "todo", "null", "none", "empty"]
    if button_text.lower() in invalid_values:
        return False

    return True
```

### Новое поле в модели Template:
```python
@dataclass
class Template:
    category: str
    subcategory: str
    button_text: str
    keywords: List[str]
    answer_ukr: str
    answer_rus: str
    sort_order: int
    has_menu_button: bool = True  # Новое поле
```

### Фильтрация в клавиатуре:
```python
def create_category_menu_keyboard(category: str, user_id: int, template_manager):
    builder = InlineKeyboardBuilder()

    if category in template_manager.templates:
        templates = template_manager.templates[category]

        # Только шаблоны с валидным button_text
        for template in templates:
            if getattr(template, 'has_menu_button', True):
                builder.row(
                    InlineKeyboardButton(
                        text=template.button_text,
                        callback_data=f"template_{category}_{template.subcategory}",
                    )
                )
```

## 📈 Новые методы TemplateManager

### 1. get_menu_templates() - только для меню
```python
menu_templates = template_manager.get_menu_templates("визитки")
# Возвращает только шаблоны с has_menu_button=True
```

### 2. get_knowledge_base_templates() - все для поиска
```python
all_templates = template_manager.get_knowledge_base_templates("визитки")
# Возвращает все шаблоны (включая без button_text)
```

### 3. get_category_templates() - все как раньше
```python
all_templates = template_manager.get_category_templates("визитки")
# Возвращает все шаблоны категории
```

## 📊 Логирование и статистика

### При загрузке шаблонов:
```
INFO - Всего загружено шаблонов: 25
INFO -   • В меню: 20
INFO -   • Только в базе знаний: 5
INFO - Шаблоны без button_text будут доступны через поиск и AI-режим
```

### Детальное логирование:
```
INFO - Шаблон invalid1 добавлен только в базу знаний (нет валидного button_text)
DEBUG -   button_text был: ''
```

## 🧪 Тестирование

### Запуск тестов:
```bash
python test_button_text_validation.py
```

### Ожидаемый результат:
```
🧪 Тестирование валидации button_text...

📊 Результаты загрузки:
• Всего шаблонов: 12
• В меню: 4
• В базе знаний: 12
• Только в базе знаний: 8

✅ Шаблоны в меню:
  • valid1: '💰 Цена визиток'
  • valid2: '📏 Размеры визиток'
  • edge1: 'AB'
  • edge2: 'AAAA...' (100 символов)

🔍 Шаблоны только в базе знаний:
  • invalid1: '' (keywords: материал, бумага)
  • invalid2: '-' (keywords: покрытие, ламинат)
  • invalid3: '_' (keywords: печать, качество)
  • invalid4: '.' (keywords: доставка, время)
  • invalid5: 'todo' (keywords: макет, дизайн)
  • invalid6: 'TBD' (keywords: срок, готовность)
  • invalid7: 'x' (keywords: логотип, брендинг)
  • edge3: 'AAAA...' (101 символ - превышение лимита)
```

## 🔄 Миграция существующих данных

### Автоматическая совместимость:
- Существующие шаблоны получают `has_menu_button=True` по умолчанию
- Старые CSV файлы продолжают работать
- Новая валидация применяется только при перезагрузке

### Рекомендации по обновлению Google Sheets:
1. **Заполните пустые button_text** осмысленными названиями
2. **Замените служебные символы** на понятный текст
3. **Проверьте длину** кнопок (2-100 символов)
4. **Используйте эмодзи** для улучшения UX

## 💡 Практические примеры

### Хорошие button_text:
```
💰 Цена визиток
📏 Стандартные размеры
🎨 Дизайн и макеты
📦 Материалы и покрытия
🚚 Доставка и сроки
❓ Частые вопросы
```

### Плохие button_text (попадут только в базу знаний):
```
-
_
.
TODO
TBD
null
x
(пустое значение)
```

## 🎯 Преимущества системы

### ✅ Для пользователей:
- Чистые и понятные меню
- Нет пустых или непонятных кнопок
- Все данные доступны через поиск

### ✅ Для администраторов:
- Гибкость в управлении контентом
- Возможность постепенного наполнения меню
- Детальная статистика загрузки

### ✅ Для разработчиков:
- Обратная совместимость
- Четкое разделение меню и базы знаний
- Логирование и отладка

## 🔧 Настройка валидации

### Изменение списка невалидных значений:
```python
# В методе _is_valid_button_text
invalid_values = ["-", "_", ".", "...", "тbd", "todo", "null", "none", "empty"]
# Добавьте или уберите значения по необходимости
```

### Изменение ограничений длины:
```python
# Минимальная длина
if len(button_text) < 2:  # Измените на нужное значение

# Максимальная длина (лимит Telegram)
if len(button_text) > 100:  # Не рекомендуется увеличивать
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи загрузки шаблонов
2. Запустите тест валидации
3. Убедитесь, что CSV файлы имеют правильную кодировку UTF-8
4. Проверьте, что все обязательные поля заполнены

**Система готова к использованию!** 🚀
