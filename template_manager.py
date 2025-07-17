import csv
import logging
import os
import shutil
from typing import Dict, List, Optional

from models import Template
from stats import StatsManager
from validation import validator
from exceptions import TemplateLoadError, TemplateNotFoundError, FileNotFoundError as BotFileNotFoundError, ValidationError
from error_handler import handle_exceptions, safe_execute


logger = logging.getLogger(__name__)


class TemplateManager:
    def __init__(self):
        self.templates: Dict[str, List[Template]] = {}
        self.user_languages: Dict[int, str] = {}  # user_id -> 'ukr' or 'rus'
        self.stats = StatsManager()
        self.load_templates()

    def load_templates(self):
        """Загружает шаблоны из CSV файлов"""
        import os
        
        csv_files = {
            'визитки': os.getenv('VISITKI_CSV_PATH', './data/visitki_templates.csv'),
            'футболки': os.getenv('FUTBOLKI_CSV_PATH', './data/futbolki_templates.csv'),
            'листовки': os.getenv('LISTOVKI_CSV_PATH', './data/listovki_templates.csv'),
            'наклейки': os.getenv('NAKLEYKI_CSV_PATH', './data/nakleyki_templates.csv'),
            'блокноты': os.getenv('BLOKNOTY_CSV_PATH', './data/bloknoty_templates.csv'),
        }

        loaded_categories = 0
        errors = []

        for category, csv_path in csv_files.items():
            try:
                templates_loaded = self._load_category_templates(category, csv_path)
                if templates_loaded > 0:
                    loaded_categories += 1
                    logger.info(f"Загружено шаблонов из {csv_path}: {templates_loaded}")
                else:
                    logger.warning(f"Нет шаблонов в файле: {csv_path}")

            except FileNotFoundError:
                error_msg = f"CSV файл не найден: {csv_path}"
                logger.error(error_msg)
                errors.append(error_msg)
                
            except PermissionError:
                error_msg = f"Нет прав на чтение файла: {csv_path}"
                logger.error(error_msg)
                errors.append(error_msg)
                
            except UnicodeDecodeError:
                error_msg = f"Ошибка кодировки файла: {csv_path}"
                logger.error(error_msg)
                errors.append(error_msg)
                
            except Exception as e:
                error_msg = f"Неожиданная ошибка при загрузке {csv_path}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Сортируем шаблоны по sort_order
        for category in self.templates:
            self.templates[category].sort(key=lambda x: x.sort_order)

        total_templates = sum(len(templates) for templates in self.templates.values())
        logger.info(f"Всего загружено шаблонов: {total_templates}")
        
        if errors:
            raise TemplateLoadError(
                f"Ошибки при загрузке шаблонов: {'; '.join(errors)}",
                details={'errors': errors, 'loaded_categories': loaded_categories}
            )
        
        if total_templates == 0:
            raise TemplateLoadError("Не удалось загрузить ни одного шаблона")

    def _load_category_templates(self, category: str, csv_path: str) -> int:
        """Загружает шаблоны для конкретной категории"""
        templates_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')
            
            for row_num, row in enumerate(reader, start=2):  # Начинаем с 2, так как 1 - заголовок
                try:
                    # Валидация обязательных полей
                    required_fields = ['category', 'subcategory', 'button_text', 'keywords', 'answer_ukr', 'answer_rus', 'sort_order']
                    missing_fields = [field for field in required_fields if not row.get(field)]
                    
                    if missing_fields:
                        logger.warning(f"Пропущены обязательные поля в строке {row_num} файла {csv_path}: {missing_fields}")
                        continue
                    
                    # Валидация sort_order
                    try:
                        sort_order = int(row['sort_order'])
                    except ValueError:
                        logger.warning(f"Некорректный sort_order в строке {row_num} файла {csv_path}: {row['sort_order']}")
                        continue
                    
                    # Создаем шаблон
                    template = Template(
                        category=row['category'].strip(),
                        subcategory=row['subcategory'].strip(),
                        button_text=row['button_text'].strip(),
                        keywords=[kw.strip() for kw in row['keywords'].split(',') if kw.strip()],
                        answer_ukr=row['answer_ukr'].strip(),
                        answer_rus=row['answer_rus'].strip(),
                        sort_order=sort_order
                    )
                    
                    # Валидация шаблона
                    if not self._validate_template(template):
                        logger.warning(f"Невалидный шаблон в строке {row_num} файла {csv_path}")
                        continue
                    
                    if template.category not in self.templates:
                        self.templates[template.category] = []
                    self.templates[template.category].append(template)
                    templates_count += 1
                    
                except Exception as e:
                    logger.error(f"Ошибка обработки строки {row_num} в файле {csv_path}: {str(e)}")
                    continue
        
        return templates_count

    def _validate_template(self, template: Template) -> bool:
        """Валидация шаблона"""
        # Проверка длины полей
        if len(template.button_text) > 100:
            return False
        
        if len(template.answer_ukr) > 4000 or len(template.answer_rus) > 4000:
            return False
        
        # Проверка наличия ключевых слов
        if not template.keywords or all(not kw for kw in template.keywords):
            return False
        
        return True

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
        try:
            # Валидация поискового запроса
            search_validation = validator.validate_search_query(query)
            if not search_validation.is_valid:
                raise ValidationError(f"Неверный поисковый запрос: {search_validation.error_message}")
            
            results = []
            query_lower = search_validation.cleaned_value.lower()

            for category_templates in self.templates.values():
                for template in category_templates:
                    try:
                        # Поиск в ключевых словах
                        for keyword in template.keywords:
                            if query_lower in keyword.lower():
                                results.append(template)
                                break
                        # Поиск в тексте кнопки
                        if query_lower in template.button_text.lower():
                            results.append(template)
                    except Exception as e:
                        logger.error(f"Ошибка при поиске в шаблоне {template.subcategory}: {str(e)}")
                        continue

            return results
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при поиске шаблонов: {str(e)}")
            raise TemplateError(f"Ошибка поиска шаблонов: {str(e)}")

    def get_template_by_subcategory(self, category: str, subcategory: str) -> Optional[Template]:
        """Безопасное получение шаблона по категории и подкатегории"""
        try:
            if category not in self.templates:
                raise TemplateNotFoundError(f"Категория '{category}' не найдена")
            
            for template in self.templates[category]:
                if template.subcategory == subcategory:
                    return template
            
            raise TemplateNotFoundError(f"Шаблон '{subcategory}' не найден в категории '{category}'")
            
        except Exception as e:
            logger.error(f"Ошибка получения шаблона {category}/{subcategory}: {str(e)}")
            raise TemplateError(f"Ошибка получения шаблона: {str(e)}")

    def get_category_templates(self, category: str) -> List[Template]:
        """Безопасное получение всех шаблонов категории"""
        try:
            if category not in self.templates:
                raise TemplateNotFoundError(f"Категория '{category}' не найдена")
            
            return self.templates[category].copy()  # Возвращаем копию для безопасности
            
        except Exception as e:
            logger.error(f"Ошибка получения шаблонов категории {category}: {str(e)}")
            raise TemplateError(f"Ошибка получения шаблонов категории: {str(e)}")

    def get_all_categories(self) -> List[str]:
        """Получение списка всех доступных категорий"""
        return list(self.templates.keys())

    def copy_csv_files(self) -> None:
        """Копирует CSV файлы из converted-data/csv/ в data/"""
        source_dir = "./converted-data/csv/"
        target_dir = "./data/"
        
        # Создаем папку data, если она не существует
        os.makedirs(target_dir, exist_ok=True)
        
        # Мапинг файлов из converted-data/csv/ в data/
        file_mapping = {
            'vizitki_01.csv': 'visitki_templates.csv',
            'futbolki_02.csv': 'futbolki_templates.csv',
            'listovki_03.csv': 'listovki_templates.csv',
            'nakleiki_04.csv': 'nakleyki_templates.csv',
            'bloknoty_05.csv': 'bloknoty_templates.csv'
        }
        
        copied_files = []
        errors = []
        
        for source_file, target_file in file_mapping.items():
            source_path = os.path.join(source_dir, source_file)
            target_path = os.path.join(target_dir, target_file)
            
            try:
                if os.path.exists(source_path):
                    shutil.copy2(source_path, target_path)
                    copied_files.append(f"{source_file} -> {target_file}")
                    logger.info(f"Скопирован файл: {source_path} -> {target_path}")
                else:
                    logger.warning(f"Файл не найден: {source_path}")
                    
            except Exception as e:
                error_msg = f"Ошибка копирования {source_file}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        if copied_files:
            logger.info(f"Успешно скопировано файлов: {len(copied_files)}")
        
        if errors:
            logger.error(f"Ошибки при копировании: {len(errors)}")
            for error in errors:
                logger.error(error)

    def reload_templates(self) -> None:
        """Перезагрузка шаблонов с обработкой ошибок"""
        try:
            old_templates = self.templates.copy()
            self.templates.clear()
            
            # Копируем CSV файлы из converted-data/csv/ в data/ перед перезагрузкой
            logger.info("Копирование CSV файлов перед перезагрузкой...")
            self.copy_csv_files()
            
            self.load_templates()
            logger.info("Шаблоны успешно перезагружены")
            
        except Exception as e:
            # Восстанавливаем старые шаблоны в случае ошибки
            self.templates = old_templates
            logger.error(f"Ошибка перезагрузки шаблонов: {str(e)}")
            raise TemplateLoadError(f"Не удалось перезагрузить шаблоны: {str(e)}")
