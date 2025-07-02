import asyncio
import csv
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv


# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_IDS = [int(x) for x in os.getenv('ADMIN_USER_IDS', '').split(',') if x]
PORTFOLIO_LINK = os.getenv('PORTFOLIO_LINK', 'https://t.me/druk_portfolio')

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


@dataclass
class Template:
    category: str
    subcategory: str
    button_text: str
    keywords: List[str]
    answer_ukr: str
    answer_rus: str
    sort_order: int


class UserStates(StatesGroup):
    main_menu = State()
    category_menu = State()
    search_mode = State()


class StatsManager:
    def __init__(self):
        self.stats_file = './data/stats.json'
        self.ensure_stats_file()

    def ensure_stats_file(self):
        """Создает файл статистики если его нет"""
        if not os.path.exists(self.stats_file):
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def log_template_usage(self, category: str, template_number: int, user_id: int, action: str = "view"):
        """Записывает использование шаблона"""
        try:
            # Читаем существующую статистику
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)

            today = datetime.now().strftime('%Y-%m-%d')
            current_time = datetime.now().strftime('%H:%M:%S')

            # Инициализируем структуру если нужно
            if today not in stats:
                stats[today] = {}
            if category not in stats[today]:
                stats[today][category] = {}
            if str(template_number) not in stats[today][category]:
                stats[today][category][str(template_number)] = {"count": 0, "last_used": "", "copies": 0}

            # Обновляем статистику
            if action == "view":
                stats[today][category][str(template_number)]["count"] += 1
                stats[today][category][str(template_number)]["last_used"] = current_time
            elif action == "copy":
                stats[today][category][str(template_number)]["copies"] += 1

            # Сохраняем обновленную статистику
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)

            logger.info(f"STATS: {action.upper()} - {category}:{template_number} by user {user_id}")

        except Exception as e:
            logger.error(f"Ошибка записи статистики: {e}")

    def get_stats_summary(self, days: int = 7) -> str:
        """Возвращает сводку статистики за последние дни"""
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)

            summary = "📊 Статистика использования шаблонов:\n\n"

            # Берем последние дни
            sorted_dates = sorted(stats.keys(), reverse=True)[:days]

            for date in sorted_dates:
                summary += f"📅 {date}:\n"
                day_stats = stats[date]

                for category, templates in day_stats.items():
                    total_views = sum(t.get("count", 0) for t in templates.values())
                    total_copies = sum(t.get("copies", 0) for t in templates.values())
                    summary += f"  • {category}: {total_views} просмотров, {total_copies} копирований\n"

                summary += "\n"

            return summary

        except Exception as e:
            return f"❌ Ошибка получения статистики: {e}"


class TemplateManager:
    def __init__(self):
        self.templates: Dict[str, List[Template]] = {}
        self.user_languages: Dict[int, str] = {}  # user_id -> 'ukr' or 'rus'
        self.stats = StatsManager()
        self.load_templates()

    def load_templates(self):
        """Загружает шаблоны из CSV файлов"""
        csv_files = {
            'визитки': './data/visitki_templates.csv',
            'футболки': './data/futbolki_templates.csv',
            'листовки': './data/listovki_templates.csv'
        }

        for category, csv_path in csv_files.items():
            try:
                with open(csv_path, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file, delimiter=';')
                    for row in reader:
                        template = Template(
                            category=row['category'],
                            subcategory=row['subcategory'],
                            button_text=row['button_text'],
                            keywords=row['keywords'].split(','),
                            answer_ukr=row['answer_ukr'],
                            answer_rus=row['answer_rus'],
                            sort_order=int(row['sort_order'])
                        )

                        if template.category not in self.templates:
                            self.templates[template.category] = []
                        self.templates[template.category].append(template)

                logger.info(f"Загружено шаблонов из {csv_path}: {len(self.templates.get(category, []))}")

            except FileNotFoundError:
                logger.warning(f"CSV файл не найден: {csv_path}")

        # Сортируем шаблоны по sort_order
        for category in self.templates:
            self.templates[category].sort(key=lambda x: x.sort_order)

        total_templates = sum(len(templates) for templates in self.templates.values())
        logger.info(f"Всего загружено шаблонов: {total_templates}")

    def get_user_language(self, user_id: int) -> str:
        return self.user_languages.get(user_id, 'ukr')

    def set_user_language(self, user_id: int, language: str):
        self.user_languages[user_id] = language

    def get_template_text(self, template: Template, user_id: int) -> str:
        lang = self.get_user_language(user_id)
        text = template.answer_ukr if lang == 'ukr' else template.answer_rus
        # ✅ Заменяем \n на реальные переносы строк
        return text.replace('\\n', '\n')

    def search_templates(self, query: str) -> List[Template]:
        """Поиск шаблонов по ключевым словам"""
        results = []
        query_lower = query.lower()

        for category_templates in self.templates.values():
            for template in category_templates:
                # Поиск в ключевых словах
                for keyword in template.keywords:
                    if query_lower in keyword.lower():
                        results.append(template)
                        break
                # Поиск в тексте кнопки
                if query_lower in template.button_text.lower():
                    results.append(template)

        return results


# Глобальный менеджер шаблонов
template_manager = TemplateManager()


def get_category_title(category: str, lang: str) -> str:
    """Возвращает заголовок категории на нужном языке"""
    titles = {
        'визитки': {'ukr': '📇 Візитки', 'rus': '📇 Визитки'},
        'футболки': {'ukr': '👕 Футболки', 'rus': '👕 Футболки'},
        'листовки': {'ukr': '📄 Листівки', 'rus': '📄 Листовки'}
    }

    return titles.get(category, {}).get(lang, f"📦 {category.title()}")


def create_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру главного меню"""
    lang = template_manager.get_user_language(user_id)

    builder = InlineKeyboardBuilder()

    # Основные категории
    builder.row(InlineKeyboardButton(text="📇 Візитки" if lang == 'ukr' else "📇 Визитки",
                                     callback_data="category_визитки"))
    builder.row(InlineKeyboardButton(text="👕 Футболки",
                                     callback_data="category_футболки"))
    builder.row(InlineKeyboardButton(text="📄 Листівки" if lang == 'ukr' else "📄 Листовки",
                                     callback_data="category_листовки"))

    # Дополнительные функции
    builder.row(InlineKeyboardButton(text="🔍 Пошук" if lang == 'ukr' else "🔍 Поиск",
                                     callback_data="search"))

    # Переключатель языка
    lang_text = "🇷🇺 Русский" if lang == 'ukr' else "🇺🇦 Українська"
    builder.row(InlineKeyboardButton(text=lang_text, callback_data="switch_language"))

    # Админ-функции (если пользователь админ)
    if user_id in ADMIN_USER_IDS:
        builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))

    return builder.as_markup()


def create_category_menu_keyboard(category: str, user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для конкретной категории"""
    builder = InlineKeyboardBuilder()

    if category in template_manager.templates:
        templates = template_manager.templates[category]

        # Добавляем кнопки для каждого шаблона
        for template in templates:
            builder.row(InlineKeyboardButton(
                text=template.button_text,
                callback_data=f"template_{category}_{template.subcategory}"
            ))

    # Кнопка "Назад"
    lang = template_manager.get_user_language(user_id)
    back_text = "⬅️ Назад" if lang == 'ukr' else "⬅️ Назад"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    return builder.as_markup()


def create_template_keyboard(user_id: int, template_data: str = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру для отображения шаблона"""
    lang = template_manager.get_user_language(user_id)
    builder = InlineKeyboardBuilder()

    # Кнопка "Копировать" - отправляет текст отдельным сообщением
    if template_data:
        copy_text = "📋 Копіювати" if lang == 'ukr' else "📋 Копировать"
        builder.add(InlineKeyboardButton(text=copy_text, callback_data=f"copy_template"))

    # Кнопка "Назад"
    back_text = "⬅️ Назад" if lang == 'ukr' else "⬅️ Назад"
    builder.add(InlineKeyboardButton(text=back_text, callback_data="back_to_category"))

    # Размещаем кнопки в одну строку
    builder.adjust(2)

    return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id

    welcome_text = (
        "👋 Привіт! Я бот-помічник для швидких відповідей клієнтам.\n\n"
        "🎯 Оберіть категорію товару, щоб отримати готові шаблони відповідей:"
        if template_manager.get_user_language(user_id) == 'ukr' else
        "👋 Привет! Я бот-помощник для быстрых ответов клиентам.\n\n"
        "🎯 Выберите категорию товара, чтобы получить готовые шаблоны ответов:"
    )

    await message.answer(
        welcome_text,
        reply_markup=create_main_menu_keyboard(user_id)
    )
    await state.set_state(UserStates.main_menu)


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Команда для просмотра статистики (только для админов)"""
    if message.from_user.id not in ADMIN_USER_IDS:
        return

    stats_text = template_manager.stats.get_stats_summary()
    await message.answer(stats_text)


@dp.callback_query(lambda c: c.data.startswith("category_"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора категории"""
    category = callback.data.replace("category_", "")
    user_id = callback.from_user.id

    lang = template_manager.get_user_language(user_id)

    # Проверяем, есть ли шаблоны для этой категории
    if category not in template_manager.templates or not template_manager.templates[category]:
        error_text = (
            f"⏳ Шаблони для категорії '{category}' ще не додані.\nЗ'являться найближчим часом!"
            if lang == 'ukr' else
            f"⏳ Шаблоны для категории '{category}' еще не добавлены.\nПоявятся в ближайшее время!"
        )
        await callback.answer(error_text)
        return

    # Определяем заголовок категории
    title = get_category_title(category, lang)
    subtitle = "Оберіть тип запиту:" if lang == 'ukr' else "Выберите тип запроса:"

    await callback.message.edit_text(
        f"{title}\n\n{subtitle}",
        reply_markup=create_category_menu_keyboard(category, user_id)
    )

    await state.update_data(current_category=category)
    await state.set_state(UserStates.category_menu)


@dp.callback_query(lambda c: c.data.startswith("template_"))
async def process_template_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора конкретного шаблона"""
    parts = callback.data.split("_")
    category = parts[1]
    subcategory = "_".join(parts[2:])
    user_id = callback.from_user.id

    # Находим нужный шаблон
    template = None
    if category in template_manager.templates:
        for t in template_manager.templates[category]:
            if t.subcategory == subcategory:
                template = t
                break

    if template:
        template_text = template_manager.get_template_text(template, user_id)
        lang = template_manager.get_user_language(user_id)

        # Логируем использование шаблона
        template_manager.stats.log_template_usage(category, template.sort_order, user_id, "view")

        header = "📋 Готовий шаблон відповіді:" if lang == 'ukr' else "📋 Готовый шаблон ответа:"
        footer = "\n\n💡 Виберіть дію:" if lang == 'ukr' else "\n\n💡 Выберите действие:"

        full_message = f"{header}\n\n{template_text}{footer}"

        # Сохраняем все необходимые данные для восстановления состояния
        await state.update_data(
            current_template_text=template_text,
            current_category=category,
            current_template_number=template.sort_order,
            previous_menu_type="category",
            previous_menu_title=header
        )

        await callback.message.edit_text(
            full_message,
            reply_markup=create_template_keyboard(user_id, template_text)
        )
    else:
        error_text = "❌ Шаблон не знайдено" if template_manager.get_user_language(
            user_id) == 'ukr' else "❌ Шаблон не найден"
        await callback.answer(error_text)


@dp.callback_query(lambda c: c.data == "copy_template")
async def copy_template_text(callback: CallbackQuery, state: FSMContext):
    """Отправляет текст шаблона отдельным сообщением для удобного копирования"""
    user_data = await state.get_data()
    template_text = user_data.get('current_template_text', '')
    current_category = user_data.get('current_category', 'визитки')
    template_number = user_data.get('current_template_number', 1)

    if template_text:
        # Логируем копирование
        template_manager.stats.log_template_usage(current_category, template_number, callback.from_user.id, "copy")

        lang = template_manager.get_user_language(callback.from_user.id)
        copy_msg = "📋 Для копіювання:" if lang == 'ukr' else "📋 Для копирования:"

        # Удаляем старое сообщение с меню
        await callback.message.delete()

        # Отправляем текст для копирования БЕЗ оформления - как обычное сообщение
        await callback.message.answer(template_text)

        # Восстанавливаем состояние и то же меню категории, что было до копирования
        await state.set_state(UserStates.category_menu)
        await state.update_data(current_category=current_category)

        category_title = get_category_title(current_category, lang)
        subtitle = "Оберіть тип запиту:" if lang == 'ukr' else "Выберите тип запроса:"

        await callback.message.answer(
            f"{category_title}\n\n{subtitle}",
            reply_markup=create_category_menu_keyboard(current_category, callback.from_user.id)
        )

        await callback.answer("✅ Готово!")
    else:
        error_text = "❌ Помилка отримання тексту" if template_manager.get_user_language(
            callback.from_user.id) == 'ukr' else "❌ Ошибка получения текста"
        await callback.answer(error_text)


@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Показ статистики для админов"""
    if callback.from_user.id not in ADMIN_USER_IDS:
        await callback.answer("❌ Нет доступа")
        return

    stats_text = template_manager.stats.get_stats_summary()
    await callback.message.answer(stats_text)


@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    welcome_text = (
        "🎯 Оберіть категорію товару:"
        if lang == 'ukr' else
        "🎯 Выберите категорию товара:"
    )

    await callback.message.edit_text(
        welcome_text,
        reply_markup=create_main_menu_keyboard(user_id)
    )
    await state.set_state(UserStates.main_menu)


@dp.callback_query(lambda c: c.data == "back_to_category")
async def back_to_category_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню категории"""
    user_data = await state.get_data()
    category = user_data.get('current_category', 'визитки')
    user_id = callback.from_user.id

    lang = template_manager.get_user_language(user_id)

    category_title = get_category_title(category, lang)
    subtitle = "Оберіть тип запиту:" if lang == 'ukr' else "Выберите тип запроса:"

    await callback.message.edit_text(
        f"{category_title}\n\n{subtitle}",
        reply_markup=create_category_menu_keyboard(category, user_id)
    )
    await state.set_state(UserStates.category_menu)


@dp.callback_query(lambda c: c.data == "switch_language")
async def switch_language(callback: CallbackQuery, state: FSMContext):
    """Переключение языка"""
    user_id = callback.from_user.id
    current_lang = template_manager.get_user_language(user_id)
    new_lang = 'rus' if current_lang == 'ukr' else 'ukr'

    template_manager.set_user_language(user_id, new_lang)

    success_text = "✅ Мова змінена на українську" if new_lang == 'ukr' else "✅ Язык изменен на русский"
    await callback.answer(success_text)

    # Обновляем главное меню
    welcome_text = (
        "🎯 Оберіть категорію товару:"
        if new_lang == 'ukr' else
        "🎯 Выберите категорию товара:"
    )

    await callback.message.edit_text(
        welcome_text,
        reply_markup=create_main_menu_keyboard(user_id)
    )


@dp.callback_query(lambda c: c.data == "search")
async def start_search(callback: CallbackQuery, state: FSMContext):
    """Начало поиска"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    search_text = (
        "🔍 Введіть ключове слово для пошуку шаблонів:\n\n"
        "Наприклад: ціна, макет, терміни, якість"
        if lang == 'ukr' else
        "🔍 Введите ключевое слово для поиска шаблонов:\n\n"
        "Например: цена, макет, сроки, качество"
    )

    builder = InlineKeyboardBuilder()
    back_text = "⬅️ Назад" if lang == 'ukr' else "⬅️ Назад"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    await callback.message.edit_text(search_text, reply_markup=builder.as_markup())
    await state.set_state(UserStates.search_mode)


@dp.message(StateFilter(UserStates.search_mode))
async def process_search_query(message: types.Message, state: FSMContext):
    """Обработка поискового запроса"""
    query = message.text.strip()
    user_id = message.from_user.id

    if len(query) < 2:
        error_text = (
            "❌ Запит занадто короткий. Введіть мінімум 2 символи."
            if template_manager.get_user_language(user_id) == 'ukr' else
            "❌ Запрос слишком короткий. Введите минимум 2 символа."
        )
        await message.answer(error_text)
        return

    # Поиск шаблонов
    found_templates = template_manager.search_templates(query)

    if not found_templates:
        no_results_text = (
            f"❌ За запитом '{query}' нічого не знайдено.\n\n"
            "Спробуйте інші ключові слова."
            if template_manager.get_user_language(user_id) == 'ukr' else
            f"❌ По запросу '{query}' ничего не найдено.\n\n"
            "Попробуйте другие ключевые слова."
        )
        await message.answer(no_results_text)
        return

    # Показываем результаты поиска
    builder = InlineKeyboardBuilder()

    for template in found_templates[:10]:  # Ограничиваем 10 результатами
        builder.row(InlineKeyboardButton(
            text=f"{template.button_text}",
            callback_data=f"template_{template.category}_{template.subcategory}"
        ))

    lang = template_manager.get_user_language(user_id)
    back_text = "⬅️ Назад" if lang == 'ukr' else "⬅️ Назад"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="back_to_main"))

    results_text = (
        f"🔍 Знайдено {len(found_templates)} результатів за запитом '{query}':"
        if lang == 'ukr' else
        f"🔍 Найдено {len(found_templates)} результатов по запросу '{query}':"
    )

    await message.answer(results_text, reply_markup=builder.as_markup())


@dp.callback_query(lambda c: c.data == "coming_soon")
async def coming_soon(callback: CallbackQuery):
    """Обработчик для функций, которые скоро появятся"""
    user_id = callback.from_user.id
    lang = template_manager.get_user_language(user_id)

    text = (
        "⏳ Ця категорія з'явиться найближчим часом!"
        if lang == 'ukr' else
        "⏳ Эта категория появится в ближайшее время!"
    )

    await callback.answer(text)


async def main():
    """Главная функция для запуска бота"""
    # Создаем директорию для данных, если её нет
    os.makedirs('./data', exist_ok=True)

    logger.info("Запуск бота...")
    logger.info(f"Загружены категории: {list(template_manager.templates.keys())}")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
