import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import Database
from scheduler import Scheduler

logger = logging.getLogger(__name__)

def setup_handlers(application, db: Database, scheduler: Scheduler):
    """Настройка обработчиков команд"""
    
    async def check_admin(update: Update) -> bool:
        """Проверка, является ли пользователь администратором"""
        return update.effective_user.id == int(application.bot_data.get('ADMIN_ID'))

    async def set_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /set_group"""
        if not await check_admin(update):
            await update.message.reply_text("⛔️ Эта команда доступна только администратору")
            return

        if len(context.args) != 2:
            await update.message.reply_text("❌ Использование: /set_group [ID группы] [ID темы 'Планёрка']")
            return

        try:
            group_id = int(context.args[0])
            topic_id = int(context.args[1])

            # Получение информации о чате
            chat = await context.bot.get_chat(group_id)
            if not chat.is_forum:
                await update.message.reply_text("❌ Указанный чат не является форумом")
                return

            # Проверка доступа к теме
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    message_thread_id=topic_id,
                    text="🔄 Проверка доступа к теме 'Планёрка'"
                )
                # Сохранение ID группы и темы
                application.bot_data['GROUP_ID'] = group_id
                db.set_group(group_id, topic_id)
                await update.message.reply_text("✅ Группа успешно настроена")
            except Exception as e:
                logger.error(f"Error accessing topic: {e}")
                await update.message.reply_text("❌ Ошибка доступа к теме. Проверьте ID темы и права бота")

        except ValueError:
            await update.message.reply_text("❌ ID группы и ID темы должны быть числами")
        except Exception as e:
            logger.error(f"Error in set_group: {e}")
            await update.message.reply_text("❌ Ошибка при настройке группы")

    async def create_kanban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /create_kanban"""
        if not await check_admin(update):
            await update.message.reply_text("⛔️ Эта команда доступна только администратору")
            return

        if len(context.args) < 3:
            await update.message.reply_text(
                "❌ Использование: /create_kanban @username1 @username2 ... DD.MM.YYYY Описание задачи"
            )
            return

        try:
            # Собираем все упоминания пользователей
            usernames = []
            deadline_str = None
            description = []
            
            for arg in context.args:
                if arg.startswith('@'):
                    usernames.append(arg.lstrip('@'))
                elif not deadline_str and len(arg.split('.')) == 3:
                    deadline_str = arg
                else:
                    description.append(arg)

            if not usernames or not deadline_str:
                await update.message.reply_text(
                    "❌ Использование: /create_kanban @username1 @username2 ... DD.MM.YYYY Описание задачи"
                )
                return

            # Парсинг даты
            deadline = datetime.strptime(deadline_str, '%d.%m.%Y')
            description_text = ' '.join(description)
            
            # Создание задач для каждого пользователя
            for username in usernames:
                task_id = db.create_task(
                    group_id=application.bot_data.get('GROUP_ID'),
                    user_id=0,  # Будет заполнено при публикации
                    username=username,
                    description=description_text,
                    deadline=deadline
                )

            # Отправка сообщения в группу
            topic_id = db.get_group_topic_id(application.bot_data.get('GROUP_ID'))
            mentions = ' '.join([f'@{username}' for username in usernames])
            message = (
                f"🗓 Задача для {mentions}\n"
                f"📝 Описание: {description_text}\n"
                f"⏰ Дедлайн: {deadline_str}"
            )
            
            await context.bot.send_message(
                chat_id=application.bot_data.get('GROUP_ID'),
                message_thread_id=topic_id,
                text=message
            )

            await update.message.reply_text("✅ Задачи успешно созданы")

        except ValueError:
            await update.message.reply_text("❌ Неверный формат даты. Используйте DD.MM.YYYY")
        except Exception as e:
            logger.error(f"Error in create_kanban: {e}")
            await update.message.reply_text("❌ Ошибка при создании задач")

    async def my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /my_tasks"""
        tasks = db.get_user_tasks(update.effective_user.id)
        if not tasks:
            await update.message.reply_text("📝 У вас нет активных задач")
            return

        message = "📋 Ваши активные задачи:\n\n"
        for task_id, description, deadline, status in tasks:
            message += f"ID: {task_id}\n"
            message += f"Описание: {description}\n"
            message += f"Дедлайн: {deadline}\n\n"

        await update.message.reply_text(message)

    async def cancel_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /cancel_task"""
        if len(context.args) != 1:
            await update.message.reply_text("❌ Использование: /cancel_task [ID задачи]")
            return

        try:
            task_id = int(context.args[0])
            if db.cancel_task(task_id):
                await update.message.reply_text("✅ Задача успешно отменена")
            else:
                await update.message.reply_text("❌ Задача не найдена или уже отменена")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID задачи")

    # Регистрация обработчиков
    application.add_handler(CommandHandler("set_group", set_group))
    application.add_handler(CommandHandler("create_kanban", create_kanban))
    application.add_handler(CommandHandler("my_tasks", my_tasks))
    application.add_handler(CommandHandler("cancel_task", cancel_task)) 