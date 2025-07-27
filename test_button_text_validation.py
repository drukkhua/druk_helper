#!/usr/bin/env python3
"""
Тест валидации button_text
Проверяет, что шаблоны без валидного button_text не попадают в меню
"""

import csv
import tempfile
import os
from src.core.template_manager import TemplateManager


def create_test_csv():
    """Создает тестовый CSV файл с различными случаями button_text"""
    test_data = [
        # Заголовок
        [
            "category",
            "subcategory",
            "button_text",
            "keywords",
            "answer_ukr",
            "answer_rus",
            "sort_order",
        ],
        # Валидные button_text - должны попасть в меню
        ["визитки", "valid1", "💰 Цена визиток", "цена,стоимость", "Ответ укр", "Ответ рус", "1"],
        ["визитки", "valid2", "📏 Размеры визиток", "размер,формат", "Ответ укр", "Ответ рус", "2"],
        # Невалидные button_text - должны идти только в базу знаний
        ["визитки", "invalid1", "", "материал,бумага", "Ответ укр", "Ответ рус", "3"],  # Пустой
        ["визитки", "invalid2", "-", "покрытие,ламинат", "Ответ укр", "Ответ рус", "4"],  # Дефис
        [
            "визитки",
            "invalid3",
            "_",
            "печать,качество",
            "Ответ укр",
            "Ответ рус",
            "5",
        ],  # Подчеркивание
        ["визитки", "invalid4", ".", "доставка,время", "Ответ укр", "Ответ рус", "6"],  # Точка
        ["визитки", "invalid5", "todo", "макет,дизайн", "Ответ укр", "Ответ рус", "7"],  # TODO
        ["визитки", "invalid6", "TBD", "срок,готовность", "Ответ укр", "Ответ рус", "8"],  # TBD
        [
            "визитки",
            "invalid7",
            "x",
            "логотип,брендинг",
            "Ответ укр",
            "Ответ рус",
            "9",
        ],  # Слишком короткий
        # Пограничные случаи
        [
            "визитки",
            "edge1",
            "AB",
            "тест1,тест2",
            "Ответ укр",
            "Ответ рус",
            "10",
        ],  # Минимум символов (валидный)
        [
            "визитки",
            "edge2",
            "A" * 100,
            "тест3,тест4",
            "Ответ укр",
            "Ответ рус",
            "11",
        ],  # Максимум символов (валидный)
        [
            "визитки",
            "edge3",
            "A" * 101,
            "тест5,тест6",
            "Ответ укр",
            "Ответ рус",
            "12",
        ],  # Превышение лимита (невалидный)
    ]

    # Создаем временный файл
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")

    writer = csv.writer(temp_file, delimiter=";")
    for row in test_data:
        writer.writerow(row)

    temp_file.close()
    return temp_file.name


def test_button_text_validation():
    """Тестирует логику валидации button_text"""

    print("🧪 Тестирование валидации button_text...")

    # Создаем тестовый CSV
    test_csv_path = create_test_csv()

    try:
        # Создаем временные переменные окружения
        original_visitki_path = os.environ.get("VISITKI_CSV_PATH")
        os.environ["VISITKI_CSV_PATH"] = test_csv_path

        # Инициализируем TemplateManager
        tm = TemplateManager()

        # Проверяем загруженные шаблоны
        all_templates = tm.get_category_templates("визитки")
        menu_templates = tm.get_menu_templates("визитки")
        knowledge_templates = tm.get_knowledge_base_templates("визитки")

        print(f"\n📊 Результаты загрузки:")
        print(f"• Всего шаблонов: {len(all_templates)}")
        print(f"• В меню: {len(menu_templates)}")
        print(f"• В базе знаний: {len(knowledge_templates)}")
        print(f"• Только в базе знаний: {len(all_templates) - len(menu_templates)}")

        print(f"\n✅ Шаблоны в меню:")
        for template in menu_templates:
            print(f"  • {template.subcategory}: '{template.button_text}'")

        print(f"\n🔍 Шаблоны только в базе знаний:")
        knowledge_only = [t for t in all_templates if not getattr(t, "has_menu_button", True)]
        for template in knowledge_only:
            print(
                f"  • {template.subcategory}: '{template.button_text}' (keywords: {', '.join(template.keywords)})"
            )

        # Проверяем конкретные случаи
        print(f"\n🎯 Проверка конкретных случаев:")

        # Валидные случаи
        valid_cases = ["valid1", "valid2", "edge1", "edge2"]
        for case in valid_cases:
            template = next((t for t in all_templates if t.subcategory == case), None)
            if template:
                has_menu = getattr(template, "has_menu_button", True)
                status = "✅ В меню" if has_menu else "❌ Не в меню"
                print(f"  • {case}: {status} - '{template.button_text}'")

        # Невалидные случаи
        invalid_cases = [
            "invalid1",
            "invalid2",
            "invalid3",
            "invalid4",
            "invalid5",
            "invalid6",
            "invalid7",
            "edge3",
        ]
        for case in invalid_cases:
            template = next((t for t in all_templates if t.subcategory == case), None)
            if template:
                has_menu = getattr(template, "has_menu_button", True)
                status = "❌ Не в меню" if not has_menu else "✅ В меню (ошибка!)"
                print(f"  • {case}: {status} - '{template.button_text}'")

        # Тестируем метод валидации
        print(f"\n🔬 Тест метода _is_valid_button_text:")
        test_values = [
            ("", False),
            ("-", False),
            ("_", False),
            (".", False),
            ("todo", False),
            ("TBD", False),
            ("x", False),
            ("AB", True),
            ("💰 Цена визиток", True),
            ("A" * 100, True),
            ("A" * 101, False),
        ]

        for value, expected in test_values:
            result = tm._is_valid_button_text(value)
            status = "✅" if result == expected else "❌"
            print(f"  {status} '{value}' -> {result} (ожидалось: {expected})")

    finally:
        # Очищаем
        if original_visitki_path:
            os.environ["VISITKI_CSV_PATH"] = original_visitki_path
        else:
            os.environ.pop("VISITKI_CSV_PATH", None)

        os.unlink(test_csv_path)

    print(f"\n✅ Тест завершен!")


if __name__ == "__main__":
    test_button_text_validation()
