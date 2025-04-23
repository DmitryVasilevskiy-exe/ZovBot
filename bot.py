import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database import Database
from scheduler import Scheduler
from handlers import setup_handlers

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

# Проверка наличия обязательных переменных окружения
if not BOT_TOKEN:
    logger.error("BOT_TOKEN не найден в переменных окружения")
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

if not ADMIN_ID:
    logger.error("ADMIN_ID не найден в переменных окружения")
    raise ValueError("ADMIN_ID не найден в переменных окружения")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    logger.error(f"ADMIN_ID должен быть числом, получено: {ADMIN_ID}")
    raise ValueError(f"ADMIN_ID должен быть числом, получено: {ADMIN_ID}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

def main() -> None:
    """Запуск бота"""
    # Инициализация базы данных
    db = Database()
    db.init_db()

    # Инициализация планировщика
    scheduler = Scheduler(db)

    # Создание приложения с настройками таймаута
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )

    # Сохранение ADMIN_ID в bot_data
    application.bot_data['ADMIN_ID'] = ADMIN_ID

    # Загрузка настроек группы из базы данных
    group_id, topic_id = db.load_group_settings()
    if group_id and topic_id:
        application.bot_data['GROUP_ID'] = group_id
        logger.info(f"Загружены настройки группы: ID={group_id}, topic_id={topic_id}")

    # Настройка обработчиков
    setup_handlers(application, db, scheduler)

    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)

    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 