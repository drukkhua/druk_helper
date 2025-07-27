import shutil

import csv
import logging
import os
from typing import Dict, List, Optional

from src.utils.error_handler import handle_exceptions, safe_execute
from src.utils.exceptions import FileNotFoundError as BotFileNotFoundError
from src.utils.exceptions import TemplateLoadError, TemplateNotFoundError, ValidationError
from src.bot.models import Template
from src.core.stats import StatsManager
from src.core.validation import validator
from config import Config

logger = logging.getLogger(__name__)


class TemplateManager:
    def __init__(self) -> None:
        self.templates: Dict[str, List[Template]] = {}
        self.user_languages: Dict[int, str] = {}  # user_id -> 'ukr' or 'rus'
        self.user_ai_modes: Dict[int, str] = {}  # user_id -> 'standard' or 'enhanced'
        self.stats = StatsManager()
        self.config = Config()
        self.load_templates()

    def load_templates(self) -> None:
        """Загружает шаблоны из CSV файлов"""
        csv_files = {
            "визитки": self.config.VISITKI_CSV_PATH,
            "футболки": self.config.FUTBOLKI_CSV_PATH,
            "листовки": self.config.LISTOVKI_CSV_PATH,
            "наклейки": self.config.NAKLEYKI_CSV_PATH,
            "блокноты": self.config.BLOKNOTY_CSV_PATH,
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

        # Подсчитываем статистику шаблонов
        total_templates = sum(len(templates) for templates in self.templates.values())
        menu_templates = sum(
            len([t for t in templates if getattr(t, "has_menu_button", True)])
            for templates in self.templates.values()
        )
        knowledge_only = total_templates - menu_templates

        logger.info(f"Всего загружено шаблонов: {total_templates}")
        logger.info(f"  • В меню: {menu_templates}")
        logger.info(f"  • Только в базе знаний: {knowledge_only}")

        if knowledge_only > 0:
            logger.info(f"Шаблоны без button_text будут доступны через поиск и AI-режим")

        if errors:
            raise TemplateLoadError(
                f"Ошибки при загрузке шаблонов: {'; '.join(errors)}",
                details={"errors": errors, "loaded_categories": loaded_categories},
            )

        if total_templates == 0:
            raise TemplateLoadError("Не удалось загрузить ни одного шаблона")

    def _load_category_templates(self, category: str, csv_path: str) -> int:
        """Загружает шаблоны для конкретной категории"""
        templates_count = 0

        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file, delimiter=",")

            for row_num, row in enumerate(reader, start=2):  # Начинаем с 2, так как 1 - заголовок
                try:
                    # Валидация обязательных полей для базы знаний
                    knowledge_base_required_fields = [
                        "category",
                        "group",
                        "keywords",
                        "answer_ukr",
                        "answer_rus",
                        "sort_order",
                    ]
                    missing_kb_fields = [
                        field for field in knowledge_base_required_fields if not row.get(field)
                    ]

                    if missing_kb_fields:
                        logger.warning(
                            f"Пропущены обязательные поля для базы знаний в строке {row_num} файла {csv_path}: {missing_kb_fields}"
                        )
                        continue

                    # Проверяем валидность button_text для создания меню
                    button_text = row.get("button_text", "").strip()
                    has_valid_button_text = self._is_valid_button_text(button_text)

                    # Валидация sort_order
                    try:
                        sort_order = int(row["sort_order"])
                    except ValueError:
                        logger.warning(
                            f"Некорректный sort_order в строке {row_num} файла {csv_path}: {row['sort_order']}"
                        )
                        continue

                    # Создаем шаблон
                    template = Template(
                        category=row["category"].strip(),
                        subcategory=row["group"].strip(),
                        button_text=button_text,
                        keywords=[kw.strip() for kw in row["keywords"].split(",") if kw.strip()],
                        answer_ukr=row["answer_ukr"].strip(),
                        answer_rus=row["answer_rus"].strip(),
                        sort_order=sort_order,
                        has_menu_button=has_valid_button_text,  # Добавляем флаг для меню
                    )

                    # Валидация шаблона
                    if not self._validate_template(template):
                        logger.warning(f"Невалидный шаблон в строке {row_num} файла {csv_path}")
                        continue

                    if template.category not in self.templates:
                        self.templates[template.category] = []
                    self.templates[template.category].append(template)
                    templates_count += 1

                    # Логируем статус шаблона
                    if has_valid_button_text:
                        logger.debug(f"Шаблон {template.subcategory} добавлен в меню и базу знаний")
                    else:
                        logger.info(
                            f"Шаблон {template.subcategory} добавлен только в базу знаний (нет валидного button_text)"
                        )
                        logger.debug(f"  button_text был: '{button_text}'")

                except Exception as e:
                    logger.error(f"Ошибка обработки строки {row_num} в файле {csv_path}: {str(e)}")
                    continue

        return templates_count

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
        invalid_values = ["-", "_", ".", "...", "тbd", "tbd", "todo", "null", "none", "empty"]
        if button_text.lower() in invalid_values:
            return False

        return True

    def _validate_template(self, template: Template) -> bool:
        """Валидация шаблона"""
        # Проверка длины ответов
        if len(template.answer_ukr) > 4000 or len(template.answer_rus) > 4000:
            return False

        # Проверка наличия ключевых слов
        if not template.keywords or all(not kw for kw in template.keywords):
            return False

        return True

    def get_user_language(self, user_id: int) -> str:
        return self.user_languages.get(user_id, "ukr")

    def set_user_language(self, user_id: int, language: str) -> None:
        self.user_languages[user_id] = language

    def get_template_text(self, template: Template, user_id: int) -> str:
        lang = self.get_user_language(user_id)
        text = template.answer_ukr if lang == "ukr" else template.answer_rus
        # ✅ Заменяем \n на реальные переносы строк
        # return text.replace('\\n', '\n')
        return text

    def search_templates(self, query: str) -> List[Template]:
        """Поиск шаблонов по ключевым словам"""
        try:
            # Валидация поискового запроса
            search_validation = validator.validate_search_query(query)
            if not search_validation.is_valid:
                raise ValidationError(
                    f"Неверный поисковый запрос: {search_validation.error_message}"
                )

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
                        logger.error(
                            f"Ошибка при поиске в шаблоне {template.subcategory}: {str(e)}"
                        )
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

            raise TemplateNotFoundError(
                f"Шаблон '{subcategory}' не найден в категории '{category}'"
            )

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

    def get_menu_templates(self, category: str) -> List[Template]:
        """Получение только шаблонов с валидным button_text для меню"""
        try:
            if category not in self.templates:
                raise TemplateNotFoundError(f"Категория '{category}' не найдена")

            # Фильтруем только шаблоны с валидным button_text
            menu_templates = [
                template
                for template in self.templates[category]
                if getattr(template, "has_menu_button", True)
            ]

            return menu_templates

        except Exception as e:
            logger.error(f"Ошибка получения меню-шаблонов категории {category}: {str(e)}")
            raise TemplateError(f"Ошибка получения меню-шаблонов категории: {str(e)}")

    def get_knowledge_base_templates(self, category: str = None) -> List[Template]:
        """Получение всех шаблонов для базы знаний (включая без button_text)"""
        try:
            all_templates = []

            if category:
                if category not in self.templates:
                    raise TemplateNotFoundError(f"Категория '{category}' не найдена")
                all_templates = self.templates[category].copy()
            else:
                # Возвращаем все шаблоны из всех категорий
                for category_templates in self.templates.values():
                    all_templates.extend(category_templates)

            return all_templates

        except Exception as e:
            logger.error(f"Ошибка получения шаблонов для базы знаний: {str(e)}")
            raise TemplateError(f"Ошибка получения шаблонов для базы знаний: {str(e)}")

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
            "vizitki_01.csv": "visitki_templates.csv",
            "futbolki_02.csv": "futbolki_templates.csv",
            "listovki_03.csv": "listovki_templates.csv",
            "nakleiki_04.csv": "nakleyki_templates.csv",
            "bloknoty_05.csv": "bloknoty_templates.csv",
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

            # Загружаем шаблоны напрямую из Google Sheets
            self.load_templates()
            logger.info("Шаблоны успешно перезагружены")

        except Exception as e:
            # Восстанавливаем старые шаблоны в случае ошибки
            self.templates = old_templates
            logger.error(f"Ошибка перезагрузки шаблонов: {str(e)}")
            raise TemplateLoadError(f"Не удалось перезагрузить шаблоны: {str(e)}")

    def get_user_ai_mode(self, user_id: int) -> str:
        """Получает режим AI для пользователя"""
        return self.user_ai_modes.get(user_id, "standard")  # По умолчанию стандартный

    def set_user_ai_mode(self, user_id: int, mode: str) -> None:
        """Устанавливает режим AI для пользователя"""
        if mode in ["standard", "enhanced"]:
            self.user_ai_modes[user_id] = mode
            logger.info(f"Пользователь {user_id} переключился на {mode} AI режим")
        else:
            logger.warning(f"Неизвестный AI режим: {mode}")

    def toggle_user_ai_mode(self, user_id: int) -> str:
        """Переключает режим AI для пользователя"""
        current_mode = self.get_user_ai_mode(user_id)
        new_mode = "enhanced" if current_mode == "standard" else "standard"
        self.set_user_ai_mode(user_id, new_mode)
        return new_mode
