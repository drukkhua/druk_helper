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


def fix_whitespace_issues():
    """Исправляет ошибки W291 (trailing whitespace) и W293 (blank line contains whitespace)"""
    print("\n🔧 Исправление проблем с пробелами (W291, W293)")

    # Находим все Python файлы в проекте (исключая venv и test_env)
    import glob
    import re

    python_files = []
    for pattern in ["*.py", "src/**/*.py", "tests/**/*.py"]:
        python_files.extend(glob.glob(pattern, recursive=True))

    # Исключаем файлы из виртуальных окружений
    python_files = [f for f in python_files if not f.startswith(("venv/", "test_env/"))]

    fixed_files = 0
    w291_fixes = 0  # trailing whitespace
    w293_fixes = 0  # blank line contains whitespace

    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            modified = False
            new_lines = []

            for line in lines:
                original_line = line

                # W291: Исправляем trailing whitespace (пробелы в конце строк)
                if line.rstrip() != line.rstrip("\n\r"):  # Есть trailing whitespace
                    line = line.rstrip() + "\n" if line.endswith("\n") else line.rstrip()
                    w291_fixes += 1
                    modified = True

                # W293: Исправляем blank lines with whitespace (пустые строки с пробелами)
                if re.match(r"^[ \t]+$", line):  # Строка содержит только пробелы/табы
                    line = "\n" if line.endswith("\n") else ""
                    w293_fixes += 1
                    modified = True

                new_lines.append(line)

            if modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                fixed_files += 1
                print(f"   ✅ Исправлен: {file_path}")

        except Exception as e:
            print(f"   ❌ Ошибка в {file_path}: {e}")

    print(f"✅ Обработано файлов: {len(python_files)}")
    print(f"✅ Исправлено файлов: {fixed_files}")
    print(f"   • W291 (trailing whitespace): {w291_fixes} исправлений")
    print(f"   • W293 (blank line whitespace): {w293_fixes} исправлений")


def main() -> int:
    """Основная функция"""
    print("🛠️  Автоматическое исправление кода")
    print("🔧 Применяем все форматирования и исправления")

    # 1. Black - автоматическое форматирование
    run_command("Black - Auto Format", f"black --line-length 100 {FILES_TO_CHECK}")

    # 2. Isort - убран из автоматических исправлений (слишком капризный)
    # run_command("Isort - Auto Sort Imports", f"isort {FILES_TO_CHECK}")

    # 3. Исправление проблем с пробелами (W291, W293)
    fix_whitespace_issues()

    # 4. Autopep8 - исправление PEP8 (если установлен)
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
