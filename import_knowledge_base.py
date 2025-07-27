#!/usr/bin/env python3
"""
Скрипт для импорта базы знаний на production сервере
Использует: python import_knowledge_base.py --backup-dir exports/knowledge_base_backup_20250123
"""

import argparse
import json
import logging
import os
import sys
import zipfile
from pathlib import Path

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.admin.knowledge_base_manager import knowledge_base_manager
from src.ai.knowledge_base import knowledge_base

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Импорт базы знаний на production сервер")
    parser.add_argument("--backup-dir", required=True, help="Путь к папке с бэкапом или ZIP файлу")
    parser.add_argument(
        "--force", action="store_true", help="Принудительная замена существующей базы знаний"
    )
    parser.add_argument(
        "--verify-only", action="store_true", help="Только проверка бэкапа без импорта"
    )

    args = parser.parse_args()

    try:
        logger.info("🚀 Начинаем импорт базы знаний на production сервер")

        # Проверяем путь к бэкапу
        backup_path = Path(args.backup_dir)
        if not backup_path.exists():
            logger.error(f"❌ Путь к бэкапу не найден: {backup_path}")
            return 1

        # Проверяем содержимое бэкапа
        if backup_path.is_file() and backup_path.suffix == ".zip":
            logger.info(f"📦 Найден ZIP бэкап: {backup_path}")
            backup_info = verify_zip_backup(backup_path)
        elif backup_path.is_dir():
            logger.info(f"📁 Найдена папка бэкапа: {backup_path}")
            backup_info = verify_directory_backup(backup_path)
        else:
            logger.error("❌ Неподдерживаемый формат бэкапа")
            return 1

        if not backup_info["valid"]:
            logger.error(f"❌ Бэкап невалиден: {backup_info['error']}")
            return 1

        logger.info(f"✅ Бэкап валиден:")
        logger.info(f"   • Записей: {backup_info['total_items']}")
        logger.info(f"   • Категории: {list(backup_info['categories'].keys())}")
        logger.info(f"   • Источники: {list(backup_info['sources'].keys())}")

        if args.verify_only:
            logger.info("✅ Проверка завершена успешно")
            return 0

        # Проверяем существующую базу знаний
        existing_overview = knowledge_base_manager.get_knowledge_base_overview()
        if existing_overview["success"] and existing_overview["total_documents"] > 0:
            if not args.force:
                logger.warning("⚠️  Обнаружена существующая база знаний:")
                logger.warning(f"   • Документов: {existing_overview['total_documents']}")
                logger.warning("   Используйте --force для принудительной замены")

                confirm = input("Продолжить и заменить существующую базу? (yes/no): ")
                if confirm.lower() not in ["yes", "y", "да"]:
                    logger.info("Импорт отменен пользователем")
                    return 0

        # Выполняем импорт
        logger.info("📥 Начинаем импорт...")

        if backup_path.suffix == ".zip":
            # Извлекаем ZIP во временную папку
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info("📦 Извлекаем ZIP архив...")
                with zipfile.ZipFile(backup_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Ищем папку с бэкапом
                extracted_dirs = [d for d in Path(temp_dir).iterdir() if d.is_dir()]
                if extracted_dirs:
                    import_path = str(extracted_dirs[0])
                else:
                    import_path = temp_dir

                result = knowledge_base_manager.import_from_backup(import_path)
        else:
            result = knowledge_base_manager.import_from_backup(str(backup_path))

        if result["success"]:
            logger.info("✅ Импорт завершен успешно!")
            logger.info(f"   • Импортировано: {result['imported_count']} записей")
            logger.info(f"   • Всего обработано: {result['total_items']} элементов")

            # Проверяем результат
            new_overview = knowledge_base_manager.get_knowledge_base_overview()
            if new_overview["success"]:
                logger.info("📊 Статистика после импорта:")
                logger.info(f"   • Всего документов: {new_overview['total_documents']}")
                for category, count in new_overview["categories"].items():
                    logger.info(f"   • {category}: {count}")

            logger.info("\n🎉 ИМПОРТ ЗАВЕРШЕН УСПЕШНО!")
            logger.info("\n📋 Рекомендации:")
            logger.info("   • Протестируйте AI режим в боте")
            logger.info("   • Выполните команду /stats для проверки")
            logger.info("   • Проверьте команду /analytics")

            return 0
        else:
            logger.error(f"❌ Ошибка импорта: {result['error']}")
            return 1

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return 1


def verify_zip_backup(zip_path: Path) -> dict:
    """Проверяет валидность ZIP бэкапа"""
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            files = zip_ref.namelist()

            # Ищем основные файлы
            has_json = any("knowledge_base.json" in f for f in files)
            has_metadata = any("backup_info.json" in f for f in files)
            has_instructions = any("DEPLOYMENT_INSTRUCTIONS.md" in f for f in files)

            if not (has_json and has_metadata):
                return {
                    "valid": False,
                    "error": "ZIP не содержит необходимых файлов (knowledge_base.json, backup_info.json)",
                }

            # Читаем метаданные
            metadata_file = None
            for f in files:
                if "backup_info.json" in f:
                    metadata_file = f
                    break

            if metadata_file:
                with zip_ref.open(metadata_file) as f:
                    metadata = json.loads(f.read().decode("utf-8"))

                    return {
                        "valid": True,
                        "total_items": metadata.get("total_items", 0),
                        "categories": metadata.get("categories", {}),
                        "sources": metadata.get("sources", {}),
                        "backup_version": metadata.get("backup_version", "unknown"),
                    }

            return {"valid": False, "error": "Не удалось прочитать метаданные"}

    except Exception as e:
        return {"valid": False, "error": f"Ошибка чтения ZIP: {e}"}


def verify_directory_backup(dir_path: Path) -> dict:
    """Проверяет валидность папки с бэкапом"""
    try:
        json_file = dir_path / "knowledge_base.json"
        metadata_file = dir_path / "backup_info.json"

        if not json_file.exists():
            return {"valid": False, "error": "Отсутствует knowledge_base.json"}

        if not metadata_file.exists():
            return {"valid": False, "error": "Отсутствует backup_info.json"}

        # Читаем метаданные
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Проверяем JSON данные
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

            if not isinstance(data, list):
                return {
                    "valid": False,
                    "error": "knowledge_base.json должен содержать массив данных",
                }

        return {
            "valid": True,
            "total_items": metadata.get("total_items", len(data)),
            "categories": metadata.get("categories", {}),
            "sources": metadata.get("sources", {}),
            "backup_version": metadata.get("backup_version", "unknown"),
        }

    except Exception as e:
        return {"valid": False, "error": f"Ошибка чтения папки: {e}"}


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
