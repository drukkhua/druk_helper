#!/usr/bin/env python3
"""
Скрипт для локального запуска всех линтеров как в CI/CD
Local linting script that matches CI/CD pipeline
"""
import subprocess

import os
import sys

# Активация виртуального окружения
VENV_PATH = "venv/bin/activate"
if os.path.exists(VENV_PATH):
    activate_cmd = f"source {VENV_PATH} && "
else:
    activate_cmd = ""

# Файлы для проверки
FILES_TO_CHECK = "*.py handlers.py tests/"


def run_command(name, cmd):
    """Запуск команды с выводом результата"""
    print(f"\n{'=' * 60}")
    print(f"🔍 {name}")
    print(f"{'=' * 60}")

    full_cmd = activate_cmd + cmd
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode == 0:
        print(f"✅ {name} - PASSED")
    else:
        print(f"❌ {name} - FAILED")

    return result.returncode == 0


def main():
    """Основная функция"""
    print("🚀 Запуск локальных проверок линтеров")
    print("🔧 Проверяем те же команды что и в CI/CD")

    success = True

    # 1. Flake8 - синтаксические ошибки
    success &= run_command(
        "Flake8 - Syntax Errors",
        f"flake8 --config .flake8 {FILES_TO_CHECK} --count --select=E9,F63,F7,F82 --show-source --statistics",
    )

    # 2. Flake8 - полная проверка
    success &= run_command(
        "Flake8 - Full Check",
        f"flake8 --config .flake8 {FILES_TO_CHECK} --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics",
    )

    # 3. Black - форматирование
    success &= run_command(
        "Black - Code Formatting", f"black --check --diff {FILES_TO_CHECK}"
    )

    # 4. Isort - сортировка импортов
    success &= run_command(
        "Isort - Import Sorting", f"isort --check-only --diff {FILES_TO_CHECK}"
    )

    # 5. Mypy - проверка типов (продолжаем при ошибке)
    run_command(
        "Mypy - Type Checking", f"mypy {FILES_TO_CHECK} --ignore-missing-imports"
    )

    # 6. Bandit - безопасность (продолжаем при ошибке)
    run_command(
        "Bandit - Security Check",
        f"bandit -r . -c pyproject.toml -f json -o bandit-report.json",
    )

    # 7. Safety - уязвимости (продолжаем при ошибке)
    run_command("Safety - Vulnerability Check", f"safety check --file requirements.txt")

    print(f"\n{'=' * 60}")
    if success:
        print("🎉 Все основные проверки пройдены!")
        print("✅ Код готов для CI/CD")
    else:
        print("⚠️  Есть проблемы, которые нужно исправить")
        print("❌ Код не готов для CI/CD")
    print(f"{'=' * 60}\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
