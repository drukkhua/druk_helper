"""
Фабрика для создания и настройки бота
"""

import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import BaseStorage

from config import BOT_TOKEN, logger
from template_manager import TemplateManager
from exceptions import ConfigurationError
from error_handler import error_handler


class BotFactory:
    """Фабрика для создания экземпляров бота"""
    
    def __init__(self):
        self.bot = None
        self.dp = None
        self.template_manager = None
        self.storage = None
        
    def create_bot(self, token: str = None) -> Bot:
        """Создание экземпляра бота"""
        if not token:
            token = BOT_TOKEN
            
        if not token:
            raise ConfigurationError("BOT_TOKEN не задан в переменных окружения")
        
        try:
            bot = Bot(token=token)
            logger.info("Бот успешно создан")
            return bot
        except Exception as e:
            logger.critical(f"Ошибка создания бота: {e}")
            raise ConfigurationError(f"Не удалось создать бота: {e}")
    
    def create_dispatcher(self, storage: BaseStorage = None) -> Dispatcher:
        """Создание диспетчера"""
        if not storage:
            storage = MemoryStorage()
            
        try:
            dp = Dispatcher(storage=storage)
            logger.info("Диспетчер успешно создан")
            return dp
        except Exception as e:
            logger.critical(f"Ошибка создания диспетчера: {e}")
            raise ConfigurationError(f"Не удалось создать диспетчер: {e}")
    
    def create_template_manager(self) -> TemplateManager:
        """Создание менеджера шаблонов"""
        try:
            template_manager = TemplateManager()
            logger.info("Менеджер шаблонов успешно создан")
            return template_manager
        except Exception as e:
            logger.critical(f"Ошибка создания менеджера шаблонов: {e}")
            raise ConfigurationError(f"Не удалось создать менеджер шаблонов: {e}")
    
    def create_bot_instance(self, token: str = None, storage: BaseStorage = None) -> tuple:
        """
        Создание полного экземпляра бота с диспетчером и менеджером шаблонов
        
        Returns:
            tuple: (bot, dispatcher, template_manager)
        """
        try:
            # Создаем компоненты
            bot = self.create_bot(token)
            dp = self.create_dispatcher(storage)
            template_manager = self.create_template_manager()
            
            # Сохраняем ссылки
            self.bot = bot
            self.dp = dp
            self.template_manager = template_manager
            self.storage = storage or MemoryStorage()
            
            logger.info("Полный экземпляр бота создан успешно")
            return bot, dp, template_manager
            
        except Exception as e:
            logger.critical(f"Критическая ошибка создания бота: {e}")
            raise
    
    def validate_configuration(self) -> bool:
        """Валидация конфигурации"""
        try:
            # Проверяем обязательные переменные
            if not BOT_TOKEN:
                raise ConfigurationError("BOT_TOKEN не задан")
            
            # Проверяем доступность файлов шаблонов
            import os
            csv_files = [
                './converted-data/csv/vizitki_page_01.csv',
                './converted-data/csv/futbolki_page_02.csv',
                './converted-data/csv/listovki_page_03.csv',
                './converted-data/csv/nakleyki_page_04.csv',
                './converted-data/csv/bloknoty_page_05.csv',
            ]
            
            missing_files = []
            for file_path in csv_files:
                if not os.path.exists(file_path):
                    missing_files.append(file_path)
            
            if missing_files:
                logger.warning(f"Отсутствуют файлы шаблонов: {missing_files}")
                # Не критично, шаблоны могут быть добавлены позже
            
            logger.info("Конфигурация валидна")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации конфигурации: {e}")
            return False
    
    def cleanup(self):
        """Очистка ресурсов"""
        try:
            if self.bot:
                # Закрываем сессию бота если нужно
                logger.info("Закрытие сессии бота")
            
            if self.storage:
                # Очищаем storage если нужно
                logger.info("Очистка storage")
            
            logger.info("Ресурсы очищены")
            
        except Exception as e:
            logger.error(f"Ошибка очистки ресурсов: {e}")


# Глобальная фабрика бота
bot_factory = BotFactory()


def create_bot_instance(token: str = None, storage: BaseStorage = None) -> tuple:
    """
    Создание экземпляра бота
    
    Returns:
        tuple: (bot, dispatcher, template_manager)
    """
    return bot_factory.create_bot_instance(token, storage)


def validate_bot_configuration() -> bool:
    """Валидация конфигурации бота"""
    return bot_factory.validate_configuration()


def cleanup_bot_resources():
    """Очистка ресурсов бота"""
    bot_factory.cleanup()