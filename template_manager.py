import csv
import logging
from typing import Dict, List

from models import Template
from stats import StatsManager


logger = logging.getLogger(__name__)


class TemplateManager:
    def __init__(self):
        self.templates: Dict[str, List[Template]] = {}
        self.user_languages: Dict[int, str] = {}  # user_id -> 'ukr' or 'rus'
        self.stats = StatsManager()
        self.load_templates()

    def load_templates(self):
        """Загружает шаблоны из CSV файлов"""
        csv_files = {
            'визитки': './converted-data/csv/vizitki_page_01.csv',
            'футболки': './converted-data/csv/futbolki_page_02.csv',
            'листовки': './converted-data/csv/listovki_page_03.csv',
            'наклейки': './converted-data/csv/nakleyki_page_04.csv',
            'блокноты': './converted-data/csv/bloknoty_page_05.csv',
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
        # return text.replace('\\n', '\n')
        return text

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
