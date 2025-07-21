"""
API для управления ботом (для внешних скриптов и мониторинга)
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from bot_lifecycle import bot_lifecycle
from config import logger
from error_monitor import generate_error_report, get_error_statistics, get_health_status


class BotAPI:
    """API для управления ботом"""

    def __init__(self) -> None:
        self.lifecycle = bot_lifecycle

    async def get_status(self) -> Dict[str, Any]:
        """Получение полного статуса бота"""
        try:
            health = await self.lifecycle.health_check()
            error_stats = get_error_statistics()

            return {
                "status": "success",
                "data": {
                    "health": health,
                    "error_statistics": error_stats,
                    "uptime": self._get_uptime(),
                    "version": "1.05",
                    "timestamp": datetime.now().isoformat(),
                },
            }
        except Exception as e:
            logger.error(f"Ошибка получения статуса: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def reload_templates(self) -> Dict[str, Any]:
        """Перезагрузка шаблонов"""
        try:
            await self.lifecycle.reload_templates()
            return {
                "status": "success",
                "message": "Шаблоны перезагружены",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Ошибка перезагрузки шаблонов: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def restart_bot(self) -> Dict[str, Any]:
        """Перезапуск бота"""
        try:
            await self.lifecycle.restart()
            return {
                "status": "success",
                "message": "Бот перезапущен",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Ошибка перезапуска бота: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_error_report(self, hours: int = 24) -> Dict[str, Any]:
        """Получение отчета об ошибках"""
        try:
            report = generate_error_report(hours)
            return {
                "status": "success",
                "data": {
                    "report": report,
                    "hours": hours,
                    "timestamp": datetime.now().isoformat(),
                },
            }
        except Exception as e:
            logger.error(f"Ошибка генерации отчета: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_template_stats(self) -> Dict[str, Any]:
        """Получение статистики шаблонов"""
        try:
            if not self.lifecycle.template_manager:
                return {
                    "status": "error",
                    "error": "Template manager не инициализирован",
                    "timestamp": datetime.now().isoformat(),
                }

            templates = self.lifecycle.template_manager.templates
            stats = {
                "total_categories": len(templates),
                "total_templates": sum(len(t) for t in templates.values()),
                "categories": {
                    category: len(templates_list)
                    for category, templates_list in templates.items()
                },
            }

            return {
                "status": "success",
                "data": stats,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики шаблонов: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _get_uptime(self) -> str:
        """Получение времени работы бота"""
        # Здесь можно добавить логику подсчета uptime
        return "N/A"  # Заглушка

    async def execute_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """Выполнение команды"""
        try:
            if command == "status":
                return await self.get_status()
            elif command == "reload":
                return await self.reload_templates()
            elif command == "restart":
                return await self.restart_bot()
            elif command == "error_report":
                hours = kwargs.get("hours", 24)
                return await self.get_error_report(hours)
            elif command == "template_stats":
                return await self.get_template_stats()
            else:
                return {
                    "status": "error",
                    "error": f"Неизвестная команда: {command}",
                    "available_commands": [
                        "status",
                        "reload",
                        "restart",
                        "error_report",
                        "template_stats",
                    ],
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.error(f"Ошибка выполнения команды {command}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# Глобальный экземпляр API
bot_api = BotAPI()


async def execute_api_command(command: str, **kwargs) -> Dict[str, Any]:
    """Выполнение API команды"""
    return await bot_api.execute_command(command, **kwargs)


def create_cli_script() -> None:
    """Создание CLI скрипта для управления ботом"""
    cli_script = """#!/usr/bin/env python3
\"\"\"
CLI скрипт для управления ботом
\"\"\"

import asyncio
import sys
import json
from bot_api import execute_api_command

async def main():
    if len(sys.argv) < 2:
        print("Использование: python cli.py <command> [options]")
        print("Доступные команды: status, reload, restart, error_report, template_stats")
        sys.exit(1)

    command = sys.argv[1]

    # Парсинг аргументов
    kwargs = {}
    if command == 'error_report' and len(sys.argv) > 2:
        kwargs['hours'] = int(sys.argv[2])

    # Выполнение команды
    result = await execute_api_command(command, **kwargs)

    # Вывод результата
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(main())
"""

    with open("/Volumes/work/TG_bots/Bot-answers/cli.py", "w", encoding="utf-8") as f:
        f.write(cli_script)

    logger.info("CLI скрипт создан: cli.py")


# Создаем CLI скрипт при импорте
create_cli_script()
