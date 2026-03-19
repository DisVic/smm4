# Модуль работы с базой данных SQLite

import sqlite3
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class Database:
    # Класс для работы с базой данных бота
    
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        # Получить соединение с БД
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        # Инициализация таблиц базы данных
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица анкет квалификации
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                name TEXT,
                company TEXT,
                service TEXT,
                budget TEXT,
                contact TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        ''')
        
        # Таблица состояний диалога
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dialog_states (
                telegram_id INTEGER PRIMARY KEY,
                state TEXT,
                data TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица истории сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                message_type TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица запросов к оператору
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operator_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    
    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    
    def add_or_update_user(self, telegram_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> bool:
        # Добавить или обновить пользователя
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_activity = CURRENT_TIMESTAMP
            ''', (telegram_id, username, first_name, last_name))
            
            conn.commit()
            logger.info(f"Пользователь {telegram_id} добавлен/обновлён")
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")
            return False
        finally:
            conn.close()
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        # Получить информацию о пользователе
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    # ==================== ЛИДЫ (АНКЕТЫ) ====================
    
    def save_lead(self, telegram_id: int, data: Dict[str, str]) -> bool:
        # Сохранить анкету квалификации
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO leads (telegram_id, name, company, service, budget, contact)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                telegram_id,
                data.get('name'),
                data.get('company'),
                data.get('service'),
                data.get('budget'),
                data.get('contact')
            ))
            
            conn.commit()
            logger.info(f"Анкета для {telegram_id} сохранена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении анкеты: {e}")
            return False
        finally:
            conn.close()
    
    def get_leads(self, status: str = None) -> List[Dict]:
        # Получить список лидов
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if status:
                cursor.execute(
                    'SELECT * FROM leads WHERE status = ? ORDER BY created_at DESC',
                    (status,)
                )
            else:
                cursor.execute('SELECT * FROM leads ORDER BY created_at DESC')
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def update_lead_status(self, lead_id: int, status: str) -> bool:
        # Обновить статус лида
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'UPDATE leads SET status = ? WHERE id = ?',
                (status, lead_id)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса лида: {e}")
            return False
        finally:
            conn.close()
    
    # ==================== СОСТОЯНИЯ ДИАЛОГА ====================
    
    def save_state(self, telegram_id: int, state: str, data: Dict = None):
        # Сохранить состояние диалога пользователя
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO dialog_states (telegram_id, state, data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    state = excluded.state,
                    data = excluded.data,
                    updated_at = CURRENT_TIMESTAMP
            ''', (telegram_id, state, json.dumps(data or {})))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при сохранении состояния: {e}")
        finally:
            conn.close()
    
    def get_state(self, telegram_id: int) -> Optional[Dict]:
        # Получить состояние диалога пользователя
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'SELECT state, data FROM dialog_states WHERE telegram_id = ?',
                (telegram_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'state': row['state'],
                    'data': json.loads(row['data']) if row['data'] else {}
                }
            return None
        finally:
            conn.close()
    
    def clear_state(self, telegram_id: int):
        # Очистить состояние диалога
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM dialog_states WHERE telegram_id = ?', (telegram_id,))
            conn.commit()
        finally:
            conn.close()
    
    # ==================== ИСТОРИЯ СООБЩЕНИЙ ====================
    
    def log_message(self, telegram_id: int, message_type: str, content: str):
        # Записать сообщение в историю
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO message_history (telegram_id, message_type, content)
                VALUES (?, ?, ?)
            ''', (telegram_id, message_type, content))
            conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при логировании сообщения: {e}")
        finally:
            conn.close()
    
    def get_message_history(self, telegram_id: int, limit: int = 50) -> List[Dict]:
        # Получить историю сообщений пользователя
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM message_history 
                WHERE telegram_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (telegram_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # ==================== ЗАПРОСЫ К ОПЕРАТОРУ ====================
    
    def create_operator_request(self, telegram_id: int) -> int:
        # Создать запрос к оператору
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO operator_requests (telegram_id)
                VALUES (?)
            ''', (telegram_id,))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при создании запроса к оператору: {e}")
            return -1
        finally:
            conn.close()
    
    def resolve_operator_request(self, request_id: int):
        # Отметить запрос как решённый
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE operator_requests 
                SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (request_id,))
            conn.commit()
        finally:
            conn.close()
    
    def get_pending_operator_requests(self) -> List[Dict]:
        # Получить ожидающие запросы к оператору
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT orq.*, u.username, u.first_name 
                FROM operator_requests orq
                LEFT JOIN users u ON orq.telegram_id = u.telegram_id
                WHERE orq.status = 'pending'
                ORDER BY orq.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # ==================== СТАТИСТИКА ====================
    
    def get_stats(self) -> Dict[str, int]:
        # Получить статистику бота
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            cursor.execute('SELECT COUNT(*) FROM users')
            stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM leads')
            stats['total_leads'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM leads WHERE status = "new"')
            stats['new_leads'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM operator_requests WHERE status = "pending"')
            stats['pending_requests'] = cursor.fetchone()[0]
            
            return stats
        finally:
            conn.close()