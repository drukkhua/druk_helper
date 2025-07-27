# Стратегия upsell_trigger и priority для максимальной релевантности

## Концепция upsell_trigger

### 🎯 **Назначение:**
Определяет **когда** показывать upselling предложение на основе контекста базового запроса.

### 📊 **Типы триггеров:**

#### 1. **Контекстные триггеры (по содержанию запроса):**
- `price` - показывать при запросах о цене
- `materials` - при вопросах о материалах/качестве
- `time` - при вопросах о сроках
- `design` - при вопросах о дизайне/макете
- `quantity` - при вопросах о тираже
- `delivery` - при вопросах о доставке
- `premium` - при упоминании премиальности, элитности, VIP

#### 2. **Поведенческие триггеры:**
- `first_time` - для новых клиентов (первый запрос)
- `returning` - для возвращающихся клиентов
- `price_sensitive` - для клиентов, акцентирующих на цене
- `quality_focused` - для клиентов, интересующихся качеством

#### 3. **Продуктовые триггеры:**
- `standard_order` - при стандартных заказах (показать премиум)
- `small_quantity` - при малых тиражах (предложить оптимизацию)
- `large_quantity` - при больших тиражах (предложить скидки)
- `urgent` - при срочных заказах (предложить ускорение)

#### 4. **Сезонные/временные триггеры:**
- `holiday_season` - в праздничные периоды
- `business_hours` - в рабочее время (B2B предложения)
- `weekend` - в выходные (личные заказы)

## Система priority (1-10)

### 🔢 **Логика приоритетов:**

#### **Priority 10 - Базовые ответы (всегда показываются):**
- Стандартные цены и услуги
- Основная информация о продукте
- Обязательные технические детали

#### **Priority 9 - Популярные улучшения (показываются в 80% случаев):**
- Ламинация визиток
- Увеличение тиража со скидкой
- Стандартные сроки → ускоренные сроки

#### **Priority 8 - Востребованные опции (показываются в 60% случаев):**
- Дизайнерские материалы
- Дополнительные форматы
- Комплексные пакеты

#### **Priority 7 - Премиум услуги (показываются в 40% случаев):**
- Тиснение фольгой
- Эксклюзивные материалы
- Индивидуальный дизайн

#### **Priority 6 - Элитные опции (показываются в 20% случаев):**
- Сложные спецэффекты
- Уникальные форматы
- VIP обслуживание

#### **Priority 5 и ниже - Специальные предложения (по запросу):**
- Очень дорогие услуги
- Экспериментальные технологии
- Индивидуальные решения

## Примеры использования

### 📋 **Структура Google Sheets с ценами:**

```csv
category,group,keywords,answer_ukr,answer_rus,priority,upsell_trigger,base_price,upsell_price,price_suffix
визитки,цена,"цена,стоимость","96 шт за {base_price} грн на стандартном картоне","96 шт за {base_price} грн на стандартном картоне",10,base,158,,
визитки,премиум_материалы,"качество,лучше","✨ Дизайнерський картон 400г/м² - всього +{upsell_price} грн до базової ціни","✨ Дизайнерский картон 400г/м² - всего +{upsell_price} грн к базовой цене",8,price,158,50,"к стандартной цене"
визитки,спецэффекты,"тиснение,фольга,люкс","🌟 Тиснення золотою фольгою - від +{upsell_price} грн","🌟 Тиснение золотой фольгой - от +{upsell_price} грн",7,materials,158,120,"за спецэффект"
визитки,срочное_производство,"быстро,срочно,завтра","⚡ Готовність за 8 годин - доплата {upsell_price} грн","⚡ Готовность за 8 часов - доплата {upsell_price} грн",6,time,158,200,"за срочность"
визитки,vip_услуги,"премиум,элитный,vip,люкс","👑 VIP-пакет: ексклюзивні матеріали + персональний дизайнер - від +{upsell_price} грн","👑 VIP-пакет: эксклюзивные материалы + персональный дизайнер - от +{upsell_price} грн",5,premium,158,400,"за VIP-обслуживание"
```

### 🎯 **Сценарии использования триггеров:**

#### **Сценарий 1: Запрос о цене (trigger: price)**
**Запрос:** "Сколько стоят визитки?"

**Логика показа:**
1. Базовый ответ (priority 10) - стандартная цена
2. Показать upselling с trigger `price` и priority 8-9:
   - Больший тираж со скидкой (priority 9)
   - Премиум материалы (priority 8)

**Результат:**
```
✅ 96 визиток за 158 грн на стандартном картоне за 1-2 дні

✨ Вигідніші варіанти:
• 1000 шт - всього 920 грн (економія 40%)
• Дизайнерський картон 400г/м² - +50 грн (преміум якість)
```

#### **Сценарий 2: Запрос о материалах (trigger: materials)**
**Запрос:** "Какая бумага используется для визиток?"

**Логика показа:**
1. Базовый ответ - стандартные материалы
2. Показать upselling с trigger `materials`:
   - Премиум материалы (priority 8)
   - Спецэффекты (priority 7)

#### **Сценарий 3: Срочный заказ (trigger: time + urgent)**
**Запрос:** "Можно ли сделать визитки к завтрашнему утру?"

**Логика показа:**
1. Стандартные сроки
2. Срочное производство (trigger `time`, priority 6)
3. Готовые шаблоны для ускорения (trigger `urgent`, priority 8)

#### **Сценарий 4: Премиальный запрос (trigger: premium)**
**Запрос:** "Хочу элитные визитки для VIP-клиентов"

**Логика показа:**
1. Базовый ответ о стандартных визитках
2. VIP-услуги (trigger `premium`, priority 5) - высокая релевантность
3. Спецэффекты (trigger `materials`, priority 7) - дополнительные опции
4. Премиум материалы (trigger `quality`, priority 8) - качественные решения

**Результат:**
```
✅ 96 визиток за 158 грн на стандартном картоне за 1-2 дня

👑 Рекомендации для VIP-клиентов:
• VIP-пакет: эксклюзивные материалы + персональный дизайнер - от +400 грн
• Тиснение золотой фольгой - от +120 грн за спецэффект
• Дизайнерский картон 400г/м² - всего +50 грн к базовой цене
```

### 🤖 **Техническая реализация:**

```python
class UpsellTriggerManager:
    """Менеджер триггеров для upselling"""

    def __init__(self):
        self.trigger_weights = {
            'price': 1.0,
            'materials': 0.9,
            'time': 0.8,
            'design': 0.7,
            'quantity': 0.6,
            'quality_focused': 1.2,
            'price_sensitive': 0.8,
            'first_time': 1.1,
            'returning': 0.9
        }

    def analyze_query_triggers(self, query: str, user_context: Dict) -> List[str]:
        """Анализирует запрос и определяет активные триггеры"""

        active_triggers = []
        query_lower = query.lower()

        # Контекстные триггеры
        if any(word in query_lower for word in ['цена', 'стоимость', 'сколько', 'прайс']):
            active_triggers.append('price')

        if any(word in query_lower for word in ['материал', 'бумага', 'качество', 'картон']):
            active_triggers.append('materials')

        if any(word in query_lower for word in ['срок', 'время', 'быстро', 'срочно', 'завтра']):
            active_triggers.append('time')

        if any(word in query_lower for word in ['дизайн', 'макет', 'красиво', 'оформление']):
            active_triggers.append('design')

        if any(word in query_lower for word in ['штук', 'тираж', 'количество', 'много', 'мало']):
            active_triggers.append('quantity')

        # Поведенческие триггеры
        if user_context.get('is_first_time', False):
            active_triggers.append('first_time')

        if user_context.get('previous_orders', 0) > 0:
            active_triggers.append('returning')

        # Определяем фокус клиента
        if self._is_price_sensitive(query, user_context):
            active_triggers.append('price_sensitive')
        elif self._is_quality_focused(query, user_context):
            active_triggers.append('quality_focused')

        return active_triggers

    def calculate_upsell_relevance(self, upsell_option: Dict, active_triggers: List[str]) -> float:
        """Вычисляет релевантность upselling опции для текущих триггеров"""

        option_trigger = upsell_option.get('metadata', {}).get('upsell_trigger', '')
        priority = int(upsell_option.get('metadata', {}).get('priority', 5))

        # Базовая релевантность на основе приоритета
        base_relevance = (11 - priority) / 10.0  # priority 10 = 0.1, priority 1 = 1.0

        # Бонус за совпадение триггеров
        trigger_bonus = 0
        if option_trigger in active_triggers:
            trigger_bonus = self.trigger_weights.get(option_trigger, 0.5)

        # Итоговая релевантность
        final_relevance = base_relevance + trigger_bonus

        return min(final_relevance, 2.0)  # Максимум 2.0

    def _is_price_sensitive(self, query: str, context: Dict) -> bool:
        """Определяет, чувствителен ли клиент к цене"""
        price_words = ['дешево', 'недорого', 'бюджет', 'экономия', 'скидка', 'дешевле']
        return any(word in query.lower() for word in price_words)

    def _is_quality_focused(self, query: str, context: Dict) -> bool:
        """Определяет, фокусируется ли клиент на качестве"""
        quality_words = ['качество', 'лучший', 'премиум', 'элитный', 'статусный', 'престижный']
        return any(word in query.lower() for word in quality_words)

class EnhancedUpsellSearch:
    """Расширенный поиск с умным upselling"""

    def __init__(self):
        self.trigger_manager = UpsellTriggerManager()

    def search_with_smart_upselling(self, query: str, user_context: Dict,
                                  language: str = "ukr") -> List[Dict]:
        """Поиск с умным upselling на основе триггеров"""

        # 1. Получаем базовые результаты
        base_results = knowledge_base.search_knowledge(query, language)

        if not base_results:
            return base_results

        # 2. Анализируем триггеры из запроса
        active_triggers = self.trigger_manager.analyze_query_triggers(query, user_context)

        # 3. Находим подходящие upselling опции
        upsell_options = self._find_relevant_upselling(base_results, active_triggers, language)

        # 4. Комбинируем результаты
        enhanced_results = []

        # Добавляем основные результаты
        for result in base_results:
            enhanced_results.append(result)

        # Добавляем лучшие upselling опции (максимум 2-3)
        for option in upsell_options[:3]:
            option['metadata']['is_upselling'] = True
            option['metadata']['triggered_by'] = active_triggers
            enhanced_results.append(option)

        return enhanced_results

    def _find_relevant_upselling(self, base_results: List[Dict],
                               active_triggers: List[str], language: str) -> List[Dict]:
        """Находит наиболее релевантные upselling опции"""

        if not base_results:
            return []

        main_result = base_results[0]
        category = main_result.get('metadata', {}).get('category', '')

        # Получаем все возможные upselling опции для категории
        all_upsell_options = self._get_upselling_options_for_category(category, language)

        # Вычисляем релевантность каждой опции
        scored_options = []
        for option in all_upsell_options:
            relevance = self.trigger_manager.calculate_upsell_relevance(option, active_triggers)
            if relevance > 0.3:  # Минимальный порог релевантности
                option['upsell_relevance'] = relevance
                scored_options.append(option)

        # Сортируем по релевантности
        scored_options.sort(key=lambda x: x['upsell_relevance'], reverse=True)

        return scored_options
```

## Варианты использования для максимальной релевантности

### 🎯 **Вариант 1: Адаптивные триггеры**

```csv
category,group,upsell_trigger,priority,conditions
визитки,премиум_материалы,price,8,"base_price < 500"
визитки,премиум_материалы,quality_focused,9,"качество в запросе"
визитки,большие_тиражи,price_sensitive,9,"упоминание экономии"
```

### 🎯 **Вариант 2: Мультитриггеры**

```csv
upsell_trigger
"price,first_time"  // Для новых клиентов при вопросе о цене
"materials,quality_focused"  // Для любителей качества при вопросах о материалах
"time,urgent"  // При срочных запросах о сроках
```

### 🎯 **Вариант 3: Динамические приоритеты**

```csv
priority,dynamic_conditions
8,"if holiday_season then 9"
7,"if returning_customer then 8"
6,"if large_order then 8"
```

### 🎯 **Вариант 4: Контекстные цепочки**

```csv
trigger_chain
"price → quantity → materials"  // Цена → объем → качество
"time → design → materials"     // Сроки → дизайн → материалы
```

**Рекомендация:** Начните с простых триггеров (`price`, `materials`, `time`) и постепенно добавляйте сложность на основе анализа поведения пользователей.

Хотите, чтобы я реализовал конкретный вариант?
