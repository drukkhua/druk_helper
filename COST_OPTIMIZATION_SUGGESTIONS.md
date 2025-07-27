# 💰 Оптимизация расходов на OpenAI токены

## 🔍 **Текущая ситуация с режимом `/compare`:**

**Да, режим сравнения использует в 2 раза больше токенов!**

```python
# Код в enhanced_ai_handlers.py строки 319-322
tasks = [
    ai_service.process_query(user_text, user_id, lang),           # 1-й запрос
    enhanced_ai_service.process_query(user_text, user_id, lang)   # 2-й запрос
]
```

## 💡 **Варианты оптимизации:**

### 1. **Ограничить режим сравнения**
```python
# Только для админов или первых N запросов в день
if user_id not in ADMIN_USER_IDS:
    daily_comparisons = get_user_daily_comparisons(user_id)
    if daily_comparisons >= 3:  # Лимит 3 сравнения в день
        await message.answer("Достигнут дневной лимит сравнений (3/день)")
        return
```

### 2. **Создать Mock-режим для демонстрации**
```python
# Использовать сохраненные примеры ответов вместо реальных запросов к API
if not user_in_premium_plan(user_id):
    # Показать заранее подготовленные примеры сравнения
    await show_demo_comparison(message)
    return
```

### 3. **Кэширование популярных запросов**
```python
# Сохранять результаты для часто задаваемых вопросов
cache_key = f"compare_{hash(user_text)}_{lang}"
cached_result = redis.get(cache_key)
if cached_result:
    await message.answer(cached_result)
    return
```

### 4. **Альтернативный режим "Smart Preview"**
```python
# Показать только Enhanced AI + краткое объяснение различий
# Вместо двух полных запросов к API
enhanced_result = await enhanced_ai_service.process_query(...)
comparison_note = generate_comparison_note(enhanced_result)
```

## 📊 **Мониторинг расходов:**

### Добавить в админскую панель:
```python
@router.message(Command("token_usage"))
async def cmd_token_usage(message):
    if message.from_user.id not in ADMIN_USER_IDS:
        return

    today_usage = analytics_service.get_token_usage_today()
    comparison_usage = analytics_service.get_comparison_mode_usage()

    report = f"""
📊 **Использование токенов сегодня:**
• Всего: {today_usage['total']} токенов
• Обычный режим: {today_usage['normal']} токенов
• Режим сравнения: {today_usage['comparison']} токенов (2x)
• Процент сравнений: {comparison_usage['percentage']:.1f}%
• Экономия при отключении /compare: ${today_usage['potential_savings']:.2f}
"""
    await message.answer(report)
```

## 🎯 **Рекомендуемая стратегия:**

1. **Краткосрочно:** Добавить предупреждение о двойном расходе токенов ✅ (уже сделано)

2. **Среднесрочно:** Ограничить режим сравнения:
   - 3 сравнения в день для обычных пользователей
   - Безлимитно для админов

3. **Долгосрочно:** Создать "Smart Comparison" режим:
   - Один запрос к Enhanced AI
   - Автоматическая генерация объяснения различий
   - Экономия 50% токенов

## 💰 **Потенциальная экономия:**

Если режим `/compare` составляет 20% всех запросов:
- **Текущие расходы:** 100% + 20% = 120% токенов
- **После оптимизации:** 100% + 10% = 110% токенов
- **Экономия:** ~8% от общего бюджета на OpenAI

## 🚀 **Быстрое решение - Smart Compare:**

```python
# Вместо двух запросов к API делаем один + локальное сравнение
async def smart_compare(query, user_id, lang):
    # Один запрос к Enhanced AI
    enhanced_result = await enhanced_ai_service.process_query(query, user_id, lang)

    # Местная генерация "обычного" ответа на основе шаблонов
    template_answer = template_manager.find_best_template(query, lang)

    # Показать разницу без второго API запроса
    return format_smart_comparison(enhanced_result, template_answer)
```

---

**Вывод:** Да, `/compare` тратит в 2 раза больше токенов. Рекомендую добавить ограничения или создать более экономичную альтернативу.
