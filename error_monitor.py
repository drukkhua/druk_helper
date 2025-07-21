"""
Мониторинг и анализ ошибок бота
"""

from collections import defaultdict

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from config import logger


class ErrorMonitor:
    """Монитор ошибок для анализа и отчетности"""

    def __init__(self, log_file: str = "error_log.json") -> None:
        self.log_file = log_file
        self.error_patterns = defaultdict(int)
        self.error_trends = defaultdict(list)

    def analyze_errors(self, hours: int = 24) -> Dict:
        """Анализ ошибок за определенный период"""
        if not os.path.exists(self.log_file):
            return {"total_errors": 0, "error_types": {}, "trends": {}}

        cutoff_time = datetime.now() - timedelta(hours=hours)
        error_types = defaultdict(int)
        hourly_errors = defaultdict(int)

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        error_data = json.loads(line.strip())
                        error_time = datetime.fromisoformat(error_data["timestamp"])

                        if error_time >= cutoff_time:
                            error_types[error_data["error_type"]] += 1
                            hour_key = error_time.strftime("%Y-%m-%d %H:00")
                            hourly_errors[hour_key] += 1

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

        except Exception as e:
            logger.error(f"Ошибка анализа логов: {e}")
            return {"total_errors": 0, "error_types": {}, "trends": {}}

        return {
            "total_errors": sum(error_types.values()),
            "error_types": dict(error_types),
            "hourly_trends": dict(hourly_errors),
            "analysis_period": f"{hours} часов",
        }

    def get_critical_errors(self, hours: int = 24) -> List[Dict]:
        """Получение критических ошибок"""
        critical_types = [
            "ConfigurationError",
            "DatabaseError",
            "ExternalAPIError",
            "FileNotFoundError",
            "TemplateLoadError",
        ]

        if not os.path.exists(self.log_file):
            return []

        cutoff_time = datetime.now() - timedelta(hours=hours)
        critical_errors = []

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        error_data = json.loads(line.strip())
                        error_time = datetime.fromisoformat(error_data["timestamp"])

                        if (
                            error_time >= cutoff_time
                            and error_data["error_type"] in critical_types
                        ):
                            critical_errors.append(error_data)

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

        except Exception as e:
            logger.error(f"Ошибка получения критических ошибок: {e}")
            return []

        return critical_errors

    def get_error_report(self, hours: int = 24) -> str:
        """Генерация отчета об ошибках"""
        analysis = self.analyze_errors(hours)
        critical_errors = self.get_critical_errors(hours)

        report = f"""
📊 **Отчет об ошибках за {hours} часов**

🔢 **Общая статистика:**
- Всего ошибок: {analysis['total_errors']}
- Критических ошибок: {len(critical_errors)}

📋 **Типы ошибок:**
"""

        for error_type, count in sorted(
            analysis["error_types"].items(), key=lambda x: x[1], reverse=True
        ):
            report += f"- {error_type}: {count}\n"

        if critical_errors:
            report += "\n🚨 **Критические ошибки:**\n"
            for error in critical_errors[-5:]:  # Последние 5
                report += f"- {error['timestamp']}: {error['error_type']} - {error['message']}\n"

        return report

    def clear_old_errors(self, days: int = 30) -> None:
        """Очистка старых ошибок"""
        if not os.path.exists(self.log_file):
            return

        cutoff_time = datetime.now() - timedelta(days=days)
        temp_file = f"{self.log_file}.tmp"

        try:
            with (
                open(self.log_file, "r", encoding="utf-8") as input_file,
                open(temp_file, "w", encoding="utf-8") as output_file,
            ):
                for line in input_file:
                    try:
                        error_data = json.loads(line.strip())
                        error_time = datetime.fromisoformat(error_data["timestamp"])

                        if error_time >= cutoff_time:
                            output_file.write(line)

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

            # Заменяем оригинальный файл
            os.replace(temp_file, self.log_file)
            logger.info(f"Очищены ошибки старше {days} дней")

        except Exception as e:
            logger.error(f"Ошибка очистки логов: {e}")
            # Удаляем временный файл в случае ошибки
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def health_check(self) -> Dict:
        """Проверка здоровья системы"""
        analysis = self.analyze_errors(1)  # За последний час
        critical_errors = self.get_critical_errors(1)

        # Определяем состояние
        if len(critical_errors) > 5:
            status = "CRITICAL"
        elif analysis["total_errors"] > 50:
            status = "WARNING"
        elif analysis["total_errors"] > 10:
            status = "DEGRADED"
        else:
            status = "HEALTHY"

        return {
            "status": status,
            "errors_last_hour": analysis["total_errors"],
            "critical_errors_last_hour": len(critical_errors),
            "timestamp": datetime.now().isoformat(),
        }


# Глобальный монитор ошибок
error_monitor = ErrorMonitor()


def get_error_statistics() -> Dict:
    """Получение статистики ошибок"""
    return error_monitor.analyze_errors()


def get_health_status() -> Dict:
    """Получение статуса здоровья системы"""
    return error_monitor.health_check()


def generate_error_report(hours: int = 24) -> str:
    """Генерация отчета об ошибках"""
    return error_monitor.get_error_report(hours)


def cleanup_old_errors(days: int = 30) -> None:
    """Очистка старых ошибок"""
    error_monitor.clear_old_errors(days)
