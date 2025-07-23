#!/usr/bin/env python3
"""
Скрипт для установки всех зависимостей проекта
Устанавливает пакеты из requirements.txt
"""

import subprocess
import sys
import os


def run_command(command, description):
    """Запускает команду и выводит результат"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - успешно!")
        if result.stdout:
            print(f"   📄 Вывод: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - ошибка!")
        if e.stdout:
            print(f"   📄 Stdout: {e.stdout.strip()}")
        if e.stderr:
            print(f"   🚨 Stderr: {e.stderr.strip()}")
        return False


def main():
    """Основная функция установки зависимостей"""
    print("🚀 УСТАНОВКА ЗАВИСИМОСТЕЙ ДЛЯ BOT-ANSWERS")
    print("=" * 50)

    # Проверяем, что мы в правильной директории
    if not os.path.exists("requirements.txt"):
        print("❌ Файл requirements.txt не найден!")
        print("   Убедитесь, что вы запускаете скрипт из корневой директории проекта")
        sys.exit(1)

    # Проверяем версию Python
    python_version = sys.version
    print(f"🐍 Python версия: {python_version}")

    # Устанавливаем зависимости из requirements.txt
    commands = [
        ("pip3 install --upgrade pip", "Обновление pip"),
        ("pip3 install -r requirements.txt", "Установка зависимостей из requirements.txt"),
    ]

    failed_commands = []

    for command, description in commands:
        success = run_command(command, description)
        if not success:
            failed_commands.append((command, description))

    print("\n" + "=" * 50)

    if failed_commands:
        print("⚠️ НЕКОТОРЫЕ КОМАНДЫ ЗАВЕРШИЛИСЬ С ОШИБКАМИ:")
        for command, description in failed_commands:
            print(f"   ❌ {description}: {command}")
        print("\n💡 Попробуйте запустить команды вручную или с флагом --break-system-packages")
    else:
        print("🎉 ВСЕ ЗАВИСИМОСТИ УСТАНОВЛЕНЫ УСПЕШНО!")

        # Проверяем установку ChromaDB
        try:
            import chromadb

            print(f"✅ ChromaDB установлен, версия: {chromadb.__version__}")
        except ImportError:
            print("⚠️ ChromaDB не удалось импортировать")

        # Проверяем установку OpenAI
        try:
            import openai

            print(f"✅ OpenAI установлен, версия: {openai.__version__}")
        except ImportError:
            print("⚠️ OpenAI не удалось импортировать")

    print("\n🔧 Если возникают проблемы с установкой, попробуйте:")
    print("   pip3 install --break-system-packages -r requirements.txt")


if __name__ == "__main__":
    main()
