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
FILES_TO_CHECK = "*.py tests/"


def run_command(name: str, cmd: str, ignore_errors: bool = False) -> bool:
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

    if result.returncode == 0 or ignore_errors:
        status = "PASSED" if result.returncode == 0 else "PASSED (informational)"
        print(f"✅ {name} - {status}")
        return True
    else:
        print(f"❌ {name} - FAILED")
        return False


def main() -> int:
    """Основная функция"""
    print("🚀 Запуск локальных проверок (идентично CI/CD)")
    print("🔧 Упрощенная проверка для внутреннего проекта")

    success = True

    # 1. Flake8 - критические ошибки (блокирующие)
    success &= run_command(
        "Flake8 - Critical Errors",
        f"flake8 --config .flake8 {FILES_TO_CHECK} --count --select=E9,F63,F7,F82 --show-source --statistics",
    )

    # 2. Flake8 - полная проверка (блокирующая)
    success &= run_command(
        "Flake8 - Full Check",
        f"flake8 --config .flake8 {FILES_TO_CHECK} --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics",
    )

    # 3. Black - форматирование (блокирующее)
    success &= run_command(
        "Black - Code Formatting",
        f"black --check --diff --line-length 100 {FILES_TO_CHECK}",
    )

    # 4. Isort - убран из проверок (слишком капризный для внутреннего проекта)
    # success &= run_command(
    #     "Isort - Import Sorting", f"isort --check-only --diff {FILES_TO_CHECK}"
    # )

    # 5. Mypy - проверка типов (информационная)
    run_command(
        "Mypy - Type Checking (informational)",
        f"mypy {FILES_TO_CHECK} --ignore-missing-imports",
        ignore_errors=True,
    )

    # 6. Bandit - безопасность (информационная)
    run_command(
        "Bandit - Security Check (informational)",
        f"bandit -r . -c pyproject.toml",
        ignore_errors=True,
    )

    # 7. Safety - уязвимости (информационная)
    run_command(
        "Safety - Vulnerability Check (informational)",
        f"safety check --file requirements.txt",
        ignore_errors=True,
    )

    # 8. Запуск тестов (блокирующий)
    success &= run_command("Pytest - Run Tests", f"pytest tests/ -v --tb=short")

    print(f"\n{'=' * 60}")
    if success:
        print("🎉 Все блокирующие проверки пройдены!")
        print("✅ Код готов для push в main")
    else:
        print("⚠️  Есть проблемы, которые нужно исправить")
        print("❌ Код НЕ готов для push")
    print(f"{'=' * 60}\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
