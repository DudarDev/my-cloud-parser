# -*- coding: utf-8 -*-
"""
Модуль для работы с локальной базой данных SQLite.
Поддерживает версионирование, дедупликацию, отслеживание истории изменения цен и аналитические выборки.
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_NAME = "swappa_listings.db"

def init_db(db_name: str = DB_NAME):
    """
    Инициализирует схему базы данных, создавая таблицы listings и price_history.
    """
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Таблица объявлений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                model TEXT,
                storage TEXT,
                storage_gb INTEGER,
                color TEXT,
                condition TEXT,
                price_raw TEXT,
                price_numeric REAL,
                carrier TEXT,
                battery_raw TEXT,
                battery_numeric INTEGER,
                seller TEXT,
                location TEXT,
                shipping TEXT,
                deal_score REAL,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица истории изменения цен
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_code TEXT,
                old_price REAL,
                new_price REAL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(listing_code) REFERENCES listings(code)
            )
        """)

        conn.commit()
        conn.close()
        logging.info(f"База данных '{db_name}' успешно инициализирована.")
    except Exception as e:
        logging.error(f"Ошибка при инициализации базы данных: {e}")
        raise


def save_to_db(data: List[Dict[str, Any]], db_name: str = DB_NAME) -> Dict[str, int]:
    """
    Сохраняет список объявлений в БД.
    Если объявление уже существует:
    - Обновляет last_updated_at.
    - Если цена изменилась, обновляет цену и фиксирует изменение в price_history.
    Возвращает статистику: {'inserted': X, 'updated': Y, 'price_changes': Z}
    """
    if not data:
        logging.warning("Нет данных для сохранения в БД.")
        return {'inserted': 0, 'updated': 0, 'price_changes': 0}

    stats = {'inserted': 0, 'updated': 0, 'price_changes': 0}

    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for item in data:
            code = item.get('code')
            if not code:
                continue

            new_price = item.get('price_numeric')

            # Проверяем наличие записи
            cursor.execute("SELECT id, price_numeric FROM listings WHERE code = ?", (code,))
            existing = cursor.fetchone()

            if existing is None:
                # Вставка нового объявления
                cursor.execute("""
                    INSERT INTO listings (
                        code, model, storage, storage_gb, color, condition,
                        price_raw, price_numeric, carrier, battery_raw, battery_numeric,
                        seller, location, shipping, deal_score, first_seen_at, last_updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    code,
                    item.get('model'),
                    item.get('storage'),
                    item.get('storage_gb'),
                    item.get('color'),
                    item.get('condition'),
                    item.get('price'),
                    new_price,
                    item.get('carrier'),
                    item.get('battery'),
                    item.get('battery_numeric'),
                    item.get('seller'),
                    item.get('location'),
                    item.get('shipping'),
                    item.get('deal_score'),
                    now_str,
                    now_str
                ))
                stats['inserted'] += 1
            else:
                listing_id, old_price = existing
                stats['updated'] += 1

                # Проверка изменения цены
                if old_price is not None and new_price is not None and abs(old_price - new_price) > 0.01:
                    cursor.execute("""
                        INSERT INTO price_history (listing_code, old_price, new_price, changed_at)
                        VALUES (?, ?, ?, ?)
                    """, (code, old_price, new_price, now_str))
                    stats['price_changes'] += 1

                # Обновление данных
                cursor.execute("""
                    UPDATE listings SET
                        price_raw = ?,
                        price_numeric = ?,
                        battery_raw = ?,
                        battery_numeric = ?,
                        deal_score = ?,
                        last_updated_at = ?
                    WHERE code = ?
                """, (
                    item.get('price'),
                    new_price,
                    item.get('battery'),
                    item.get('battery_numeric'),
                    item.get('deal_score'),
                    now_str,
                    code
                ))

        conn.commit()
        conn.close()
        logging.info(f"БД обновлена: добавлено={stats['inserted']}, обновлено={stats['updated']}, изменений цен={stats['price_changes']}")
        return stats
    except Exception as e:
        logging.error(f"Ошибка сохранения в БД: {e}")
        return stats


def get_price_history(db_name: str = DB_NAME, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Возвращает последние изменения цен для объявлений.
    """
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.listing_code, l.model, l.storage, p.old_price, p.new_price, p.changed_at
            FROM price_history p
            LEFT JOIN listings l ON p.listing_code = l.code
            ORDER BY p.changed_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                'code': r[0],
                'model': r[1],
                'storage': r[2],
                'old_price': r[3],
                'new_price': r[4],
                'changed_at': r[5],
                'diff': round(r[4] - r[3], 2)
            }
            for r in rows
        ]
    except Exception as e:
        logging.error(f"Ошибка при чтении истории цен: {e}")
        return []
