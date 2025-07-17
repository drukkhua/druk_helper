"""
Декораторы для автоматической валидации и безопасности
"""

import functools
from typing import Callable, Any
from aiogram.types import Message, CallbackQuery

from config import logger
from validation import validator


def validate_user_id(func: Callable) -> Callable:
    """
    Декоратор для валидации user_id в обработчиках
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Найти объект с user_id
        user_id = None
        for arg in args:
            if isinstance(arg, (Message, CallbackQuery)):
                user_id = arg.from_user.id
                break
        
        if user_id is None:
            logger.error("Не найден user_id для валидации")
            return
        
        # Валидация user_id
        user_validation = validator.validate_user_id(user_id)
        if not user_validation.is_valid:
            logger.error(f"Неверный user_id: {user_id}")
            return
        
        return await func(*args, **kwargs)
    
    return wrapper


def validate_callback_data(func: Callable) -> Callable:
    """
    Декоратор для валидации callback_data в обработчиках
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Найти CallbackQuery
        callback = None
        for arg in args:
            if isinstance(arg, CallbackQuery):
                callback = arg
                break
        
        if callback is None:
            logger.error("Не найден CallbackQuery для валидации")
            return
        
        # Валидация callback_data
        callback_validation = validator.validate_callback_data(callback.data)
        if not callback_validation.is_valid:
            logger.error(f"Неверный callback_data: {callback.data}")
            await callback.answer("❌ Ошибка обработки запроса")
            return
        
        return await func(*args, **kwargs)
    
    return wrapper


def validate_message_text(func: Callable) -> Callable:
    """
    Декоратор для валидации текста сообщения
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Найти Message
        message = None
        for arg in args:
            if isinstance(arg, Message):
                message = arg
                break
        
        if message is None or not message.text:
            logger.error("Не найден текст сообщения для валидации")
            return
        
        # Валидация текста сообщения
        message_validation = validator.validate_user_message(message.text)
        if not message_validation.is_valid:
            logger.error(f"Неверный текст сообщения: {message.text[:50]}...")
            await message.answer("❌ Сообщение содержит недопустимые символы")
            return
        
        return await func(*args, **kwargs)
    
    return wrapper


def rate_limit(calls_per_minute: int = 30):
    """
    Декоратор для ограничения частоты запросов
    """
    from collections import defaultdict
    from datetime import datetime, timedelta
    
    user_calls = defaultdict(list)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Найти user_id
            user_id = None
            for arg in args:
                if isinstance(arg, (Message, CallbackQuery)):
                    user_id = arg.from_user.id
                    break
            
            if user_id is None:
                return await func(*args, **kwargs)
            
            # Проверить лимит
            now = datetime.now()
            user_calls[user_id] = [
                call_time for call_time in user_calls[user_id]
                if now - call_time < timedelta(minutes=1)
            ]
            
            if len(user_calls[user_id]) >= calls_per_minute:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                
                # Отправить сообщение о превышении лимита
                for arg in args:
                    if isinstance(arg, Message):
                        await arg.answer("❌ Слишком много запросов. Подождите минуту.")
                        return
                    elif isinstance(arg, CallbackQuery):
                        await arg.answer("❌ Слишком много запросов. Подождите минуту.")
                        return
                
                return
            
            user_calls[user_id].append(now)
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def admin_only(func: Callable) -> Callable:
    """
    Декоратор для ограничения доступа только админам
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        from config import ADMIN_USER_IDS
        
        # Найти user_id
        user_id = None
        for arg in args:
            if isinstance(arg, (Message, CallbackQuery)):
                user_id = arg.from_user.id
                break
        
        if user_id is None or user_id not in ADMIN_USER_IDS:
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            
            # Отправить сообщение об отказе в доступе
            for arg in args:
                if isinstance(arg, Message):
                    await arg.answer("❌ Нет доступа")
                    return
                elif isinstance(arg, CallbackQuery):
                    await arg.answer("❌ Нет доступа")
                    return
            
            return
        
        return await func(*args, **kwargs)
    
    return wrapper