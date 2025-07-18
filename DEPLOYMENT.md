# Развертывание бота "Яскравий друк"

## 🚀 Быстрый старт

### 1. Подготовка окружения

```bash
# Клонирование/копирование проекта
cd /path/to/your/bot

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка конфигурации

```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование конфигурации
nano .env
```

Обязательные настройки в `.env`:
```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_USER_IDS=your_telegram_user_id
GOOGLE_SHEETS_API_KEY=your_google_api_key
```

### 3. Подготовка данных

```bash
# Создание необходимых директорий
mkdir -p data logs converted-data/csv

# Проверка наличия файлов шаблонов
ls -la converted-data/csv/
```

### 4. Запуск бота

```bash
# Запуск в режиме разработки
python main_2.py

# Запуск в фоновом режиме
nohup python main_2.py > logs/bot.log 2>&1 &
```

## 🔧 Управление ботом

### CLI команды

```bash
# Проверка статуса
python cli.py status

# Перезагрузка шаблонов
python cli.py reload

# Перезапуск бота
python cli.py restart

# Отчет об ошибках за 24 часа
python cli.py error_report 24

# Статистика шаблонов
python cli.py template_stats
```

### Команды бота в Telegram

Для администраторов:
- `/stats` - Статистика использования
- `/reload` - Перезагрузка шаблонов
- `/health` - Проверка здоровья системы

## 🐧 Развертывание на Linux VPS

### 1. Системные требования

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python 3.8+
sudo apt install python3 python3-pip python3-venv -y

# Установка системных зависимостей
sudo apt install git curl wget -y
```

### 2. Создание пользователя

```bash
# Создание пользователя для бота
sudo useradd -m -s /bin/bash botuser
sudo su - botuser
```

### 3. Настройка проекта

```bash
# Загрузка проекта
git clone <your-repo> telegram-bot
cd telegram-bot

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка конфигурации
cp .env.example .env
nano .env
```

### 4. Systemd сервис

Создание файла сервиса:

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Содержимое файла:
```ini
[Unit]
Description=Telegram Bot Yaskravyi Druk
After=network.target

[Service]
Type=simple
User=botuser
Group=botuser
WorkingDirectory=/home/botuser/telegram-bot
Environment=PATH=/home/botuser/telegram-bot/venv/bin
ExecStart=/home/botuser/telegram-bot/venv/bin/python main_2.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 5. Запуск сервиса

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable telegram-bot

# Запуск сервиса
sudo systemctl start telegram-bot

# Проверка статуса
sudo systemctl status telegram-bot

# Просмотр логов
sudo journalctl -u telegram-bot -f
```

## 📊 Мониторинг

### 1. Логи

```bash
# Логи бота
tail -f logs/bot.log

# Логи ошибок
tail -f error_log.json

# Системные логи
sudo journalctl -u telegram-bot -f
```

### 2. Мониторинг ресурсов

```bash
# Использование памяти и CPU
htop

# Проверка процессов
ps aux | grep python

# Проверка портов
netstat -tulpn
```

### 3. Автоматическая очистка

Добавление в crontab:
```bash
crontab -e
```

Содержимое:
```cron
# Очистка старых логов каждый день в 2:00
0 2 * * * /home/botuser/telegram-bot/venv/bin/python -c "from error_monitor import cleanup_old_errors; cleanup_old_errors(7)"

# Проверка здоровья каждые 5 минут
*/5 * * * * /home/botuser/telegram-bot/venv/bin/python cli.py status > /dev/null 2>&1
```

## 🔄 Обновление

### 1. Обновление кода

```bash
# Остановка сервиса
sudo systemctl stop telegram-bot

# Обновление кода
git pull origin main

# Установка новых зависимостей
source venv/bin/activate
pip install -r requirements.txt

# Запуск сервиса
sudo systemctl start telegram-bot
```

### 2. Миграция данных

```bash
# Создание бэкапа
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/ logs/

# Применение миграций (если есть)
python cli.py migrate
```

## 🛡️ Безопасность

### 1. Файрвол

```bash
# Установка UFW
sudo apt install ufw -y

# Базовые правила
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Разрешение SSH
sudo ufw allow ssh

# Включение файрвола
sudo ufw enable
```

### 2. Ограничение доступа

```bash
# Права на файлы
chmod 600 .env
chmod 755 main_2.py
chmod -R 755 logs/

# Владелец файлов
chown -R botuser:botuser /home/botuser/telegram-bot
```

### 3. SSL/TLS (для webhook режима)

```bash
# Установка certbot
sudo apt install certbot -y

# Получение сертификата
sudo certbot certonly --standalone -d yourdomain.com
```

## 🔧 Troubleshooting

### Часто встречающиеся проблемы

1. **Бот не запускается**
   ```bash
   # Проверка конфигурации
   python cli.py status

   # Проверка зависимостей
   pip list

   # Проверка логов
   sudo journalctl -u telegram-bot -n 50
   ```

2. **Ошибки с шаблонами**
   ```bash
   # Проверка файлов
   ls -la converted-data/csv/

   # Перезагрузка шаблонов
   python cli.py reload
   ```

3. **Проблемы с памятью**
   ```bash
   # Мониторинг памяти
   free -h

   # Перезапуск бота
   sudo systemctl restart telegram-bot
   ```

### Контакты поддержки

При проблемах с развертыванием:
1. Проверьте логи
2. Убедитесь в правильности конфигурации
3. Проверьте системные требования
4. Обратитесь к документации API Telegram
