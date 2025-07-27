"""
Простой веб-dashboard для просмотра аналитики AI бота
Показывает статистику, топ неотвеченных запросов и предложения по улучшению
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

try:
    from flask import Flask, render_template_string, jsonify, request

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from .analytics_service import analytics_service

logger = logging.getLogger(__name__)


# HTML шаблон для dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Bot Analytics Dashboard</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .stat-item { text-align: center; padding: 15px; background: #e3f2fd; border-radius: 8px; }
        .stat-value { font-size: 2em; font-weight: bold; color: #1976d2; }
        .stat-label { color: #666; margin-top: 5px; }
        .query-list { max-height: 300px; overflow-y: auto; }
        .query-item { padding: 10px; border-bottom: 1px solid #eee; }
        .priority-high { border-left: 4px solid #f44336; }
        .priority-medium { border-left: 4px solid #ff9800; }
        .priority-low { border-left: 4px solid #4caf50; }
        .refresh-btn { background: #1976d2; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #1565c0; }
        h1, h2 { color: #333; }
        .timestamp { color: #999; font-size: 0.9em; }
    </style>
    <script>
        function refreshData() {
            fetch('/api/analytics')
                .then(response => response.json())
                .then(data => {
                    updateStats(data);
                })
                .catch(error => console.error('Error:', error));
        }

        function updateStats(data) {
            // Обновляем статистику
            if (data.period_stats) {
                document.getElementById('total-queries').textContent = data.period_stats.total_queries;
                document.getElementById('answer-rate').textContent = data.period_stats.answer_rate.toFixed(1) + '%';
                document.getElementById('avg-confidence').textContent = data.period_stats.avg_confidence.toFixed(3);
                document.getElementById('response-time').textContent = data.period_stats.avg_response_time_ms.toFixed(0) + 'ms';
            }

            // Обновляем timestamp
            document.getElementById('last-updated').textContent = 'Обновлено: ' + new Date().toLocaleString();
        }

        // Автообновление каждые 30 секунд
        setInterval(refreshData, 30000);
    </script>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Bot Analytics Dashboard</h1>
        <p class="timestamp" id="last-updated">Обновлено: {{ timestamp }}</p>

        <button class="refresh-btn" onclick="refreshData()">🔄 Обновить данные</button>

        <!-- Основная статистика -->
        <div class="card">
            <h2>📊 Статистика за {{ data.period_days }} дней</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value" id="total-queries">{{ data.period_stats.total_queries }}</div>
                    <div class="stat-label">Всего запросов</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="answer-rate">{{ "%.1f"|format(data.period_stats.answer_rate) }}%</div>
                    <div class="stat-label">Процент ответов</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="avg-confidence">{{ "%.3f"|format(data.period_stats.avg_confidence) }}</div>
                    <div class="stat-label">Средняя уверенность</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="response-time">{{ "%.0f"|format(data.period_stats.avg_response_time_ms) }}ms</div>
                    <div class="stat-label">Время ответа</div>
                </div>
            </div>
        </div>

        <!-- Общая статистика -->
        <div class="card">
            <h2>📈 Общая статистика</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{{ data.overall_stats.total_queries }}</div>
                    <div class="stat-label">Всего запросов</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{{ data.overall_stats.knowledge_gaps }}</div>
                    <div class="stat-label">Пробелы в знаниях</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{{ "%.1f"|format(data.overall_stats.answer_rate) }}%</div>
                    <div class="stat-label">Общий % ответов</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{{ "%.3f"|format(data.overall_stats.avg_confidence) }}</div>
                    <div class="stat-label">Общая уверенность</div>
                </div>
            </div>
        </div>

        <!-- Топ неотвеченных запросов -->
        <div class="card">
            <h2>❓ Топ неотвеченных запросов</h2>
            <div class="query-list">
                {% for query in data.top_unanswered %}
                <div class="query-item">
                    <strong>{{ query.query }}</strong>
                    <span style="float: right; color: #f44336;">{{ query.frequency }} раз</span>
                </div>
                {% endfor %}
                {% if not data.top_unanswered %}
                <div class="query-item">✅ Нет неотвеченных запросов</div>
                {% endif %}
            </div>
        </div>

        <!-- Пробелы в знаниях -->
        <div class="card">
            <h2>🔍 Пробелы в знаниях</h2>
            <div class="query-list">
                {% for gap in data.knowledge_gaps %}
                <div class="query-item priority-{{ gap.priority }}">
                    <strong>{{ gap.pattern }}</strong> ({{ gap.category }})
                    <span style="float: right;">{{ gap.frequency }} раз</span>
                    <div style="font-size: 0.9em; color: #666;">Приоритет: {{ gap.priority }}</div>
                </div>
                {% endfor %}
                {% if not data.knowledge_gaps %}
                <div class="query-item">✅ Пробелы в знаниях не найдены</div>
                {% endif %}
            </div>
        </div>

        <!-- Распределение по источникам -->
        <div class="card">
            <h2>📚 Источники ответов</h2>
            {% for source in data.source_distribution %}
            <div class="query-item">
                <strong>{{ source.source or 'Неизвестно' }}</strong>
                <span style="float: right;">{{ source.count }} запросов</span>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""


class AnalyticsDashboard:
    """Веб-dashboard для аналитики"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.app = None

        if not FLASK_AVAILABLE:
            logger.warning("Flask не установлен - dashboard недоступен")
            return

        self.app = Flask(__name__)
        self._setup_routes()
        logger.info(f"Analytics Dashboard инициализирован на {host}:{port}")

    def _setup_routes(self):
        """Настройка маршрутов Flask"""

        @self.app.route("/")
        def dashboard():
            """Главная страница dashboard"""
            try:
                data = analytics_service.get_analytics_summary(days=7)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                return render_template_string(DASHBOARD_HTML, data=data, timestamp=timestamp)
            except Exception as e:
                logger.error(f"Ошибка при получении данных для dashboard: {e}")
                return f"Ошибка: {e}", 500

        @self.app.route("/api/analytics")
        def api_analytics():
            """API endpoint для получения аналитики"""
            try:
                days = request.args.get("days", 7, type=int)
                data = analytics_service.get_analytics_summary(days=days)
                return jsonify(data)
            except Exception as e:
                logger.error(f"Ошибка API аналитики: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/suggestions")
        def api_suggestions():
            """API endpoint для получения предложений по улучшению"""
            try:
                suggestions = analytics_service.get_improvement_suggestions()
                return jsonify(suggestions)
            except Exception as e:
                logger.error(f"Ошибка API предложений: {e}")
                return jsonify({"error": str(e)}), 500

    def run(self, debug: bool = False):
        """Запуск dashboard сервера"""
        if not self.app:
            logger.error("Flask не доступен - невозможно запустить dashboard")
            return

        try:
            logger.info(f"Запуск Analytics Dashboard на http://{self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)
        except Exception as e:
            logger.error(f"Ошибка при запуске dashboard: {e}")


def create_simple_report() -> str:
    """Создает простой текстовый отчет (альтернатива веб-dashboard)"""
    try:
        data = analytics_service.get_analytics_summary(days=7)
        suggestions = analytics_service.get_improvement_suggestions()

        report = f"""
📊 ОТЧЕТ ПО АНАЛИТИКЕ AI БОТА
Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 ОБЩАЯ СТАТИСТИКА:
• Всего запросов: {data['overall_stats']['total_queries']}
• Процент ответов: {data['overall_stats']['answer_rate']:.1f}%
• Средняя уверенность: {data['overall_stats']['avg_confidence']:.3f}
• Пробелы в знаниях: {data['overall_stats']['knowledge_gaps']}

📅 СТАТИСТИКА ЗА 7 ДНЕЙ:
• Запросов: {data['period_stats']['total_queries']}
• Отвечено: {data['period_stats']['answered_queries']}
• Процент ответов: {data['period_stats']['answer_rate']:.1f}%
• Среднее время ответа: {data['period_stats']['avg_response_time_ms']:.0f}ms

❓ ТОП НЕОТВЕЧЕННЫХ ЗАПРОСОВ:
"""

        for i, query in enumerate(data["top_unanswered"][:5], 1):
            report += f"{i}. {query['query']} ({query['frequency']} раз)\n"

        if not data["top_unanswered"]:
            report += "✅ Нет неотвеченных запросов\n"

        report += "\n🔍 ПРОБЕЛЫ В ЗНАНИЯХ:\n"
        for i, gap in enumerate(data["knowledge_gaps"][:5], 1):
            report += f"{i}. {gap['pattern']} (категория: {gap['category']}, приоритет: {gap['priority']}) - {gap['frequency']} раз\n"

        if not data["knowledge_gaps"]:
            report += "✅ Пробелы в знаниях не найдены\n"

        report += "\n💡 ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ:\n"
        for i, suggestion in enumerate(suggestions[:3], 1):
            report += f"{i}. [{suggestion['priority'].upper()}] {suggestion['description']}\n"

        if not suggestions:
            report += "✅ Все работает отлично - предложений нет\n"

        return report

    except Exception as e:
        logger.error(f"Ошибка при создании отчета: {e}")
        return f"Ошибка при создании отчета: {e}"


# Глобальный экземпляр dashboard
dashboard = AnalyticsDashboard() if FLASK_AVAILABLE else None


if __name__ == "__main__":
    # Для тестирования
    if dashboard:
        dashboard.run(debug=False)
    else:
        print("Flask не установлен. Вот текстовый отчет:")
        print(create_simple_report())
