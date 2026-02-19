# my_cloudparser/database.py

import sqlite3
import logging
from typing import List, Dict

DB_NAME = "swappa_listings.db"

def init_db():
    """
    Ініціалізує базу даних та створює таблицю 'listings',
    якщо вона ще не існує.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # SQL-запит для створення таблиці.
        # IF NOT EXISTS - запобігає помилці, якщо таблиця вже створена.
        # 'code' (код оголошення) буде унікальним, щоб уникнути дублікатів.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                price TEXT,
                carrier TEXT,
                color TEXT,
                storage TEXT,
                model TEXT,
                condition TEXT,
                battery TEXT,
                seller TEXT,
                location TEXT,
                shipping TEXT,
                code TEXT UNIQUE 
            )
        """)
        
        conn.commit()
        conn.close()
        logging.info(f"База даних '{DB_NAME}' успішно ініціалізована.")
    except Exception as e:
        logging.error(f"Помилка при ініціалізації бази даних: {e}")

def save_to_db(data: List[Dict]):
    """
    Зберігає список оголошень у базу даних.
    Ігнорує дублікати за унікальним полем 'code'.
    """
    if not data:
        logging.warning("Немає даних для збереження в базу даних.")
        return

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # INSERT OR IGNORE - команда, яка не буде додавати запис,
        # якщо оголошення з таким 'code' вже існує в таблиці.
        for item in data:
            keys = ', '.join(item.keys())
            placeholders = ', '.join(['?'] * len(item))
            query = f"INSERT OR IGNORE INTO listings ({keys}) VALUES ({placeholders})"
            cursor.execute(query, list(item.values()))

        conn.commit()
        conn.close()
        logging.info(f"Успішно збережено/оновлено {len(data)} записів у базі даних.")
    except Exception as e:
        logging.error(f"Помилка при збереженні даних в БД: {e}")