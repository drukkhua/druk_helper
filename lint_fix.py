#!/usr/bin/env python3
"""
Скрипт для автоматического исправления всех линтеров
Auto-fix script that applies formatting and fixes linting issues
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
    print(f"🔧 {name}")
    print(f"{'=' * 60}")

    full_cmd = activate_cmd + cmd
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode == 0 or ignore_errors:
        print(f"✅ {name} - COMPLETED")
        return True
    else:
        print(f"❌ {name} - FAILED")
        return False


def main() -> int:
    """Основная функция"""
    print("🛠️  Автоматическое исправление кода")
    print("🔧 Применяем все форматирования и исправления")

    # 1. Black - автоматическое форматирование
    run_command("Black - Auto Format", f"black --line-length 100 {FILES_TO_CHECK}")

    # 2. Isort - убран из автоматических исправлений (слишком капризный)
    # run_command("Isort - Auto Sort Imports", f"isort {FILES_TO_CHECK}")

    # 3. Autopep8 - исправление PEP8 (если установлен)
    if (
        subprocess.run(activate_cmd + "which autopep8", shell=True, capture_output=True).returncode
        == 0
    ):
        run_command(
            "Autopep8 - Fix PEP8 Issues",
            f"autopep8 --in-place --aggressive --aggressive --max-line-length 100 {FILES_TO_CHECK}",
            ignore_errors=True,
        )

    print(f"\n{'=' * 60}")
    print("🎉 Автоматическое исправление завершено!")
    print("✅ Теперь запустите lint_check.py для проверки")
    print("📝 Команды для проверки:")
    print("   python lint_check.py")
    print("   make lint-check")
    print(f"{'=' * 60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
