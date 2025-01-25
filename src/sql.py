import sqlite3
from typing import Literal
from datetime import datetime, timezone
from log import log
from hashlib import sha256


def text_to_hash(text: str) -> str:
    return sha256(text.encode()).hexdigest()[:32]

def utc_time():
    '''Get the current time in UTC + 0. Format: %Y.%m.%d %H:%M:%S'''
    time = datetime.now(timezone.utc)
    return time.strftime('%Y.%m.%d %H:%M:%S')

def sql_launch():
    '''Creates tables if they do not exist'''
    connection = sqlite3.connect('assistant.db') 
    cursor = connection.cursor()
    
    # TODO: files
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
        number_of_messages INT,
        first_message TEXT,
        last_message TEXT
        )
        ''')
    
    # TODO: settings

    connection.commit()
    connection.close()


def sql_check_user(telegram_name: str, telegram_username: str, user_id: int):
    '''Adds a new user to the database if they do not exist. Otherways updates the last_message_time and number_of_messages. Nessory before each request'''
    connection = sqlite3.connect('assistant.db')
    cursor = connection.cursor()
    
    user = cursor.execute('SELECT * FROM Users WHERE user_id = ?', (user_id, )).fetchone()
    if user is None:
        log(f'new user {telegram_name} {telegram_username} {user_id}')
        time = utc_time()
        cursor.execute('INSERT INTO Users (telegram_name, telegram_username, user_id, number_of_messages, first_message, last_message) VALUES (?, ?, ?, ?, ?, ?)', (telegram_name, telegram_username, user_id, 1, time, time))

    else:
        cursor.execute('UPDATE Users SET number_of_messages = number_of_messages + 1, last_message = ? WHERE user_id = ?', (utc_time(), user_id))

    connection.commit()
    connection.close()


def sql_select_history(id: int, n: int | str = 7):
    '''Returns the last n messages from the database by id. Format [{'role' : ..., 'content': ...}, ...]'''
    connection = sqlite3.connect('assistant.db') 
    cursor = connection.cursor()

    role_content = cursor.execute('SELECT role, content FROM Messages WHERE user_id = ? ORDER BY time DESC LIMIT ?', (id, n)).fetchall()[::-1]   
    connection.close()
    
    return [{'role': i[0], 'content': i[1]} for i in role_content]


def sql_insert_message(user_id: int, role: Literal['user', 'assistant', 'system'], content: str):
    '''Add message to database. Auto-generate user_name, time and hash'''
    connection = sqlite3.connect('assistant.db') 
    cursor = connection.cursor()

    user_name = cursor.execute('SELECT telegram_name FROM Users WHERE user_id = ?', (user_id,)).fetchone()[0]

    hash = text_to_hash(content)
    cursor.execute('INSERT INTO Messages (user_name, user_id, role, content, time, message_hash) VALUES (?, ?, ?, ?, ?, ?)', (user_name, user_id, role, content, utc_time(), hash))

    connection.commit()
    connection.close()


def sql_get_message_by_hash(message_hash: str):
    '''Returns the message by hash'''
    connection = sqlite3.connect('assistant.db')
    cursor = connection.cursor()

    content = cursor.execute(f"SELECT content FROM Messages WHERE message_hash = '{message_hash}'").fetchone()[0]
    connection.close()

    return content


sql_launch()
