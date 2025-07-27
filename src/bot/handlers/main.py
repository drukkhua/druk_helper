from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_USER_IDS, logger
from src.utils.error_handler import handle_exceptions
from src.utils.exceptions import *
from src.bot.keyboards import (
    create_category_menu_keyboard,
    create_main_menu_keyboard,
    create_template_keyboard,
    get_category_title,
    get_cyrillic_category,
    get_latin_category,
)
from src.bot.models import UserStates
from src.core.validation import validator
from src.ai.enhanced_ai_service import enhanced_ai_service as ai_service
from src.core.business_hours import get_business_status
from src.admin.quick_corrections import quick_corrections_service
from src.admin.knowledge_base_manager import knowledge_base_manager


@handle_exceptions
async def cmd_start(message: types.Message, state: FSMContext, template_manager) -> None:
    """Обработчик команды /start"""
    user_id = message.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        raise ValidationError(f"Неверный user_id: {user_id}")

    welcome_text = (
        "👋 Привіт! Я бот-помічник для швидких відповідей клієнтам.\n\n"
        "🤖 **Я розумію питання про поліграфію!** Можете одразу написати ваше питання в чаті, і я дам детальну відповідь.\n\n"
        "📝 **Приклади питань:**\n"
        "• Скільки коштують візитки?\n"
        "• Які терміни виготовлення?\n"
        "• Які формати макетів приймаєте?\n\n"
        "🎯 Або оберіть категорію товару для готових шаблонів:"
        if template_manager.get_user_language(user_id) == "ukr"
        else "👋 Привет! Я бот-помощник для быстрых ответов клиентам.\n\n"
        "🤖 **Я понимаю вопросы о полиграфии!** Можете сразу написать ваш вопрос в чате, и я дам подробный ответ.\n\n"
        "📝 **Примеры вопросов:**\n"
        "• Сколько стоят визитки?\n"
        "• Какие сроки изготовления?\n"
        "• Какие форматы макетов принимаете?\n\n"
        "🎯 Или выберите категорию товара для готовых шаблонов:"
    )

    await message.answer(
        welcome_text, reply_markup=create_main_menu_keyboard(user_id, template_manager)
    )
    await state.set_state(UserStates.main_menu)


async def cmd_stats(message: types.Message, template_manager) -> None:
    """Команда для просмотра статистики (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        return

    # Получаем статистику от template_manager
    template_stats = template_manager.stats.get_stats_summary()

    try:
        # Импортируем сервис аналитики
        from src.analytics.analytics_service import analytics_service
        from src.integrations.knowledge_sync import knowledge_sync_service

        # Получаем аналитику AI системы
        ai_summary = analytics_service.get_analytics_summary(days=7)
        sync_status = knowledge_sync_service.get_sync_status()

        # Формируем расширенную статистику
        extended_stats = (
            f"📊 **СТАТИСТИКА СИСТЕМЫ**\n\n"
            f"🤖 **AI Аналитика (7 дней):**\n"
            f"• Всего запросов: {ai_summary['period_stats']['total_queries']}\n"
            f"• Процент ответов: {ai_summary['period_stats']['answer_rate']:.1f}%\n"
            f"• Средняя уверенность: {ai_summary['period_stats']['avg_confidence']:.3f}\n"
            f"• Время ответа: {ai_summary['period_stats']['avg_response_time_ms']:.0f}ms\n\n"
            f"📋 **База знаний:**\n"
            f"• Всего документов: {ai_summary['overall_stats']['total_documents']}\n"
            f"• Пробелы в знаниях: {ai_summary['overall_stats']['knowledge_gaps']}\n\n"
            f"🔄 **Последняя синхронизация:**\n"
            f"• Время: {sync_status['last_sync_time'] or 'Не выполнялась'}\n"
            f"• Успешно: {'✅' if sync_status['last_sync_success'] else '❌'}\n"
            f"• Изменений: {sync_status['last_sync_changes']}\n\n"
            f"📄 **Шаблоны (legacy):**\n"
            f"{template_stats}"
        )

        stats_text = extended_stats

    except Exception as e:
        # Fallback на старую статистику если новая недоступна
        stats_text = (
            f"📄 **Статистика шаблонов:**\n{template_stats}\n\n⚠️ AI аналитика недоступна: {e}"
        )
    await message.answer(stats_text)


async def process_category_selection(
    callback: CallbackQuery, state: FSMContext, template_manager
) -> None:
    """Обработчик выбора категории"""
    # Валидация callback_data
    callback_validation = validator.validate_callback_data(callback.data)
    if not callback_validation.is_valid:
        logger.error(f"Неверный callback_data: {callback.data}")
        await callback.answer("❌ Ошибка обработки запроса")
        return

    latin_category = callback_validation.cleaned_value.replace("category_", "")
    category = get_cyrillic_category(latin_category)  # Преобразуем в кириллицу для поиска
    user_id = callback.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {user_id}")
        return

    lang = template_manager.get_user_language(user_id)

    # Проверяем, есть ли шаблоны для этой категории
    if category not in template_manager.templates or not template_manager.templates[category]:
        error_text = (
            f"⏳ Шаблони для категорії '{category}' ще не додані.\nЗ'являться найближчим часом!"
            if lang == "ukr"
            else f"⏳ Шаблоны для категории '{category}' еще не добавлены.\nПоявятся в ближайшее время!"
        )
        await callback.answer(error_text)
        return

    # Определяем заголовок категории
    title = get_category_title(category, lang)
    subtitle = "Оберіть тип запиту:" if lang == "ukr" else "Выберите тип запроса:"

    await callback.message.edit_text(
        f"{title}\n\n{subtitle}",
        reply_markup=create_category_menu_keyboard(category, user_id, template_manager),
    )

    await state.update_data(current_category=category)
    await state.set_state(UserStates.category_menu)


@handle_exceptions
async def process_template_selection(
    callback: CallbackQuery, state: FSMContext, template_manager
) -> None:
    """Обработчик выбора конкретного шаблона"""
    # Валидация callback_data
    callback_validation = validator.validate_callback_data(callback.data)
    if not callback_validation.is_valid:
        raise ValidationError(f"Неверный callback_data: {callback.data}")

    parts = callback_validation.cleaned_value.split("_")
    if len(parts) < 3:
        raise ValidationError(f"Неверный формат callback_data: {callback.data}")

    latin_category = parts[1]
    category = get_cyrillic_category(latin_category)  # Преобразуем в кириллицу
    subcategory = "_".join(parts[2:])
    user_id = callback.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        raise ValidationError(f"Неверный user_id: {user_id}")

    # Находим нужный шаблон используя безопасный метод
    template = template_manager.get_template_by_subcategory(category, subcategory)

    if template:
        template_text = template_manager.get_template_text(template, user_id)
        lang = template_manager.get_user_language(user_id)

        # Логируем использование шаблона
        template_manager.stats.log_template_usage(category, template.sort_order, user_id, "view")

        header = "📋 Готовий шаблон відповіді:" if lang == "ukr" else "📋 Готовый шаблон ответа:"
        footer = "\n\n💡 Виберіть дію:" if lang == "ukr" else "\n\n💡 Выберите действие:"

        full_message = f"{header}\n\n{template_text}{footer}"

        # Сохраняем все необходимые данные для восстановления состояния
        await state.update_data(
            current_template_text=template_text,
            current_category=category,
            current_template_number=template.sort_order,
            previous_menu_type="category",
            previous_menu_title=header,
        )

        await callback.message.edit_text(
            full_message,
            reply_markup=create_template_keyboard(user_id, template_manager, template_text),
        )
    else:
        error_text = (
            "❌ Шаблон не знайдено"
            if template_manager.get_user_language(user_id) == "ukr"
            else "❌ Шаблон не найден"
        )
        await callback.answer(error_text)


async def copy_template_text(callback: CallbackQuery, state: FSMContext, template_manager) -> None:
    """Отправляет текст шаблона отдельным сообщением для удобного копирования"""
    # Валидация user_id
    user_validation = validator.validate_user_id(callback.from_user.id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {callback.from_user.id}")
        return

    user_data = await state.get_data()
    template_text = user_data.get("current_template_text", "")
    current_category = user_data.get("current_category", "визитки")
    template_number = user_data.get("current_template_number", 1)

    if template_text:
        # Логируем копирование
        template_manager.stats.log_template_usage(
            current_category, template_number, callback.from_user.id, "copy"
        )

        lang = template_manager.get_user_language(callback.from_user.id)
        copy_msg = "📋 Для копіювання:" if lang == "ukr" else "📋 Для копирования:"

        # Удаляем старое сообщение с меню
        await callback.message.delete()

        # Отправляем текст для копирования БЕЗ оформления - как обычное сообщение
        await callback.message.answer(template_text)

        # Восстанавливаем состояние и то же меню категории, что было до копирования
        await state.set_state(UserStates.category_menu)
        await state.update_data(current_category=current_category)

        category_title = get_category_title(current_category, lang)
        subtitle = "Оберіть тип запиту:" if lang == "ukr" else "Выберите тип запроса:"

        await callback.message.answer(
            f"{category_title}\n\n{subtitle}",
            reply_markup=create_category_menu_keyboard(
                current_category, callback.from_user.id, template_manager
            ),
        )

        await callback.answer("✅ Готово!")
    else:
        error_text = (
            "❌ Помилка отримання тексту"
            if template_manager.get_user_language(callback.from_user.id) == "ukr"
            else "❌ Ошибка получения текста"
        )
        await callback.answer(error_text)


async def admin_stats(callback: CallbackQuery, template_manager) -> None:
    """Показ статистики для админов"""
    # Валидация user_id
    user_validation = validator.validate_user_id(callback.from_user.id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {callback.from_user.id}")
        return

    if callback.from_user.id not in ADMIN_USER_IDS:
        await callback.answer("❌ Нет доступа")
        return

    stats_text = template_manager.stats.get_stats_summary()
    await callback.message.answer(stats_text)


async def back_to_main_menu(callback: CallbackQuery, state: FSMContext, template_manager) -> None:
    """Возврат в главное меню"""
    user_id = callback.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {user_id}")
        return
    lang = template_manager.get_user_language(user_id)

    welcome_text = (
        "🎯 Оберіть категорію товару:" if lang == "ukr" else "🎯 Выберите категорию товара:"
    )

    await callback.message.edit_text(
        welcome_text, reply_markup=create_main_menu_keyboard(user_id, template_manager)
    )
    await state.set_state(UserStates.main_menu)


async def back_to_category_menu(
    callback: CallbackQuery, state: FSMContext, template_manager
) -> None:
    """Возврат в меню категории"""
    user_data = await state.get_data()
    category = user_data.get("current_category", "визитки")
    user_id = callback.from_user.id

    lang = template_manager.get_user_language(user_id)

    category_title = get_category_title(category, lang)
    subtitle = "Оберіть тип запиту:" if lang == "ukr" else "Выберите тип запроса:"

    await callback.message.edit_text(
        f"{category_title}\n\n{subtitle}",
        reply_markup=create_category_menu_keyboard(category, user_id, template_manager),
    )
    await state.set_state(UserStates.category_menu)


async def switch_language(callback: CallbackQuery, state: FSMContext, template_manager) -> None:
    """Переключение языка"""
    user_id = callback.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {user_id}")
        return
    current_lang = template_manager.get_user_language(user_id)
    new_lang = "rus" if current_lang == "ukr" else "ukr"

    template_manager.set_user_language(user_id, new_lang)

    success_text = (
        "✅ Мова змінена на українську" if new_lang == "ukr" else "✅ Язык изменен на русский"
    )
    await callback.answer(success_text)

    # Обновляем главное меню
    welcome_text = (
        "🎯 Оберіть категорію товару:" if new_lang == "ukr" else "🎯 Выберите категорию товара:"
    )

    await callback.message.edit_text(
        welcome_text, reply_markup=create_main_menu_keyboard(user_id, template_manager)
    )


async def start_search(callback: CallbackQuery, state: FSMContext, template_manager) -> None:
    """Начало поиска"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    search_text = (
        "🔍 Введіть ключове слово для пошуку шаблонів:\n\n"
        "Наприклад: ціна, макет, терміни, якість"
        if lang == "ukr"
        else "🔍 Введите ключевое слово для поиска шаблонов:\n\n"
        "Например: цена, макет, сроки, качество"
    )

    builder = InlineKeyboardBuilder()
    back_text = "⬅️ Назад" if lang == "ukr" else "⬅️ Назад"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    await callback.message.edit_text(search_text, reply_markup=builder.as_markup())
    await state.set_state(UserStates.search_mode)


@handle_exceptions
async def process_search_query(message: types.Message, state: FSMContext, template_manager) -> None:
    """Обработка поискового запроса"""
    user_id = message.from_user.id

    # Валидация user_id
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        raise ValidationError(f"Неверный user_id: {user_id}")

    # Валидация поискового запроса
    search_validation = validator.validate_search_query(message.text)
    if not search_validation.is_valid:
        lang = template_manager.get_user_language(user_id)
        error_text = (
            f"❌ {search_validation.error_message}"
            if lang == "ukr"
            else f"❌ {search_validation.error_message}"
        )
        await message.answer(error_text)
        return

    query = search_validation.cleaned_value

    # Поиск шаблонов (теперь с proper error handling)
    found_templates = template_manager.search_templates(query)

    if not found_templates:
        no_results_text = (
            f"❌ За запитом '{query}' нічого не знайдено.\n\n" "Спробуйте інші ключові слова."
            if template_manager.get_user_language(user_id) == "ukr"
            else f"❌ По запросу '{query}' ничего не найдено.\n\n"
            "Попробуйте другие ключевые слова."
        )
        await message.answer(no_results_text)
        return

    # Показываем результаты поиска
    builder = InlineKeyboardBuilder()

    for template in found_templates[:10]:  # Ограничиваем 10 результатами
        latin_category = get_latin_category(template.category)  # Преобразуем в латиницу
        builder.row(
            InlineKeyboardButton(
                text=f"{template.button_text}",
                callback_data=f"template_{latin_category}_{template.subcategory}",
            )
        )

    lang = template_manager.get_user_language(user_id)
    back_text = "⬅️ Назад" if lang == "ukr" else "⬅️ Назад"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    results_text = (
        f"🔍 Знайдено {len(found_templates)} результатів за запитом '{query}':"
        if lang == "ukr"
        else f"🔍 Найдено {len(found_templates)} результатов по запросу '{query}':"
    )

    await message.answer(results_text, reply_markup=builder.as_markup())


async def coming_soon(callback: CallbackQuery, template_manager) -> None:
    """Обработчик для функций, которые скоро появятся"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    text = (
        "⏳ Ця категорія з'явиться найближчим часом!"
        if lang == "ukr"
        else "⏳ Эта категория появится в ближайшее время!"
    )

    await callback.answer(text)


@handle_exceptions
async def cmd_reload(message: types.Message, template_manager) -> None:
    """Команда для перезагрузки шаблонов (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    try:
        await message.answer("🔄 Начинаем полное обновление системы...")

        # Импортируем новый сервис синхронизации
        from src.integrations.knowledge_sync import knowledge_sync_service

        # Выполняем полную синхронизацию
        await message.answer("📊 Синхронизируем с Google Sheets и обновляем AI базу знаний...")
        sync_result = await knowledge_sync_service.full_sync_knowledge_base(force_reload=True)

        if sync_result["success"]:
            # Перезагружаем шаблоны в память для обратной совместимости
            await message.answer("🔄 Обновляем шаблоны в памяти...")
            template_manager.reload_templates()

            success_text = (
                f"✅ Система полностью обновлена!\n"
                f"📊 CSV файлов обновлено: {sync_result['csv_files_updated']}\n"
                f"🤖 ChromaDB обновлена: {'✅' if sync_result['chromadb_updated'] else '❌'}\n"
                f"📈 Аналитика записана: {'✅' if sync_result['analytics_recorded'] else '❌'}\n"
                f"⏱️ Время выполнения: {sync_result['duration_ms']}ms\n"
                f"📋 Загружено категорий: {len(template_manager.templates)}\n"
                f"📄 Всего шаблонов: {sum(len(t) for t in template_manager.templates.values())}"
            )
            await message.answer(success_text)
        else:
            error_text = (
                f"❌ Обновление завершилось с ошибками:\n"
                f"📊 CSV файлов обновлено: {sync_result['csv_files_updated']}\n"
                f"❌ Ошибки: {', '.join(sync_result['errors'])}"
            )
            await message.answer(error_text)

    except Exception as e:
        error_text = f"❌ Критическая ошибка при обновлении: {str(e)}"
        await message.answer(error_text)


@handle_exceptions
async def cmd_health(message: types.Message, template_manager) -> None:
    """Команда для проверки здоровья системы (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    try:
        from datetime import datetime

        from error_monitor import get_health_status

        health_status = get_health_status()

        # Статистика шаблонов
        templates_count = sum(len(t) for t in template_manager.templates.values())
        categories_count = len(template_manager.templates)

        # Статистика ошибок
        error_stats = (
            template_manager.stats.get_stats_summary()
            if hasattr(template_manager, "stats")
            else "Недоступно"
        )

        health_text = f"""
🏥 **Состояние системы**

🤖 **Статус:** {health_status['status']}
📊 **Категории:** {categories_count}
📋 **Шаблоны:** {templates_count}
🕒 **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 **Ошибки за час:**
- Всего: {health_status['errors_last_hour']}
- Критических: {health_status['critical_errors_last_hour']}

💾 **Память:** OK
🌐 **Сеть:** OK
        """

        await message.answer(health_text)

    except Exception as e:
        error_text = f"❌ Ошибка получения статуса: {str(e)}"
        await message.answer(error_text)


@handle_exceptions
async def cmd_analytics(message: types.Message, template_manager) -> None:
    """Команда для просмотра детальной аналитики AI (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    try:
        from src.analytics.dashboard import create_simple_report

        # Создаем текстовый отчет
        report = create_simple_report()

        # Разбиваем отчет если он слишком длинный
        if len(report) > 4000:
            parts = [report[i : i + 4000] for i in range(0, len(report), 4000)]
            for i, part in enumerate(parts, 1):
                await message.answer(f"📊 **Аналитика (часть {i}/{len(parts)}):**\n\n{part}")
        else:
            await message.answer(f"📊 **Полная аналитика:**\n\n{report}")

    except Exception as e:
        await message.answer(f"❌ Ошибка получения аналитики: {e}")


@handle_exceptions
async def cmd_sync(message: types.Message, template_manager) -> None:
    """Команда для умной синхронизации (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    try:
        from src.integrations.knowledge_sync import knowledge_sync_service

        await message.answer("🔍 Проверяем необходимость синхронизации...")

        # Выполняем умную синхронизацию
        sync_result = await knowledge_sync_service.smart_sync()

        if sync_result.get("skipped"):
            await message.answer(
                f"✅ Синхронизация не требуется\n" f"💡 Причина: {sync_result['reason']}"
            )
        elif sync_result["success"]:
            await message.answer(
                f"✅ Умная синхронизация завершена!\n"
                f"📊 Изменений: {sync_result['changes']}\n"
                f"⏱️ Время: {sync_result['duration_ms']}ms"
            )
        else:
            await message.answer(
                f"❌ Ошибка синхронизации: {sync_result.get('error', 'Неизвестная ошибка')}"
            )

    except Exception as e:
        await message.answer(f"❌ Критическая ошибка синхронизации: {e}")


@handle_exceptions
async def cmd_suggestions(message: types.Message, template_manager) -> None:
    """Команда для получения предложений по улучшению (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    try:
        from src.analytics.analytics_service import analytics_service

        suggestions = analytics_service.get_improvement_suggestions()

        if suggestions:
            suggestions_text = "💡 **ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ:**\n\n"

            for i, suggestion in enumerate(suggestions, 1):
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    suggestion.get("priority", "medium"), "🔵"
                )

                suggestions_text += f"{priority_emoji} **{i}. {suggestion['description']}**\n"

                if "examples" in suggestion:
                    suggestions_text += "   Примеры:\n"
                    for example in suggestion["examples"][:2]:
                        suggestions_text += f"   • {example}\n"

                suggestions_text += "\n"

            await message.answer(suggestions_text)
        else:
            await message.answer(
                "✅ Предложения по улучшению отсутствуют - система работает оптимально!"
            )

    except Exception as e:
        await message.answer(f"❌ Ошибка получения предложений: {e}")


@handle_exceptions
async def process_ai_message(message: types.Message, state: FSMContext, template_manager) -> None:
    """Обработчик текстовых сообщений в AI-режиме"""
    user_id = message.from_user.id
    user_text = message.text

    # Валидация
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {user_id}")
        return

    text_validation = validator.validate_search_query(user_text)
    if not text_validation.is_valid:
        lang = template_manager.get_user_language(user_id)
        error_text = (
            f"❌ {text_validation.error_message}"
            if lang == "ukr"
            else f"❌ {text_validation.error_message}"
        )
        await message.answer(error_text)
        return

    lang = template_manager.get_user_language(user_id)

    try:
        # Показываем индикатор "печатает"
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        # Обрабатываем запрос через AI
        ai_result = await ai_service.process_query(user_text, user_id, lang)

        if ai_result.get("answer"):
            # AI дал хороший ответ
            response_text = ai_result["answer"]

            # Для администраторов добавляем метрики
            if user_id in ADMIN_USER_IDS:
                confidence = ai_result.get("confidence", 0.0)
                source = ai_result.get("source", "unknown")
                response_time_ms = ai_result.get("response_time_ms", 0)

                admin_metrics = (
                    f"\n\n📊 **Метрики (только для админа):**\n"
                    f"• Уверенность: {confidence:.1%}\n"
                    f"• Источник: {source}\n"
                    f"• Время ответа: {response_time_ms}ms"
                )
                response_text += admin_metrics

            # Добавляем кнопки
            builder = InlineKeyboardBuilder()

            # Кнопка связи с менеджером для всех
            manager_text = (
                "📞 Зв'язатися з менеджером" if lang == "ukr" else "📞 Связаться с менеджером"
            )
            builder.row(InlineKeyboardButton(text=manager_text, callback_data="contact_manager"))

            # Дополнительные кнопки для администраторов
            if user_id in ADMIN_USER_IDS:
                # Создаем callback сессии для кнопок
                correct_callback_id = quick_corrections_service.create_callback_session(
                    user_id, user_text, response_text, "correct"
                )
                add_callback_id = quick_corrections_service.create_callback_session(
                    user_id, user_text, response_text, "add"
                )

                # Кнопка для исправления ответа
                correct_text = "✏️ Исправить ответ" if lang == "rus" else "✏️ Виправити відповідь"
                builder.row(
                    InlineKeyboardButton(
                        text=correct_text, callback_data=f"correct:{correct_callback_id}"
                    )
                )

                # Кнопка для добавления в базу знаний
                add_text = "➕ Добавить в базу" if lang == "rus" else "➕ Додати в базу"
                builder.row(
                    InlineKeyboardButton(text=add_text, callback_data=f"add:{add_callback_id}")
                )

            back_text = "⬅️ Головне меню" if lang == "ukr" else "⬅️ Главное меню"
            builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

            await message.answer(response_text, reply_markup=builder.as_markup())

        else:
            # AI не смог помочь, отправляем fallback
            response_text = ai_result["answer"]

            builder = InlineKeyboardBuilder()
            back_text = "⬅️ Головне меню" if lang == "ukr" else "⬅️ Главное меню"
            builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

            await message.answer(response_text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"Ошибка при обработке AI сообщения от {user_id}: {e}")

        # Отправляем fallback сообщение
        fallback_text = (
            "😔 Вибачте, сталася помилка. Спробуйте ще раз або зверніться до менеджера."
            if lang == "ukr"
            else "😔 Извините, произошла ошибка. Попробуйте еще раз или обратитесь к менеджеру."
        )

        builder = InlineKeyboardBuilder()
        back_text = "⬅️ Головне меню" if lang == "ukr" else "⬅️ Главное меню"
        builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

        await message.answer(fallback_text, reply_markup=builder.as_markup())


async def contact_manager(callback: CallbackQuery, template_manager) -> None:
    """Обработчик кнопки 'Связаться с менеджером'"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    # Получаем статус работы
    business_status = get_business_status(lang)

    contact_info = (
        "📞 **Контактна інформація:**\n\n"
        "👤 Менеджер: @YourManagerUsername\n"
        "📱 Телефон: +380XX XXX XX XX\n"
        "⏰ Робочий час: Пн-Пт 9:00-18:00, Сб 10:00-15:00\n\n"
        if lang == "ukr"
        else "📞 **Контактная информация:**\n\n"
        "👤 Менеджер: @YourManagerUsername\n"
        "📱 Телефон: +380XX XXX XX XX\n"
        "⏰ Рабочие часы: Пн-Пт 9:00-18:00, Сб 10:00-15:00\n\n"
    )

    full_message = business_status + "\n\n" + contact_info

    builder = InlineKeyboardBuilder()
    back_text = "⬅️ Головне меню" if lang == "ukr" else "⬅️ Главное меню"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    await callback.message.edit_text(full_message, reply_markup=builder.as_markup())
    await callback.answer()


async def start_ai_mode(callback: CallbackQuery, state: FSMContext, template_manager) -> None:
    """Переход в AI-режим"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    ai_intro_text = (
        "🤖 **AI-помічник активований!**\n\n"
        "Тепер ви можете задати будь-яке питання про наші послуги, "
        "і я спробую дати вам детальну відповідь на основі нашої бази знань.\n\n"
        "📝 **Приклади запитів:**\n"
        "• Скільки коштують візитки?\n"
        "• Які терміни виготовлення футболок?\n"
        "• Які формати макетів ви приймаєте?\n"
        "• Чи можете зробити дизайн з нуля?\n\n"
        "💡 Просто напишіть ваше питання наступним повідомленням!"
        if lang == "ukr"
        else "🤖 **AI-помощник активирован!**\n\n"
        "Теперь вы можете задать любой вопрос о наших услугах, "
        "и я попробую дать вам подробный ответ на основе нашей базы знаний.\n\n"
        "📝 **Примеры запросов:**\n"
        "• Сколько стоят визитки?\n"
        "• Какие сроки изготовления футболок?\n"
        "• Какие форматы макетов вы принимаете?\n"
        "• Можете ли сделать дизайн с нуля?\n\n"
        "💡 Просто напишите ваш вопрос следующим сообщением!"
    )

    builder = InlineKeyboardBuilder()
    back_text = "⬅️ Головне меню" if lang == "ukr" else "⬅️ Главное меню"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    await callback.message.edit_text(ai_intro_text, reply_markup=builder.as_markup())
    await state.set_state(UserStates.ai_mode)
    await callback.answer()


async def start_answer_correction(
    callback: CallbackQuery, state: FSMContext, template_manager
) -> None:
    """Начало исправления ответа администратором"""
    user_id = callback.from_user.id

    # Проверяем права администратора
    if user_id not in ADMIN_USER_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    lang = template_manager.get_user_language(user_id)

    # Извлекаем callback_id из callback_data
    callback_data = callback.data
    callback_id = callback_data.replace("correct:", "")

    # Получаем данные из callback сессии
    callback_session = quick_corrections_service.get_callback_session(callback_id)
    if not callback_session:
        await callback.answer("❌ Сессия истекла, попробуйте еще раз", show_alert=True)
        return

    original_query = callback_session["query"]
    original_answer = callback_session["answer"]

    # Убираем админские метрики из ответа
    if "📊 **Метрики (только для админа):**" in original_answer:
        original_answer = original_answer.split("📊 **Метрики (только для админа):**")[0].strip()

    # Начинаем сессию исправления
    session_id = quick_corrections_service.start_correction_session(
        user_id, original_query, original_answer
    )

    # Сохраняем данные в состоянии пользователя
    await state.update_data(
        correction_session_id=session_id,
        original_query=original_query,
        original_answer=original_answer,
        callback_id=callback_id,
    )

    correction_text = (
        "✏️ **Исправление ответа**\n\n"
        f"**Оригинальный запрос:**\n{original_query}\n\n"
        f"**Текущий ответ:**\n{original_answer}\n\n"
        "📝 Отправьте исправленный ответ следующим сообщением:"
        if lang == "rus"
        else "✏️ **Виправлення відповіді**\n\n"
        f"**Оригінальний запит:**\n{original_query}\n\n"
        f"**Поточна відповідь:**\n{original_answer}\n\n"
        "📝 Надішліть виправлену відповідь наступним повідомленням:"
    )

    builder = InlineKeyboardBuilder()
    cancel_text = "❌ Отменить" if lang == "rus" else "❌ Скасувати"
    builder.row(InlineKeyboardButton(text=cancel_text, callback_data="cancel_correction"))

    await callback.message.edit_text(correction_text, reply_markup=builder.as_markup())
    await state.set_state(UserStates.admin_correction)
    await callback.answer()


async def start_kb_addition(callback: CallbackQuery, state: FSMContext, template_manager) -> None:
    """Начало добавления нового вопроса-ответа в базу знаний"""
    user_id = callback.from_user.id

    # Проверяем права администратора
    if user_id not in ADMIN_USER_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    lang = template_manager.get_user_language(user_id)

    # Извлекаем callback_id из callback_data
    callback_data = callback.data
    callback_id = callback_data.replace("add:", "")

    # Получаем данные из callback сессии
    callback_session = quick_corrections_service.get_callback_session(callback_id)
    if not callback_session:
        await callback.answer("❌ Сессия истекла, попробуйте еще раз", show_alert=True)
        return

    query = callback_session["query"]

    # Начинаем сессию добавления
    session_id = quick_corrections_service.start_add_to_kb_session(user_id, query)

    # Сохраняем данные в состоянии пользователя
    await state.update_data(addition_session_id=session_id, query=query, callback_id=callback_id)

    addition_text = (
        "➕ **Добавление в базу знаний**\n\n"
        f"**Запрос для добавления:**\n{query}\n\n"
        "📝 Отправьте правильный ответ на этот запрос следующим сообщением:"
        if lang == "rus"
        else "➕ **Додавання до бази знань**\n\n"
        f"**Запит для додавання:**\n{query}\n\n"
        "📝 Надішліть правильну відповідь на цей запит наступним повідомленням:"
    )

    builder = InlineKeyboardBuilder()
    cancel_text = "❌ Отменить" if lang == "rus" else "❌ Скасувати"
    builder.row(InlineKeyboardButton(text=cancel_text, callback_data="cancel_correction"))

    await callback.message.edit_text(addition_text, reply_markup=builder.as_markup())
    await state.set_state(UserStates.admin_addition)
    await callback.answer()


async def cancel_correction(callback: CallbackQuery, state: FSMContext, template_manager) -> None:
    """Отмена процесса исправления"""
    user_id = callback.from_user.id

    if user_id not in ADMIN_USER_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    lang = template_manager.get_user_language(user_id)

    # Отменяем сессию в сервисе
    quick_corrections_service.cancel_session(user_id)

    # Возвращаемся в AI режим
    await state.set_state(UserStates.ai_mode)

    cancel_text = (
        "❌ Исправление отменено.\n\n"
        "💡 Вы можете задать новый вопрос или вернуться в главное меню."
        if lang == "rus"
        else "❌ Виправлення скасовано.\n\n"
        "💡 Ви можете поставити нове питання або повернутися до головного меню."
    )

    builder = InlineKeyboardBuilder()
    back_text = "⬅️ Головне меню" if lang == "ukr" else "⬅️ Главное меню"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    await callback.message.edit_text(cancel_text, reply_markup=builder.as_markup())
    await callback.answer()


async def process_admin_correction(
    message: types.Message, state: FSMContext, template_manager
) -> None:
    """Обработка исправленного ответа от администратора"""
    user_id = message.from_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    lang = template_manager.get_user_language(user_id)
    corrected_answer = message.text

    try:
        # Получаем callback_id из состояния и очищаем его
        user_data = await state.get_data()
        callback_id = user_data.get("callback_id")
        if callback_id:
            quick_corrections_service.cleanup_callback_session(callback_id)

        # Обрабатываем исправление
        result = quick_corrections_service.process_correction(user_id, corrected_answer)

        if result["success"]:
            # Получаем данные из состояния для расширенной информации о ключевых словах
            user_data = await state.get_data()
            original_query = user_data.get("original_query", "")
            original_answer = user_data.get("original_answer", "")

            # Получаем превью ключевых слов
            if original_query:
                keyword_preview = quick_corrections_service.get_keyword_preview(
                    original_query, corrected_answer, result["category"]
                )

                keywords_info = (
                    f"**🔍 Извлечено из запроса:** {keyword_preview['extracted']}\n"
                    f"**➕ Автоматически добавлено:** {', '.join(keyword_preview['auto_added']) if keyword_preview['auto_added'] else 'нет'}\n"
                    f"**💡 Доступные варианты:** {', '.join(keyword_preview['suggestions'][:5]) if keyword_preview['suggestions'] else 'нет'}"
                    if lang == "rus"
                    else f"**🔍 Витягнено з запиту:** {keyword_preview['extracted']}\n"
                    f"**➕ Автоматично додано:** {', '.join(keyword_preview['auto_added']) if keyword_preview['auto_added'] else 'немає'}\n"
                    f"**💡 Доступні варіанти:** {', '.join(keyword_preview['suggestions'][:5]) if keyword_preview['suggestions'] else 'немає'}"
                )
            else:
                keywords_info = (
                    f"**Ключевые слова:** {result['keywords']}"
                    if lang == "rus"
                    else f"**Ключові слова:** {result['keywords']}"
                )

            success_text = (
                f"✅ {result['message']}\n\n"
                f"**Категория:** {result['category']}\n"
                f"{keywords_info}\n\n"
                "Исправление добавлено в векторную базу знаний и будет использоваться для будущих ответов."
                if lang == "rus"
                else f"✅ {result['message']}\n\n"
                f"**Категорія:** {result['category']}\n"
                f"{keywords_info}\n\n"
                "Виправлення додано до векторної бази знань і буде використовуватися для майбутніх відповідей."
            )

            builder = InlineKeyboardBuilder()
            back_text = "⬅️ Головне меню" if lang == "ukr" else "⬅️ Главное меню"
            builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

            await message.answer(success_text, reply_markup=builder.as_markup())

        else:
            error_text = (
                f"❌ Ошибка: {result['error']}\n\n"
                "Попробуйте еще раз или обратитесь к техническому администратору."
                if lang == "rus"
                else f"❌ Помилка: {result['error']}\n\n"
                "Спробуйте ще раз або зверніться до технічного адміністратора."
            )

            await message.answer(error_text)

    except Exception as e:
        logger.error(f"Ошибка при обработке исправления от {user_id}: {e}")

        error_text = (
            "❌ Произошла техническая ошибка при обработке исправления.\n\n"
            "Попробуйте еще раз позже."
            if lang == "rus"
            else "❌ Сталася технічна помилка при обробці виправлення.\n\n"
            "Спробуйте ще раз пізніше."
        )

        await message.answer(error_text)

    # Возвращаемся в AI режим
    await state.set_state(UserStates.ai_mode)


async def process_admin_addition(
    message: types.Message, state: FSMContext, template_manager
) -> None:
    """Обработка добавления нового вопроса-ответа в базу знаний"""
    user_id = message.from_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    lang = template_manager.get_user_language(user_id)
    answer = message.text

    try:
        # Получаем callback_id из состояния и очищаем его
        user_data = await state.get_data()
        callback_id = user_data.get("callback_id")
        if callback_id:
            quick_corrections_service.cleanup_callback_session(callback_id)

        # Обрабатываем добавление
        result = quick_corrections_service.process_kb_addition(user_id, answer)

        if result["success"]:
            # Получаем данные из состояния для расширенной информации о ключевых словах
            user_data = await state.get_data()
            query = user_data.get("query", "")

            # Получаем превью ключевых слов
            if query:
                keyword_preview = quick_corrections_service.get_keyword_preview(
                    query, answer, result["category"]
                )

                keywords_info = (
                    f"**🔍 Извлечено из запроса:** {keyword_preview['extracted']}\n"
                    f"**➕ Автоматически добавлено:** {', '.join(keyword_preview['auto_added']) if keyword_preview['auto_added'] else 'нет'}\n"
                    f"**💡 Доступные варианты:** {', '.join(keyword_preview['suggestions'][:5]) if keyword_preview['suggestions'] else 'нет'}"
                    if lang == "rus"
                    else f"**🔍 Витягнено з запиту:** {keyword_preview['extracted']}\n"
                    f"**➕ Автоматично додано:** {', '.join(keyword_preview['auto_added']) if keyword_preview['auto_added'] else 'немає'}\n"
                    f"**💡 Доступні варіанти:** {', '.join(keyword_preview['suggestions'][:5]) if keyword_preview['suggestions'] else 'немає'}"
                )
            else:
                keywords_info = (
                    f"**Ключевые слова:** {result['keywords']}"
                    if lang == "rus"
                    else f"**Ключові слова:** {result['keywords']}"
                )

            success_text = (
                f"✅ {result['message']}\n\n"
                f"**Категория:** {result['category']}\n"
                f"{keywords_info}\n\n"
                "Новый вопрос-ответ добавлен в векторную базу знаний."
                if lang == "rus"
                else f"✅ {result['message']}\n\n"
                f"**Категорія:** {result['category']}\n"
                f"{keywords_info}\n\n"
                "Нове питання-відповідь додано до векторної бази знань."
            )

            builder = InlineKeyboardBuilder()
            back_text = "⬅️ Головне меню" if lang == "ukr" else "⬅️ Главное меню"
            builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

            await message.answer(success_text, reply_markup=builder.as_markup())

        else:
            error_text = (
                f"❌ Ошибка: {result['error']}\n\n"
                "Попробуйте еще раз или обратитесь к техническому администратору."
                if lang == "rus"
                else f"❌ Помилка: {result['error']}\n\n"
                "Спробуйте ще раз або зверніться до технічного адміністратора."
            )

            await message.answer(error_text)

    except Exception as e:
        logger.error(f"Ошибка при добавлении в БЗ от {user_id}: {e}")

        error_text = (
            "❌ Произошла техническая ошибка при добавлении в базу знаний.\n\n"
            "Попробуйте еще раз позже."
            if lang == "rus"
            else "❌ Сталася технічна помилка при додаванні до бази знань.\n\n"
            "Спробуйте ще раз пізніше."
        )

        await message.answer(error_text)

    # Возвращаемся в AI режим
    await state.set_state(UserStates.ai_mode)


async def cmd_browse_kb(message: types.Message, template_manager) -> None:
    """Команда для просмотра содержимого базы знаний (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    try:
        # Получаем обзор базы знаний
        overview = knowledge_base_manager.get_knowledge_base_overview()

        if not overview["success"]:
            await message.answer(f"❌ Ошибка получения данных: {overview['error']}")
            return

        # Формируем отчет
        overview_text = (
            "📚 **ОБЗОР БАЗЫ ЗНАНИЙ**\n\n"
            f"📊 **Общая статистика:**\n"
            f"• Всего документов: {overview['total_documents']}\n"
            f"• Коллекция: {overview['collection_name']}\n"
            f"• Обновлено: {overview['last_updated'][:19]}\n\n"
            f"🗂 **По категориям:**\n"
        )

        for category, count in overview["categories"].items():
            overview_text += f"• {category}: {count} документов\n"

        overview_text += f"\n🔗 **По источникам:**\n"
        for source, count in overview["sources"].items():
            source_name = {
                "csv": "CSV файлы",
                "admin_correction": "Админские исправления",
                "admin_addition": "Админские добавления",
            }.get(source, source)
            overview_text += f"• {source_name}: {count}\n"

        overview_text += f"\n🌐 **По языкам:**\n"
        for lang, count in overview["languages"].items():
            lang_name = {"ukrainian": "Украинский", "russian": "Русский"}.get(lang, lang)
            overview_text += f"• {lang_name}: {count}\n"

        # Разбиваем сообщение если оно слишком длинное
        if len(overview_text) > 4000:
            chunks = [overview_text[i : i + 4000] for i in range(0, len(overview_text), 4000)]
            for chunk in chunks:
                await message.answer(chunk)
        else:
            await message.answer(overview_text)

        # Предлагаем дополнительные команды
        additional_info = (
            "\n💡 **Дополнительные команды:**\n"
            "`/search_kb [запрос]` - Поиск в базе знаний\n"
            "`/export_kb` - Экспорт базы знаний"
        )
        await message.answer(additional_info)

    except Exception as e:
        logger.error(f"Ошибка команды browse_kb: {e}")
        await message.answer("❌ Произошла ошибка при получении данных")


async def cmd_search_kb(message: types.Message, template_manager) -> None:
    """Команда для поиска в базе знаний (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    try:
        # Извлекаем запрос из команды
        command_parts = message.text.split(" ", 1)
        if len(command_parts) < 2:
            await message.answer(
                "🔍 **Поиск в базе знаний**\n\n"
                "Использование: `/search_kb ваш запрос`\n\n"
                "Примеры:\n"
                "• `/search_kb визитки цена`\n"
                "• `/search_kb футболки размеры`\n"
                "• `/search_kb ламинация`"
            )
            return

        search_query = command_parts[1].strip()

        # Выполняем поиск
        search_results = knowledge_base_manager.search_knowledge_base(search_query, limit=10)

        if not search_results["success"]:
            await message.answer(f"❌ Ошибка поиска: {search_results['error']}")
            return

        if not search_results["results"]:
            await message.answer(f"🔍 По запросу «{search_query}» ничего не найдено")
            return

        # Формируем результаты поиска
        results_text = (
            f"🔍 **РЕЗУЛЬТАТЫ ПОИСКА**\n"
            f"Запрос: «{search_query}»\n"
            f"Найдено: {search_results['total_found']} результатов\n\n"
        )

        for i, result in enumerate(search_results["results"][:5], 1):
            relevance_percent = int(result["relevance_score"] * 100)
            results_text += (
                f"**{i}. {result['category']}** ({relevance_percent}% релевантность)\n"
                f"🔑 Ключевые слова: {result['keywords'][:100]}{'...' if len(result['keywords']) > 100 else ''}\n"
                f"🇺🇦 Украинский: {result['answer_ukr'][:150]}{'...' if len(result['answer_ukr']) > 150 else ''}\n"
                f"🇷🇺 Русский: {result['answer_rus'][:150]}{'...' if len(result['answer_rus']) > 150 else ''}\n"
                f"📄 Источник: {result['source']}\n\n"
            )

        # Разбиваем длинное сообщение
        if len(results_text) > 4000:
            chunks = [results_text[i : i + 4000] for i in range(0, len(results_text), 4000)]
            for chunk in chunks:
                await message.answer(chunk)
        else:
            await message.answer(results_text)

        if len(search_results["results"]) > 5:
            await message.answer(f"... и еще {len(search_results['results']) - 5} результатов")

    except Exception as e:
        logger.error(f"Ошибка команды search_kb: {e}")
        await message.answer("❌ Произошла ошибка при поиске")


async def cmd_export_kb(message: types.Message, template_manager) -> None:
    """Команда для экспорта базы знаний (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ Нет доступа")
        return

    try:
        # Показываем доступные форматы
        export_info = (
            "📦 **ЭКСПОРТ БАЗЫ ЗНАНИЙ**\n\n"
            "Доступные форматы:\n"
            "• `json` - JSON формат для разработки\n"
            "• `csv` - CSV для Google Sheets\n"
            "• `backup` - Полный бэкап для production\n\n"
            "Использование: `/export_kb [формат]`\n"
            "Пример: `/export_kb backup`"
        )

        # Извлекаем формат из команды
        command_parts = message.text.split(" ", 1)
        if len(command_parts) < 2:
            await message.answer(export_info)
            return

        export_format = command_parts[1].strip().lower()

        if export_format not in ["json", "csv", "backup"]:
            await message.answer(export_info)
            return

        await message.answer("⏳ Создаем экспорт...")

        # Выполняем экспорт
        export_result = knowledge_base_manager.export_knowledge_base(
            export_format=export_format, include_admin_additions=True
        )

        if not export_result["success"]:
            await message.answer(f"❌ Ошибка экспорта: {export_result['error']}")
            return

        # Формируем отчет об экспорте
        file_size_mb = export_result["file_size"] / (1024 * 1024)

        success_text = (
            f"✅ **ЭКСПОРТ ЗАВЕРШЕН**\n\n"
            f"📁 Формат: {export_result['format'].upper()}\n"
            f"📄 Файл: `{export_result.get('filename', export_result.get('zip_file'))}`\n"
            f"📊 Записей: {export_result['items_exported']}\n"
            f"💾 Размер: {file_size_mb:.2f} MB\n"
        )

        if export_format == "backup":
            success_text += (
                f"📦 Включает: {', '.join(export_result['includes'])}\n\n"
                f"🚀 **Для развертывания на production:**\n"
                f"1. Скачайте файл: `{export_result['zip_file']}`\n"
                f"2. Распакуйте на production сервере\n"
                f"3. Следуйте инструкциям в DEPLOYMENT_INSTRUCTIONS.md\n\n"
                f"💡 Бэкап содержит все необходимое для переноса базы знаний!"
            )
        elif export_format == "csv":
            success_text += (
                f"\n📋 **Для загрузки в Google Sheets:**\n"
                f"1. Откройте Google Sheets\n"
                f"2. Импортируйте CSV файл\n"
                f"3. Настройте синхронизацию с ботом"
            )

        await message.answer(success_text)

        # Показываем путь к файлу
        filepath = export_result.get("filepath", export_result.get("zip_filepath"))
        await message.answer(f"📂 Полный путь: `{filepath}`")

    except Exception as e:
        logger.error(f"Ошибка команды export_kb: {e}")
        await message.answer("❌ Произошла ошибка при экспорте")


async def process_direct_ai_message(
    message: types.Message, state: FSMContext, template_manager
) -> None:
    """Обработчик прямых сообщений пользователя для AI (без перехода в AI режим)"""
    user_id = message.from_user.id
    user_text = message.text

    # Валидация
    user_validation = validator.validate_user_id(user_id)
    if not user_validation.is_valid:
        logger.error(f"Неверный user_id: {user_id}")
        return

    # Проверяем, не является ли это командой или системным сообщением
    if user_text.startswith("/") or user_text.startswith("🎯") or user_text.startswith("📞"):
        return  # Пропускаем системные сообщения

    text_validation = validator.validate_search_query(user_text)
    if not text_validation.is_valid:
        lang = template_manager.get_user_language(user_id)
        error_text = (
            f"❌ {text_validation.error_message}"
            if lang == "ukr"
            else f"❌ {text_validation.error_message}"
        )
        await message.answer(error_text)
        return

    lang = template_manager.get_user_language(user_id)

    try:
        # Показываем индикатор "печатает"
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        # Определяем какой AI сервис использовать
        user_ai_mode = template_manager.get_user_ai_mode(user_id)
        if user_ai_mode == "enhanced":
            from src.ai.enhanced_ai_service import enhanced_ai_service

            ai_result = await enhanced_ai_service.process_query(user_text, user_id, lang)
        else:
            ai_result = await ai_service.process_query(user_text, user_id, lang)

        if ai_result.get("answer"):
            # AI дал хороший ответ
            response_text = ai_result["answer"]

            # Для администраторов добавляем метрики
            if user_id in ADMIN_USER_IDS:
                confidence = ai_result.get("confidence", 0.0)
                source = ai_result.get("source", "unknown")
                response_time_ms = ai_result.get("response_time_ms", 0)

                admin_metrics = (
                    f"\n\n📊 **Метрики (только для админа):**\n"
                    f"• Уверенность: {confidence:.1%}\n"
                    f"• Источник: {source}\n"
                    f"• Время ответа: {response_time_ms}ms"
                )
                response_text += admin_metrics

            # Добавляем кнопки
            builder = InlineKeyboardBuilder()

            # Кнопка связи с менеджером для всех
            manager_text = (
                "📞 Зв'язатися з менеджером" if lang == "ukr" else "📞 Связаться с менеджером"
            )
            builder.row(InlineKeyboardButton(text=manager_text, callback_data="contact_manager"))

            # Кнопка перейти в AI режим для продолжения диалога
            ai_mode_text = "🤖 Режим AI-діалогу" if lang == "ukr" else "🤖 Режим AI-диалога"
            builder.row(InlineKeyboardButton(text=ai_mode_text, callback_data="start_ai_mode"))

            # Дополнительные кнопки для администраторов
            if user_id in ADMIN_USER_IDS:
                # Создаем callback сессии для кнопок
                correct_callback_id = quick_corrections_service.create_callback_session(
                    user_id, user_text, response_text, "correct"
                )
                add_callback_id = quick_corrections_service.create_callback_session(
                    user_id, user_text, response_text, "add"
                )

                # Кнопка для исправления ответа
                correct_text = "✏️ Исправить ответ" if lang == "rus" else "✏️ Виправити відповідь"
                builder.row(
                    InlineKeyboardButton(
                        text=correct_text, callback_data=f"correct:{correct_callback_id}"
                    )
                )

                # Кнопка для добавления в базу знаний
                add_text = "➕ Добавить в базу" if lang == "rus" else "➕ Додати в базу"
                builder.row(
                    InlineKeyboardButton(text=add_text, callback_data=f"add:{add_callback_id}")
                )

            # Кнопка показать меню
            menu_text = "📋 Головне меню" if lang == "ukr" else "📋 Главное меню"
            builder.row(InlineKeyboardButton(text=menu_text, callback_data="back_to_main"))

            await message.answer(response_text, reply_markup=builder.as_markup())

        else:
            # AI не смог дать ответ - предлагаем альтернативы
            fallback_text = (
                "🤔 Не зміг знайти точну відповідь на ваше питання.\n\n"
                "📞 Рекомендую зв'язатися з менеджером для детальної консультації, "
                "або спробуйте переформулювати питання.\n\n"
                "🎯 Також можете скористатися меню категорій нижче:"
                if lang == "ukr"
                else "🤔 Не смог найти точный ответ на ваш вопрос.\n\n"
                "📞 Рекомендую связаться с менеджером для детальной консультации, "
                "или попробуйте переформулировать вопрос.\n\n"
                "🎯 Также можете воспользоваться меню категорий ниже:"
            )

            builder = InlineKeyboardBuilder()

            # Кнопка связи с менеджером
            manager_text = (
                "📞 Зв'язатися з менеджером" if lang == "ukr" else "📞 Связаться с менеджером"
            )
            builder.row(InlineKeyboardButton(text=manager_text, callback_data="contact_manager"))

            # Кнопка AI режима
            ai_mode_text = "🤖 AI-помічник" if lang == "ukr" else "🤖 AI-помощник"
            builder.row(InlineKeyboardButton(text=ai_mode_text, callback_data="start_ai_mode"))

            # Кнопка показать меню
            menu_text = "📋 Показати меню" if lang == "ukr" else "📋 Показать меню"
            builder.row(InlineKeyboardButton(text=menu_text, callback_data="back_to_main"))

            await message.answer(fallback_text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"Ошибка обработки прямого AI запроса: {e}")

        fallback_text = (
            "⚠️ Виникла помилка при обробці вашого запиту.\n\n"
            "📞 Будь ласка, зв'яжіться з менеджером або спробуйте ще раз."
            if lang == "ukr"
            else "⚠️ Возникла ошибка при обработке вашего запроса.\n\n"
            "📞 Пожалуйста, свяжитесь с менеджером или попробуйте еще раз."
        )

        builder = InlineKeyboardBuilder()
        manager_text = (
            "📞 Зв'язатися з менеджером" if lang == "ukr" else "📞 Связаться с менеджером"
        )
        builder.row(InlineKeyboardButton(text=manager_text, callback_data="contact_manager"))

        menu_text = "📋 Головне меню" if lang == "ukr" else "📋 Главное меню"
        builder.row(InlineKeyboardButton(text=menu_text, callback_data="back_to_main"))

        await message.answer(fallback_text, reply_markup=builder.as_markup())


async def switch_to_enhanced_ai(
    callback: CallbackQuery, state: FSMContext, template_manager
) -> None:
    """Переключение на персонализированный AI (Олена)"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    # Переключаем режим
    template_manager.set_user_ai_mode(user_id, "enhanced")

    success_text = (
        "🎭 Переключено на персонализированный AI с Оленой!\n\n"
        "Теперь общение будет более живым и персональным. "
        "Олена помнит контекст беседы и адаптируется под ваши потребности."
        if lang == "rus"
        else "🎭 Переключено на персоналізований AI з Оленою!\n\n"
        "Тепер спілкування буде більш живим та персональним. "
        "Олена пам'ятає контекст бесіди та адаптується під ваші потреби."
    )

    await callback.answer("✅ Режим изменен!" if lang == "rus" else "✅ Режим змінено!")

    # Обновляем главное меню с новой кнопкой
    welcome_text = (
        "🎯 Выберите категорию товара:" if lang == "rus" else "🎯 Оберіть категорію товару:"
    )

    await callback.message.edit_text(
        f"{success_text}\n\n{welcome_text}",
        reply_markup=create_main_menu_keyboard(user_id, template_manager),
    )


async def switch_to_standard_ai(
    callback: CallbackQuery, state: FSMContext, template_manager
) -> None:
    """Переключение на стандартный AI"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    # Переключаем режим
    template_manager.set_user_ai_mode(user_id, "standard")

    success_text = (
        "🤖 Переключено на стандартный AI-помощник!\n\n"
        "Теперь используется классический режим ответов без персонализации."
        if lang == "rus"
        else "🤖 Переключено на стандартний AI-помічник!\n\n"
        "Тепер використовується класичний режим відповідей без персоналізації."
    )

    await callback.answer("✅ Режим изменен!" if lang == "rus" else "✅ Режим змінено!")

    # Обновляем главное меню с новой кнопкой
    welcome_text = (
        "🎯 Выберите категорию товара:" if lang == "rus" else "🎯 Оберіть категорію товару:"
    )

    await callback.message.edit_text(
        f"{success_text}\n\n{welcome_text}",
        reply_markup=create_main_menu_keyboard(user_id, template_manager),
    )
