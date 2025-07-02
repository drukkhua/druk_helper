import json
import logging
import os
from datetime import datetime


logger = logging.getLogger(__name__)


class StatsManager:
    def __init__(self):
        self.stats_file = './data/stats.json'
        self.ensure_stats_file()

    def ensure_stats_file(self):
        """Создает файл статистики если его нет"""
        if not os.path.exists(self.stats_file):
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def log_template_usage(self, category: str, template_number: int, user_id: int, action: str = "view"):
        """Записывает использование шаблона"""
        try:
            # Читаем существующую статистику
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)

            today = datetime.now().strftime('%Y-%m-%d')
            current_time = datetime.now().strftime('%H:%M:%S')

            # Инициализируем структуру если нужно
            if today not in stats:
                stats[today] = {}
            if category not in stats[today]:
                stats[today][category] = {}
            if str(template_number) not in stats[today][category]:
                stats[today][category][str(template_number)] = {"count": 0, "last_used": "", "copies": 0}

            # Обновляем статистику
            if action == "view":
                stats[today][category][str(template_number)]["count"] += 1
                stats[today][category][str(template_number)]["last_used"] = current_time
            elif action == "copy":
                stats[today][category][str(template_number)]["copies"] += 1

            # Сохраняем обновленную статистику
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)

            logger.info(f"STATS: {action.upper()} - {category}:{template_number} by user {user_id}")

        except Exception as e:
            logger.error(f"Ошибка записи статистики: {e}")

    def get_stats_summary(self, days: int = 7) -> str:
        """Возвращает сводку статистики за последние дни"""
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)

            summary = "📊 Статистика использования шаблонов:\n\n"

            # Берем последние дни
            sorted_dates = sorted(stats.keys(), reverse=True)[:days]

            for date in sorted_dates:
                summary += f"📅 {date}:\n"
                day_stats = stats[date]

                for category, templates in day_stats.items():
                    total_views = sum(t.get("count", 0) for t in templates.values())
                    total_copies = sum(t.get("copies", 0) for t in templates.values())
                    summary += f"  • {category}: {total_views} просмотров, {total_copies} копирований\n"

                summary += "\n"

            return summary

        except Exception as e:
            return f"❌ Ошибка получения статистики: {e}"
