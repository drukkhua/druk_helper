"""
Модуль для управления рабочими часами и бизнес-логикой
Определяет когда бот работает в автоматическом режиме, а когда предлагает дождаться менеджера
"""

import os
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import pytz


class BusinessHours:
    """Класс для управления рабочими часами компании"""

    def __init__(self):
        self.timezone = ZoneInfo(os.getenv("BUSINESS_TIMEZONE", "Europe/Kiev"))

        # Рабочие часы по дням недели (0=понедельник, 6=воскресенье)
        self.schedule = {
            0: {"start": time(9, 0), "end": time(18, 0)},  # Понедельник
            1: {"start": time(9, 0), "end": time(18, 0)},  # Вторник
            2: {"start": time(9, 0), "end": time(18, 0)},  # Среда
            3: {"start": time(9, 0), "end": time(18, 0)},  # Четверг
            4: {"start": time(9, 0), "end": time(18, 0)},  # Пятница
            5: {"start": time(10, 0), "end": time(15, 0)},  # Суббота
            6: None,  # Воскресенье - выходной
        }

        # Праздничные дни (формат: YYYY-MM-DD)
        self.holidays = self._load_holidays()

    def _load_holidays(self) -> List[str]:
        """Загружает список праздничных дней"""
        holidays_str = os.getenv("BUSINESS_HOLIDAYS", "")
        if holidays_str:
            return [date.strip() for date in holidays_str.split(",")]

        # Дефолтные украинские праздники 2024-2025
        return [
            "2024-01-01",  # Новый год
            "2024-01-07",  # Рождество
            "2024-03-08",  # 8 марта
            "2024-04-28",  # Пасха 2024
            "2024-04-29",  # Понедельник после Пасхи
            "2024-05-01",  # День труда
            "2024-05-09",  # День победы
            "2024-06-16",  # Троица 2024
            "2024-08-24",  # День независимости
            "2024-10-14",  # День защитника
            "2024-12-25",  # Католическое Рождество
            "2025-01-01",  # Новый год 2025
            "2025-01-07",  # Рождество 2025
        ]

    def is_business_hours(self, dt: Optional[datetime] = None) -> bool:
        """
        Проверяет, является ли указанное время рабочим

        Args:
            dt: Время для проверки. Если None, используется текущее время

        Returns:
            True если рабочее время, False иначе
        """
        if dt is None:
            dt = datetime.now(self.timezone)
        else:
            dt = dt.astimezone(self.timezone)

        # Проверяем праздники
        date_str = dt.strftime("%Y-%m-%d")
        if date_str in self.holidays:
            return False

        # Проверяем день недели
        weekday = dt.weekday()
        schedule_day = self.schedule.get(weekday)

        if schedule_day is None:  # Выходной день
            return False

        # Проверяем время
        current_time = dt.time()
        return schedule_day["start"] <= current_time <= schedule_day["end"]

    def get_next_business_time(self, dt: Optional[datetime] = None) -> datetime:
        """
        Возвращает следующее рабочее время

        Args:
            dt: Время от которого искать. Если None, используется текущее время

        Returns:
            Datetime следующего рабочего времени
        """
        if dt is None:
            dt = datetime.now(self.timezone)
        else:
            dt = dt.astimezone(self.timezone)

        # Ищем следующий рабочий день (максимум 14 дней вперед)
        for days_ahead in range(14):
            check_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            check_date = check_date.replace(day=dt.day + days_ahead)

            date_str = check_date.strftime("%Y-%m-%d")
            if date_str in self.holidays:
                continue

            weekday = check_date.weekday()
            schedule_day = self.schedule.get(weekday)

            if schedule_day is None:
                continue

            # Если это сегодня и еще не конец рабочего дня
            if days_ahead == 0 and dt.time() < schedule_day["end"]:
                return dt.replace(
                    hour=max(dt.hour, schedule_day["start"].hour),
                    minute=max(
                        dt.minute if dt.hour == schedule_day["start"].hour else 0,
                        schedule_day["start"].minute,
                    ),
                    second=0,
                    microsecond=0,
                )

            # Иначе возвращаем начало рабочего дня
            return check_date.replace(
                hour=schedule_day["start"].hour,
                minute=schedule_day["start"].minute,
                second=0,
                microsecond=0,
            )

        # Если не нашли за 14 дней, возвращаем через неделю в 9 утра
        return dt.replace(day=dt.day + 7, hour=9, minute=0, second=0, microsecond=0)

    def get_business_status_message(self, lang: str = "ukr") -> str:
        """
        Возвращает сообщение о статусе работы

        Args:
            lang: Язык сообщения ("ukr" или "rus")

        Returns:
            Текстовое сообщение о статусе
        """
        now = datetime.now(self.timezone)

        if self.is_business_hours(now):
            if lang == "ukr":
                return "🟢 Зараз робочий час. Наш менеджер онлайн!"
            else:
                return "🟢 Сейчас рабочее время. Наш менеджер онлайн!"

        next_work_time = self.get_next_business_time(now)

        if lang == "ukr":
            return (
                f"🟡 Зараз не робочий час.\n"
                f"Наш менеджер буде онлайн: {next_work_time.strftime('%d.%m.%Y о %H:%M')}"
            )
        else:
            return (
                f"🟡 Сейчас не рабочее время.\n"
                f"Наш менеджер будет онлайн: {next_work_time.strftime('%d.%m.%Y в %H:%M')}"
            )


# Глобальный экземпляр для использования в приложении
business_hours = BusinessHours()


def is_business_time() -> bool:
    """Упрощенная функция для проверки рабочего времени"""
    return business_hours.is_business_hours()


def get_business_status(lang: str = "ukr") -> str:
    """Упрощенная функция для получения статуса работы"""
    return business_hours.get_business_status_message(lang)
