# 🔧 Решение проблем с зависанием бота в PyCharm

## 🚨 Основные причины зависания

### 1. **Блокирующие операции**
```python
# ❌ НЕПРАВИЛЬНО - блокирует event loop
import time
import requests

def bad_handler():
    time.sleep(5)  # Блокирует весь бот!
    response = requests.get("https://api.com")  # Блокирует!

# ✅ ПРАВИЛЬНО - асинхронные операции
import asyncio
import aiohttp

async def good_handler():
    await asyncio.sleep(5)  # Не блокирует
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.com") as response:
            data = await response.json()
```

### 2. **Неправильная работа с файлами**
```python
# ❌ НЕПРАВИЛЬНО - блокирует
with open('file.txt', 'r') as f:
    data = f.read()

# ✅ ПРАВИЛЬНО - асинхронно
import aiofiles

async with aiofiles.open('file.txt', 'r') as f:
    data = await f.read()
```

### 3. **Проблемы с Google Sheets API**
```python
# ❌ НЕПРАВИЛЬНО - синхронный запрос
import requests

def sync_google_request():
    response = requests.get("https://sheets.googleapis.com/...")
    return response.json()

# ✅ ПРАВИЛЬНО - асинхронный
import aiohttp

async def async_google_request():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://sheets.googleapis.com/...") as response:
            return await response.json()
```

## 🔍 Диагностика проблем

### Запуск диагностики
```bash
# Проверка конфигурации PyCharm
python pycharm_config.py

# Запуск с отладкой
python debug_runner.py
```

### Проверка логов
```bash
# Просмотр логов
tail -f pycharm_debug.log

# Поиск ошибок
grep -i "error\|exception\|traceback" pycharm_debug.log
```

## 🛠️ Настройка PyCharm

### 1. **Конфигурация запуска**
```
Run -> Edit Configurations -> Add New -> Python

Settings:
- Script path: /path/to/Bot-answers/debug_runner.py
- Working directory: /path/to/Bot-answers
- Environment variables: BOT_TOKEN, ADMIN_USER_IDS, etc.
- Python interpreter: /path/to/Bot-answers/venv/bin/python
```

### 2. **Переменные окружения**
Создайте файл `.env` в корне проекта:
```env
BOT_TOKEN=your_bot_token_here
ADMIN_USER_IDS=123456789,987654321
GOOGLE_SHEETS_API_KEY=your_api_key_here
COMPANY_NAME=Яскравий друк
DEBUG=True
LOG_LEVEL=DEBUG
```

### 3. **Интерпретатор Python**
```
File -> Settings -> Project -> Python Interpreter
-> Add -> Existing environment
-> Выберите: /path/to/Bot-answers/venv/bin/python
```

## 🐛 Отладка зависаний

### Включение отладки asyncio
```python
import asyncio
import logging

# В начале main.py
logging.basicConfig(level=logging.DEBUG)
asyncio.get_event_loop().set_debug(True)
```

### Мониторинг задач
```python
import asyncio

async def monitor_tasks():
    while True:
        tasks = [task for task in asyncio.all_tasks() if not task.done()]
        print(f"Активных задач: {len(tasks)}")
        for task in tasks:
            print(f"  - {task.get_name()}: {task}")
        await asyncio.sleep(30)
```

### Проверка deadlocks
```python
import asyncio
import signal

def debug_signal_handler(signum, frame):
    print("=== DEBUG INFO ===")
    tasks = asyncio.all_tasks()
    for task in tasks:
        print(f"Task: {task}")
        if not task.done():
            print(f"  State: {task._state}")
            print(f"  Callbacks: {task._callbacks}")
    print("==================")

signal.signal(signal.SIGUSR1, debug_signal_handler)
```

## 🔧 Решения конкретных проблем

### Problem 1: Бот не отвечает на сообщения
**Причина**: Обработчик зависает на синхронной операции
**Решение**:
```python
# Найдите все синхронные операции в handlers.py
# Замените на асинхронные аналоги
```

### Problem 2: Бот зависает при /reload
**Причина**: Google Sheets API вызывается синхронно
**Решение**:
```python
# В google_sheets_updater.py используйте aiohttp вместо requests
```

### Problem 3: Зависание при работе с файлами
**Причина**: Синхронное чтение/запись файлов
**Решение**:
```python
# Используйте aiofiles для асинхронной работы с файлами
```

### Problem 4: Память растет постоянно
**Причина**: Утечка памяти в event loop
**Решение**:
```python
# Закрывайте ресурсы в finally блоках
# Используйте async context managers
```

## 🚀 Рекомендации для PyCharm

### 1. **Профилирование**
```python
# Добавьте в debug_runner.py
import cProfile
import pstats

def profile_bot():
    profiler = cProfile.Profile()
    profiler.enable()

    # Запуск бота
    asyncio.run(main())

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats()
```

### 2. **Память мониторинг**
```python
import psutil
import asyncio

async def memory_monitor():
    process = psutil.Process()
    while True:
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"Memory usage: {memory_mb:.1f} MB")
        await asyncio.sleep(60)
```

### 3. **Graceful shutdown**
```python
import signal
import asyncio

class BotRunner:
    def __init__(self):
        self.shutdown_event = asyncio.Event()

    def setup_signals(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print(f"Received signal {signum}")
        self.shutdown_event.set()

    async def run(self):
        # Запуск бота
        bot_task = asyncio.create_task(start_bot())

        # Ожидание сигнала завершения
        await self.shutdown_event.wait()

        # Graceful shutdown
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
```

## 📊 Чек-лист для устранения зависаний

- [ ] Все операции с сетью асинхронные
- [ ] Нет блокирующих `time.sleep()`
- [ ] Файлы читаются через `aiofiles`
- [ ] База данных использует async драйвер
- [ ] Exception handlers не блокируют
- [ ] Логирование не замедляет работу
- [ ] Graceful shutdown реализован
- [ ] Мониторинг памяти включен
- [ ] Профилирование настроено
- [ ] Переменные окружения заданы

## 🆘 Экстренные команды

```bash
# Если бот завис в PyCharm
# 1. Остановить через PyCharm (красная кнопка)
# 2. Если не помогает:
pkill -f "python.*main.py"

# Проверить процессы
ps aux | grep python

# Проверить порты
netstat -an | grep :443
```

## 📞 Техподдержка

1. **Логи**: Всегда смотрите `pycharm_debug.log`
2. **Профилирование**: Используйте cProfile для поиска узких мест
3. **Мониторинг**: Следите за использованием памяти и CPU
4. **Тестирование**: Проверяйте компоненты по отдельности

---

💡 **Помните**: Asyncio требует, чтобы ВСЕ операции были асинхронными. Одна блокирующая операция может заморозить весь бот!
