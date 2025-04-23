import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('kanban.db')
        self.cursor = self.conn.cursor()

    def init_db(self):
        """Инициализация базы данных"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                planning_topic_id INTEGER
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                user_id INTEGER,
                username TEXT,
                description TEXT,
                deadline DATETIME,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (group_id) REFERENCES groups (group_id)
            )
        ''')
        self.conn.commit()

    def load_group_settings(self) -> tuple:
        """Загрузка настроек группы из базы данных"""
        self.cursor.execute('SELECT group_id, planning_topic_id FROM groups LIMIT 1')
        result = self.cursor.fetchone()
        return result if result else (None, None)

    def set_group(self, group_id: int, topic_id: int) -> None:
        """Установка группы и ID темы планёрки"""
        self.cursor.execute(
            'INSERT OR REPLACE INTO groups (group_id, planning_topic_id) VALUES (?, ?)',
            (group_id, topic_id)
        )
        self.conn.commit()

    def create_task(self, group_id: int, user_id: int, username: str, 
                   description: str, deadline: datetime) -> int:
        """Создание новой задачи"""
        self.cursor.execute('''
            INSERT INTO tasks (group_id, user_id, username, description, deadline)
            VALUES (?, ?, ?, ?, ?)
        ''', (group_id, user_id, username, description, deadline))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_user_tasks(self, user_id: int) -> list:
        """Получение задач пользователя"""
        self.cursor.execute('''
            SELECT id, description, deadline, status
            FROM tasks
            WHERE user_id = ? AND status = 'active'
        ''', (user_id,))
        return self.cursor.fetchall()

    def cancel_task(self, task_id: int) -> bool:
        """Отмена задачи"""
        self.cursor.execute('''
            UPDATE tasks
            SET status = 'cancelled'
            WHERE id = ? AND status = 'active'
        ''', (task_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_tasks_for_reminder(self) -> list:
        """Получение задач для напоминания"""
        self.cursor.execute('''
            SELECT id, group_id, username, description
            FROM tasks
            WHERE status = 'active'
            AND datetime(deadline) <= datetime('now', '+1 day')
            AND datetime(deadline) > datetime('now')
        ''')
        return self.cursor.fetchall()

    def get_group_topic_id(self, group_id: int) -> int:
        """Получение ID темы планёрки для группы"""
        self.cursor.execute('''
            SELECT planning_topic_id
            FROM groups
            WHERE group_id = ?
        ''', (group_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_all_active_tasks(self) -> list:
        """Получение всех активных задач"""
        self.cursor.execute('''
            SELECT id, group_id, user_id, username, description, deadline
            FROM tasks
            WHERE status = 'active'
        ''')
        return self.cursor.fetchall()

    def get_user_id_by_username(self, username: str) -> int:
        """Получение user_id по username"""
        self.cursor.execute('''
            SELECT user_id
            FROM tasks
            WHERE username = ?
            ORDER BY id DESC
            LIMIT 1
        ''', (username,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def __del__(self):
        """Закрытие соединения с базой данных"""
        self.conn.close() 