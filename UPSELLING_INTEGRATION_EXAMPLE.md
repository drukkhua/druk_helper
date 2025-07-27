# Интеграция системы upselling - Примеры использования

## Структура Google Sheets с ценами

### 📊 **Рекомендуемая структура:**

```csv
category,group,button_text,keywords,answer_ukr,answer_rus,priority,upsell_trigger,base_price,upsell_price,price_suffix
визитки,цена,,цена стоимость сколько,"96 візиток за {base_price} грн на крейдованому папері 350г/м²","96 визиток за {base_price} грн на мелованной бумаге 350г/м²",10,base,158,,
визитки,премиум_материалы,,качество лучше,"✨ Дизайнерський картон 400г/м² - всього +{upsell_price} грн","✨ Дизайнерский картон 400г/м² - всего +{upsell_price} грн",8,price,158,50,к базовой цене
визитки,спецэффекты,,тиснение фольга люкс,"🌟 Тиснення золотою фольгою - від +{upsell_price} грн","🌟 Тиснение золотой фольгой - от +{upsell_price} грн",7,materials,158,120,за спецэффект
визитки,срочное_производство,,быстро срочно завтра,"⚡ Готовність за 8 годин - доплата {upsell_price} грн","⚡ Готовность за 8 часов - доплата {upsell_price} грн",6,time,158,200,за срочность
визитки,большие_тиражи,,тираж много оптом,"💰 1000 шт - всього {base_price} грн (економія 40%)","💰 1000 шт - всего {base_price} грн (экономия 40%)",9,"price,quantity",920,,оптовая цена
листовки,цена,,цена стоимость,"Листівки А4 на крейдованому папері - {base_price} грн за 100 шт","Листовки А4 на мелованной бумаге - {base_price} грн за 100 шт",10,base,180,,
листовки,спецэффекты,,ламинация защита,"✨ Ламінація - +{upsell_price} грн, захистить від вологи","✨ Ламинация - +{upsell_price} грн, защитит от влаги",8,materials,180,40,за ламинацию
```

## Примеры работы системы

### 🎯 **Пример 1: Запрос о цене**

**Запрос пользователя:** "Сколько стоят визитки?"

**Активные триггеры:** `['price']`

**Результат системы:**
```
✅ 96 візиток за 158 грн на крейдованому папері 350г/м² за 1-2 дні

✨ Додаткові можливості:
• 1000 шт - всього 920 грн (економія 40%)
• Дизайнерський картон 400г/м² - всього +50 грн
```

**Логика выбора:**
- Базовый ответ (priority 10, trigger "base")
- Большие тиражи (priority 9, trigger "price,quantity") - высокий приоритет + совпадение триггера
- Премиум материалы (priority 8, trigger "price") - совпадение триггера

### 🎯 **Пример 2: Запрос о качестве материалов**

**Запрос пользователя:** "Какая бумага используется для визиток? Нужно качественно"

**Активные триггеры:** `['materials', 'quality', 'quality_focused']`

**Результат системы:**
```
✅ 96 візиток за 158 грн на крейдованому папері 350г/м² за 1-2 дні

✨ Додаткові можливості:
• Тиснення золотою фольгою - від +120 грн
• Дизайнерський картон 400г/м² - всього +50 грн
```

**Логика выбора:**
- Спецэффекты (priority 7, trigger "materials") + бонус за "quality_focused"
- Премиум материалы (priority 8, trigger "price") - подходит для качества

### 🎯 **Пример 3: Срочный заказ**

**Запрос пользователя:** "Можно ли сделать визитки к завтрашнему утру? Очень срочно нужно"

**Активные триггеры:** `['time']`

**Результат системы:**
```
✅ 96 візиток за 158 грн на крейдованому папері 350г/м² за 1-2 дні

✨ Додаткові можливості:
• Готовність за 8 годин - доплата 200 грн
```

**Логика выбора:**
- Срочное производство (priority 6, trigger "time") - прямое совпадение триггера

## Интеграция с существующим кодом

### 🔧 **Модификация обработчика сообщений:**

```python
# В src/bot/handlers/main.py

from src.ai.upselling_engine import upsell_engine

async def handle_message(message: Message):
    """Обработчик сообщений с поддержкой upselling"""

    user_text = message.text
    user_context = {
        'user_id': message.from_user.id,
        'is_first_time': await is_first_time_user(message.from_user.id),
        'previous_orders': await get_user_order_count(message.from_user.id)
    }

    # Используем upselling движок вместо обычного поиска
    search_results = upsell_engine.search_with_upselling(
        query=user_text,
        user_context=user_context,
        language="ukr",
        max_upsell=2
    )

    if search_results:
        # Форматируем ответ с upselling предложениями
        formatted_answer = upsell_engine.format_final_answer(search_results, "ukr")

        # Получаем аналитику для мониторинга
        analytics = upsell_engine.get_upselling_analytics(search_results)
        logger.info(f"Upselling analytics: {analytics}")

        await message.answer(formatted_answer)
    else:
        await message.answer("Извините, не могу найти подходящий ответ.")
```

### 🔧 **Модификация знаний с ценами:**

```python
# Обновление src/ai/knowledge_base.py для поддержки цен

def load_csv_data(self) -> List[Dict]:
    """Загружает данные из CSV с поддержкой полей цен"""

    # ... существующий код ...

    data_item = {
        "id": unique_id,
        "category": category,
        "subcategory": row.get("group", ""),
        "button_text": row.get("button_text", ""),
        "keywords": row.get("keywords", ""),
        "answer_ukr": row.get("answer_ukr", ""),
        "answer_rus": row.get("answer_rus", ""),
        "sort_order": row.get("sort_order", "0"),
        # Новые поля для upselling
        "priority": int(row.get("priority", 10)),
        "upsell_trigger": row.get("upsell_trigger", ""),
        "base_price": self._parse_price(row.get("base_price", "")),
        "upsell_price": self._parse_price(row.get("upsell_price", "")),
        "price_suffix": row.get("price_suffix", "")
    }

def _parse_price(self, price_str: str) -> float:
    """Парсит цену из строки"""
    if not price_str:
        return 0.0
    try:
        # Удаляем всё кроме цифр и точки
        clean_price = re.sub(r'[^\d.]', '', str(price_str))
        return float(clean_price) if clean_price else 0.0
    except:
        return 0.0
```

## Настройка триггеров для разных сценариев

### 🎯 **Универсальные триггеры:**

| Trigger | Когда использовать | Пример |
|---------|-------------------|--------|
| `price` | При вопросах о стоимости | "Сколько стоят визитки?" |
| `materials` | При вопросах о материалах | "Какая бумага используется?" |
| `time` | При вопросах о сроках | "Когда будет готово?" |
| `design` | При вопросах о дизайне | "Можете сделать макет?" |
| `quantity` | При упоминании количества | "Нужно 1000 штук" |

### 🎯 **Комбинированные триггеры:**

| Trigger | Сценарий | Результат |
|---------|----------|-----------|
| `price,quantity` | Вопрос о цене + большой тираж | Показать оптовые скидки |
| `materials,quality` | Вопрос о материалах + акцент на качество | Показать премиум опции |
| `time,urgent` | Срочный заказ | Показать срочное производство |

### 🎯 **Поведенческие триггеры:**

| Trigger | Условие | Стратегия |
|---------|---------|-----------|
| `first_time` | Новый клиент | Показать популярные опции |
| `returning` | Повторный клиент | Показать новые услуги |
| `price_sensitive` | Акцент на экономии | Показать выгодные предложения |
| `quality_focused` | Акцент на качестве | Показать премиум услуги |

## Мониторинг и аналитика

### 📊 **Ключевые метрики:**

```python
# Пример логирования аналитики
analytics = {
    'query': user_text,
    'active_triggers': active_triggers,
    'upsell_shown': len(upsell_results),
    'upsell_options': [r['metadata']['group'] for r in upsell_results],
    'total_potential_revenue': sum([r['metadata'].get('upsell_price', 0) for r in upsell_results]),
    'timestamp': datetime.now().isoformat()
}
```

### 📈 **Отслеживание эффективности:**

- Процент показов upselling (% запросов с upselling)
- Средний чек с upselling vs без upselling
- Популярные триггеры и их конверсия
- Эффективность разных priority уровней

Эта система позволит вам гибко управлять ценами через Google Sheets и автоматически показывать релевантные upselling предложения на основе анализа запросов пользователей!
