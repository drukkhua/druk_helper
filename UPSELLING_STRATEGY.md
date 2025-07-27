# Стратегия умного upselling через систему приоритетов

## Концепция многоуровневых ответов

### 🎯 **Принцип работы:**
1. **Базовый ответ** (priority 10) - стандартное предложение
2. **Premium дополнения** (priority 8-9) - улучшенные варианты
3. **Эксклюзивные опции** (priority 6-7) - премиум услуги

## Предлагаемые группы и разделы

### 📊 **Расширенная структура групп:**

#### **Основные группы (существующие):**
- `сроки` - временные рамки
- `цена` - стоимость базовых услуг
- `макет` - дизайн и подготовка
- `материалы` - стандартные материалы

#### **Новые группы для upselling:**
- `премиум_материалы` - улучшенные материалы
- `спецэффекты` - тиснение, ламинация, УФ-лак
- `нестандартные_форматы` - особые размеры и формы
- `срочное_производство` - ускоренные сроки
- `большие_тиражи` - оптовые предложения
- `комплексные_решения` - пакетные предложения

## Система приоритетов

### 🔢 **Шкала приоритетов (1-10):**

**10 - Базовые ответы** (показываются всегда):
- Стандартные цены
- Обычные материалы
- Стандартные сроки

**8-9 - Популярные улучшения** (показываются часто):
- Ламинация
- Увеличенные тиражи
- Ускоренные сроки

**6-7 - Премиум опции** (показываются при интересе):
- Тиснение фольгой
- Дизайнерские материалы
- Эксклюзивная печать

**4-5 - Специальные предложения** (по запросу):
- Уникальные форматы
- Комплексные пакеты
- Индивидуальные решения

## Примеры реализации

### 📋 **Структура данных:**

```csv
category,group,keywords,answer_ukr,answer_rus,priority,upsell_trigger,price_range
визитки,цена,"цена,стоимость","96 шт за 158 грн - стандарт","96 шт за 158 грн - стандарт",10,base,low
визитки,премиум_материалы,"премиум,качество","+ Дизайнерський картон 400г/м² - всього +50 грн","+ Дизайнерский картон 400г/м² - всего +50 грн",8,price,medium
визитки,спецэффекты,"тиснение,фольга","✨ Тиснення золотою фольгою додасть престижу - від +120 грн","✨ Тиснение золотой фольгой добавит престижа - от +120 грн",7,materials,high
```

### 🎯 **Алгоритм показа upselling:**

```python
def get_enhanced_search_results(query: str, user_context: Dict) -> List[Dict]:
    """Расширенный поиск с умным upselling"""

    # 1. Получаем базовые результаты
    base_results = knowledge_base.search_knowledge(query)

    # 2. Определяем контекст запроса
    query_context = analyze_user_intent(query, user_context)

    # 3. Добавляем уместные upselling предложения
    enhanced_results = add_smart_upselling(base_results, query_context)

    return enhanced_results

def add_smart_upselling(base_results: List[Dict], context: Dict) -> List[Dict]:
    """Добавляет умные предложения улучшений"""

    enhanced = []

    for result in base_results:
        # Добавляем основной результат
        enhanced.append(result)

        # Определяем подходящие upselling опции
        category = result.get('metadata', {}).get('category')
        group = result.get('metadata', {}).get('subcategory')  # наша group

        # Находим связанные премиум опции
        upsell_options = find_upselling_options(category, group, context)

        # Добавляем 1-2 наиболее подходящие опции
        for option in upsell_options[:2]:
            option['is_upselling'] = True
            option['relevance_score'] *= 0.8  # Немного снижаем приоритет
            enhanced.append(option)

    return enhanced

def find_upselling_options(category: str, base_group: str, context: Dict) -> List[Dict]:
    """Находит подходящие опции для upselling"""

    # Мапинг базовых групп к upselling группам
    upselling_map = {
        'цена': ['премиум_материалы', 'большие_тиражи'],
        'материалы': ['спецэффекты', 'премиум_материалы'],
        'сроки': ['срочное_производство'],
        'макет': ['комплексные_решения']
    }

    target_groups = upselling_map.get(base_group, [])

    # Ищем опции в соответствующих группах
    upsell_results = []
    for group in target_groups:
        options = knowledge_base.search_by_group(category, group)
        upsell_results.extend(options)

    # Сортируем по приоритету и контексту
    return sorted(upsell_results, key=lambda x: x.get('priority', 10))
```

## Конкретные примеры upselling

### 🎨 **Визитки:**

**Базовый ответ** (priority 10):
```
"96 визиток за 158 грн на крейдованом папері 350г/м² за 1-2 дні"
```

**Upselling дополнения** (priority 8-7):
```
"✨ Додаткові опції для ваших візиток:
• Ламінація (матова/глянцева) - +60 грн - робить візитки довговічними
• Дизайнерський картон 400г/м² - +50 грн - преміум відчуття
• Тиснення фольгою - від +120 грн - статусний вигляд"
```

### 📄 **Листовки:**

**Базовый ответ** (priority 10):
```
"Листівки А4 на крейдованому папері 130г/м² - 100 шт за 180 грн"
```

**Upselling** (priority 8-7):
```
"🚀 Зробіть листівки ще ефектнішими:
• Друк на дизайнерському папері - +40 грн - унікальна фактура
• Біговка для буклету - +25 грн - професійне складання
• УФ-лак на логотип - +80 грн - яскравий акцент"
```

## Технические решения

### 🔧 **Модификация поиска:**

```python
class EnhancedKnowledgeBase(KnowledgeBase):
    """Расширенная база знаний с upselling"""

    def search_with_upselling(self, query: str, language: str = "ukr",
                            max_upsell: int = 2) -> List[Dict]:
        """Поиск с автоматическим добавлением upselling опций"""

        # Базовый поиск
        base_results = self.search_knowledge(query, language)

        if not base_results:
            return base_results

        enhanced_results = []

        for result in base_results:
            # Добавляем основной результат
            enhanced_results.append(result)

            # Ищем связанные upsell опции
            upsell_options = self._find_related_upselling(result, language)

            # Добавляем лучшие опции
            for option in upsell_options[:max_upsell]:
                option['metadata']['is_upselling'] = True
                option['metadata']['base_query'] = query
                enhanced_results.append(option)

        return enhanced_results

    def _find_related_upselling(self, base_result: Dict, language: str) -> List[Dict]:
        """Находит связанные upselling опции"""

        metadata = base_result.get('metadata', {})
        category = metadata.get('category')
        group = metadata.get('subcategory')  # наша group

        # Определяем целевые группы для upselling
        upsell_groups = self._get_upselling_groups(group)

        upsell_results = []
        for target_group in upsell_groups:
            # Ищем в целевой группе
            group_results = self._search_by_category_and_group(category, target_group, language)

            # Фильтруем по приоритету (только 6-9)
            filtered = [r for r in group_results
                       if 6 <= int(r.get('metadata', {}).get('priority', 10)) <= 9]

            upsell_results.extend(filtered)

        # Сортируем по приоритету
        return sorted(upsell_results,
                     key=lambda x: int(x.get('metadata', {}).get('priority', 10)))

    def _get_upselling_groups(self, base_group: str) -> List[str]:
        """Мапинг базовых групп к upselling группам"""

        upselling_map = {
            'цена': ['большие_тиражи', 'премиум_материалы'],
            'материалы': ['премиум_материалы', 'спецэффекты'],
            'сроки': ['срочное_производство'],
            'макет': ['комплексные_решения', 'спецэффекты']
        }

        return upselling_map.get(base_group, [])
```

### 📝 **Формат ответа с upselling:**

```python
def format_answer_with_upselling(results: List[Dict], language: str) -> str:
    """Форматирует ответ с upselling предложениями"""

    base_answers = [r for r in results if not r.get('metadata', {}).get('is_upselling')]
    upsell_options = [r for r in results if r.get('metadata', {}).get('is_upselling')]

    # Основной ответ
    main_answer = base_answers[0]['answer'] if base_answers else ""

    # Добавляем upselling опции
    if upsell_options:
        upsell_text = "\n\n✨ Додаткові можливості:" if language == "ukr" else "\n\n✨ Дополнительные возможности:"

        for option in upsell_options:
            upsell_text += f"\n• {option['answer']}"

        main_answer += upsell_text

    return main_answer
```

## Метрики и оптимизация

### 📊 **Отслеживание эффективности:**

- Процент показов upselling опций
- CTR по дополнительным предложениям
- Конверсия в заказы премиум услуг
- Средний чек с upselling vs без

### 🎯 **A/B тестирование:**

- Разное количество upselling опций (1 vs 2 vs 3)
- Разные форматы подачи
- Различные приоритеты показа

Такая система позволит естественно предлагать дополнительные услуги, не выглядя навязчиво, и значительно увеличить средний чек заказа!
