import os
import json
import sqlite3
from typing import Literal
from hashlib import sha256
from datetime import datetime, timezone
from ..config.logger import logger
from ..config.config import load_config


config = load_config()


def text_to_hash(text: str) -> str:
    return sha256(str(text).encode()).hexdigest()[:32]

def utc_time():
    '''Get the current time in UTC + 0. Format: %Y.%m.%d %H:%M:%S'''
    time = datetime.now(timezone.utc)
    return time.strftime('%Y.%m.%d %H:%M:%S')

def sql_launch():
    '''Creates tables if they do not exist'''
    connection = sqlite3.connect(config.database.path) 
    cursor = connection.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Messages (
        user_name TEXT,
        user_id INT,
        role TEXT,
        content TEXT,
        time TEXT,
        message_hash TEXT
        )
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
        telegram_name TEXT,
        telegram_username TEXT,
        user_id INTEGER PRIMARY KEY,
        hide_execution_info INTEGER DEFAULT 0,
        compound_model TEXT DEFAULT 'groq/compound',
        browser_automation_enabled INTEGER DEFAULT 0,
        current_state TEXT DEFAULT 'default',        
        number_of_messages INT,
        first_message TEXT,
        last_message TEXT
        )
        ''')
    
    # Add current_state column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE Users ADD COLUMN current_state TEXT DEFAULT "default"')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    connection.commit()
    connection.close()


def sql_check_user(telegram_name: str, telegram_username: str, user_id: int):
    '''Adds a new user to the database if they do not exist. Otherways updates the last_message_time and number_of_messages. Nessory before each request'''
    connection = sqlite3.connect(config.database.path)
    cursor = connection.cursor()
    
    user = cursor.execute('SELECT * FROM Users WHERE user_id = ?', (user_id, )).fetchone()
    if user is None:
        logger.info(f'new user {telegram_name} {telegram_username} {user_id}')
        time = utc_time()
        cursor.execute('INSERT INTO Users (telegram_name, telegram_username, user_id, number_of_messages, first_message, last_message, hide_execution_info, compound_model, browser_automation_enabled, current_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                       (telegram_name, telegram_username, user_id, 1, time, time, 0, 'groq/compound', 0, 'default'))

    else:
        cursor.execute('UPDATE Users SET number_of_messages = number_of_messages + 1, last_message = ? WHERE user_id = ?', (utc_time(), user_id))

    connection.commit()
    connection.close()


def sql_select_history(id: int, n: int | str = 10):
    '''Returns the last n messages from the database by id. Format [{'role' : ..., 'content': ...}, ...]'''
    connection = sqlite3.connect(config.database.path) 
    cursor = connection.cursor()

    role_content = cursor.execute('SELECT role, content FROM Messages WHERE user_id = ? ORDER BY time DESC LIMIT ?', (id, n)).fetchall()[::-1]   
    connection.close()
    
    return [{'role': i[0], 'content': i[1]} for i in role_content]


def sql_insert_message(user_id: int, role: Literal['user', 'assistant', 'system'], content: str):
    '''Add message to database. Auto-generate user_name, time and hash'''
    connection = sqlite3.connect(config.database.path) 
    cursor = connection.cursor()

    user_name = cursor.execute('SELECT telegram_name FROM Users WHERE user_id = ?', (user_id,)).fetchone()[0]

    hash = text_to_hash(content)
    cursor.execute('INSERT INTO Messages (user_name, user_id, role, content, time, message_hash) VALUES (?, ?, ?, ?, ?, ?)', (user_name, user_id, role, content, utc_time(), hash))

    connection.commit()
    connection.close()


def sql_get_message_by_hash(message_hash: str):
    '''Returns the message by hash'''
    connection = sqlite3.connect(config.database.path)
    cursor = connection.cursor()

    content = cursor.execute(f"SELECT content FROM Messages WHERE message_hash = '{message_hash}'").fetchone()[0]
    
    connection.close()

    return content


def sql_clear_user_history(user_id: int):
    connection = sqlite3.connect(config.database.path)
    cursor = connection.cursor()
    history = cursor.execute('SELECT role, content, time FROM Messages WHERE user_id = ? ORDER BY time', (user_id,)).fetchall()
    dialog = [{'role': i[0], 'content': i[1], 'time': i[2]} for i in history]
    if dialog:
        logs_path = os.path.join(config.base_dir, 'src', 'logs', 'deleted_dialogues.json')
        data = []
        if os.path.exists(logs_path) and os.path.getsize(logs_path) > 0:
            try:
                with open(logs_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = [data]
            except json.JSONDecodeError:
                data = []

        # append new entry and write back as a JSON array
        data.append({f"{user_id}_{utc_time()}": dialog})
        with open(logs_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    cursor.execute('DELETE FROM Messages WHERE user_id = ?', (user_id,))
    connection.commit()
    connection.close()
    logger.info(f'Cleared history for {user_id}')


def sql_get_settings(user_id: int, settings: str | list[str]) -> dict:
    connection = sqlite3.connect(config.database.path) 
    cursor = connection.cursor()

    if type(settings) == str:
        settings = [settings]
    result = {}

    for setting in settings:
        try:
            result[setting] = cursor.execute(f'SELECT {setting} FROM Users WHERE user_id = {user_id}').fetchall()[0][0]
        except:
            logger.error(f'The "{setting}" setting is not in the database.')
            result[setting] = None

    connection.close()
    return result


def sql_change_setting(user_id: int, setting_name: str, setting_value: str | int) -> bool:
    connection = sqlite3.connect(config.database.path)
    cursor = connection.cursor()

    try:
        cursor.execute(f'UPDATE Users SET {setting_name} = ? WHERE user_id = ?', (setting_value, user_id))
        connection.commit()

    except Exception as e:
        logger.error(f'There is no setting "{setting_name}" to change it: {e}')
        return False
    connection.close()
    return True


def sql_set_user_state(user_id: int, state: str) -> bool:
    '''Set user state in database'''
    return sql_change_setting(user_id=user_id, setting_name='current_state', setting_value=state)


def sql_get_user_state(user_id: int) -> str:
    '''Get user state from database'''
    result = sql_get_settings(user_id=user_id, settings=['current_state'])
    return result.get('current_state', 'default')


def sql_clear_user_state(user_id: int) -> bool:
    '''Clear user state to saved state from database'''
    saved_state = sql_get_user_state(user_id)
    return saved_state
 
sql_launch()