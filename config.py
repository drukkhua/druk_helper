import logging
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class Config:
    """Класс конфигурации бота"""

    # Основные настройки бота
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    BOT_NAME = os.getenv("BOT_NAME", "YaskravyiDrukBot")

    # Администраторы
    ADMIN_USER_IDS = [int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x]

    # Google API
    GOOGLE_SHEETS_API_KEY = os.getenv("GOOGLE_SHEETS_API_KEY")

    # Компания
    COMPANY_NAME = os.getenv("COMPANY_NAME", "Яскравий друк")
    PORTFOLIO_LINK = os.getenv("PORTFOLIO_LINK", "https://t.me/druk_portfolio")

    # Разработка
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# Backward compatibility - экспортируем переменные как раньше
BOT_TOKEN = Config.BOT_TOKEN
ADMIN_USER_IDS = Config.ADMIN_USER_IDS
PORTFOLIO_LINK = Config.PORTFOLIO_LINK
GOOGLE_SHEETS_API_KEY = Config.GOOGLE_SHEETS_API_KEY
