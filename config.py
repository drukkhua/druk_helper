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

    # AI/ML настройки
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
    AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.1"))
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "1000"))

    # RAG настройки
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "3000"))
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # Векторная база данных
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/vectorstore")
    CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "bot_knowledge_base")

    # Режим работы AI
    AI_ENABLED = os.getenv("AI_ENABLED", "False").lower() in ("true", "1", "yes")
    AI_FALLBACK_TO_TEMPLATES = os.getenv("AI_FALLBACK_TO_TEMPLATES", "True").lower() in (
        "true",
        "1",
        "yes",
    )


# Backward compatibility - экспортируем переменные как раньше
BOT_TOKEN = Config.BOT_TOKEN
ADMIN_USER_IDS = Config.ADMIN_USER_IDS
PORTFOLIO_LINK = Config.PORTFOLIO_LINK
GOOGLE_SHEETS_API_KEY = Config.GOOGLE_SHEETS_API_KEY
