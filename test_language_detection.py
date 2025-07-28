#!/usr/bin/env python3
"""
Тест автоопределения языка
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.template_manager import TemplateManager


def test_language_detection():
    """Тестирует автоопределение языка"""

    manager = TemplateManager()

    # Тестовые фразы
    test_cases = [
        # Украинские фразы
        ("Скільки коштують візитки?", "ukr"),
        ("Потрібно надрукувати листівки", "ukr"),
        ("Яка ціна на футболки?", "ukr"),
        ("Дякую за допомогу", "ukr"),
        ("Що таке тиснення фольгою?", "ukr"),
        ("Можна зробити наклейки?", "ukr"),
        # Русские фразы
        ("Сколько стоят визитки?", "rus"),
        ("Нужно напечатать листовки", "rus"),
        ("Какая цена на футболки?", "rus"),
        ("Спасибо за помощь", "rus"),
        ("Что такое тиснение фольгой?", "rus"),
        ("Можно сделать наклейки?", "rus"),
        # Смешанные и сложные случаи
        ("Привіт! Скільки коштує друк візиток?", "ukr"),
        ("Привет! Сколько стоит печать визиток?", "rus"),
        ("фольгування", "ukr"),
        ("фольгирование", "rus"),
    ]

    print("=== Тест автоопределения языка ===\n")

    correct = 0
    total = len(test_cases)

    for text, expected_lang in test_cases:
        detected_lang = manager.detect_language(text)
        status = "✅" if detected_lang == expected_lang else "❌"

        print(f"{status} '{text}'")
        print(f"   Ожидался: {expected_lang}, определен: {detected_lang}")

        if detected_lang == expected_lang:
            correct += 1
        print()

    accuracy = (correct / total) * 100
    print(f"Результат: {correct}/{total} ({accuracy:.1f}% точность)")

    if accuracy >= 90:
        print("🎉 Отличная точность определения языка!")
    elif accuracy >= 80:
        print("👍 Хорошая точность определения языка")
    else:
        print("⚠️ Нужно улучшить алгоритм определения языка")


if __name__ == "__main__":
    test_language_detection()
