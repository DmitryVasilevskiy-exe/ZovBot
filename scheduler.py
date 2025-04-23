from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
import logging
from datetime import datetime, timedelta
from database import Database

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, db: Database):
        self.db = db
        self.scheduler = AsyncIOScheduler()
        self.bot = None

    def set_bot(self, bot: Bot):
        """Установка экземпляра бота для отправки сообщений"""
        self.bot = bot

    async def check_deadlines(self):
        """Проверка дедлайнов и отправка напоминаний"""
        if not self.bot:
            logger.error("Bot instance not set")
            return

        tasks = self.db.get_tasks_for_reminder()
        for task_id, group_id, username, description in tasks:
            topic_id = self.db.get_group_topic_id(group_id)
            if not topic_id:
                logger.error(f"Topic ID not found for group {group_id}")
                continue

            try:
                message = f"⚠️ @{username}, завтра дедлайн по задаче: {description}"
                await self.bot.send_message(
                    chat_id=group_id,
                    message_thread_id=topic_id,
                    text=message
                )
            except Exception as e:
                logger.error(f"Error sending reminder: {e}")

    def start(self):
        """Запуск планировщика"""
        # Загрузка всех активных задач
        tasks = self.db.get_all_active_tasks()
        logger.info(f"Загружено {len(tasks)} активных задач")

        self.scheduler.add_job(
            self.check_deadlines,
            CronTrigger(hour=0, minute=0),  # Проверка каждый день в полночь
            id='check_deadlines'
        )
        self.scheduler.start()

    def shutdown(self):
        """Остановка планировщика"""
        self.scheduler.shutdown() 