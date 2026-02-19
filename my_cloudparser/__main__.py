# -*- coding: utf-8 -*-

"""
Головний виконуваний файл для пакета my_cloudparser.
Запускає парсер, обробляє аргументи командного рядка та керує збереженням даних.
"""

import argparse
import logging

# --- ВАЖЛИВО: Виправлені відносні імпорти ---
# Крапка (.) на початку вказує Python шукати файли в цій же папці (пакеті).
from .scraper import SwappaScraper
from .database import init_db, save_to_db # Припускаючи, що ви використовуєте ці функції

# --- Налаштування логування ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Словник для функцій збереження (якщо ви захочете їх додати сюди)
# Наприклад: from .savers import save_to_csv; SAVERS = {'csv': save_to_csv}
SAVERS = {} 

def main():
    """Головна функція, що керує всім процесом."""
    parser = argparse.ArgumentParser(description="Парсер оголошень з сайту Swappa.com")
    
    # --- Аргументи командного рядка ---
    parser.add_argument('--api_key', type=str, required=True, help='Ваш API ключ від ScrapingBee')
    parser.add_argument('--url', type=str, required=True, help='URL сторінки для парсингу')
    parser.add_argument('--output', type=str, default="swappa_report", help="Базове ім'я для вихідних файлів (без розширення)")
    parser.add_argument('--formats', nargs='+', default=[], help="Список форматів для збереження (напр. csv xlsx)")
    parser.add_argument('--save-db', action='store_true', help='Зберегти результати в базу даних SQLite')
    
    args = parser.parse_args()

    logging.info("Запуск парсера...")
    
    # Ініціалізація бази даних (якщо потрібно)
    if args.save_db:
        init_db()

    # Створення та запуск скрапера
    scraper = SwappaScraper(api_key=args.api_key)
    scraper.run(url=args.url)

    # Обробка та збереження результатів
    if scraper.scraped_data:
        logging.info(f"Отримано {len(scraper.scraped_data)} оголошень.")

        # Збереження у файли на основі аргументу --formats
        for file_format in args.formats:
            saver_function = SAVERS.get(file_format)
            if saver_function:
                filename = f"{args.output}.{file_format}"
                saver_function(scraper.scraped_data, filename)
            else:
                logging.warning(f"Формат '{file_format}' не підтримується.")

        # Збереження в базу даних
        if args.save_db:
            save_to_db(scraper.scraped_data)
            logging.info("Збереження в базу даних завершено.")
    else:
        logging.warning("Не вдалося отримати дані.")
        
    logging.info("Робота завершена.")


if __name__ == "__main__":
    main()
