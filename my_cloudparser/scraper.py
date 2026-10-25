# -*- coding: utf-8 -*-
"""
Профессиональный парсер Swappa.com (версия 6.0 Pro).
Включает ООП-архитектуру SwappaScraper, гибридный режим (ScrapingBee / Direct / Local HTML),
очистку и нормализацию данных, расчет метрик выгоды (deal_score).
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Импорт модулей экспорта и аналитики
from .exporters import save_to_csv, save_to_xlsx, save_to_json, save_to_docx
from .analytics import calculate_statistics

# Карта колонок по умолчанию для Swappa table#listings_table
DEFAULT_COLUMN_MAPPING = {
    "price": 1,
    "carrier": 3,
    "color": 4,
    "storage": 5,
    "model": 6,
    "condition": 7,
    "battery": 8,
    "seller": 9,
    "location": 10,
    "shipping": 12,
    "code": 13
}

# Обратная совместимость с версией 5.0
COLUMN_MAPPING = DEFAULT_COLUMN_MAPPING


class SwappaScraper:
    """
    Основной класс скрапера для Swappa.com.
    """

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_direct: bool = False,
        column_mapping: Optional[Dict[str, int]] = None,
        timeout: int = 45
    ):
        """
        :param api_key: ScrapingBee API ключ. Если не указан, берется из переменной SCRAPINGBEE_API_KEY.
        :param use_direct: Принудительный прямой запрос без ScrapingBee.
        :param column_mapping: Пользовательская карта колонок.
        :param timeout: Таймаут запроса в секундах.
        """
        self.api_key = api_key or os.getenv("SCRAPINGBEE_API_KEY")
        self.use_direct = use_direct
        self.column_mapping = column_mapping or DEFAULT_COLUMN_MAPPING
        self.timeout = timeout
        self.scraped_data: List[Dict[str, Any]] = []
        self.statistics: Dict[str, Any] = {}

    def fetch_html(self, url: str, render_js: bool = True) -> Optional[str]:
        """
        Получение HTML страницы через ScrapingBee или прямым HTTP-запросом.
        """
        if self.use_direct or not self.api_key:
            if not self.api_key and not self.use_direct:
                logging.warning("API-ключ ScrapingBee не найден в аргументах или .env. Переключение в прямой HTTP-режим...")
            return self._fetch_direct(url)
        else:
            return self._fetch_scrapingbee(url, render_js=render_js)

    def _fetch_scrapingbee(self, url: str, render_js: bool = True) -> Optional[str]:
        """Запрос через API ScrapingBee."""
        logging.info(f"Отправка запроса через ScrapingBee API к: {url}")
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true' if render_js else 'false'
        }
        try:
            response = requests.get(
                url='https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=self.timeout
            )
            if response.status_code == 200:
                logging.info("HTML успешно получен от ScrapingBee.")
                return response.text
            else:
                logging.error(f"Ошибка ScrapingBee API (код {response.status_code}): {response.text}")
                return None
        except Exception as e:
            logging.error(f"Сетевая ошибка при запросе к ScrapingBee: {e}")
            return None

    def _fetch_direct(self, url: str) -> Optional[str]:
        """Прямой запрос к сайту с маскировкой под реальный браузер."""
        logging.info(f"Прямой HTTP-запрос к: {url}")
        headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Referer": "https://swappa.com/",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1"
        }
        try:
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                logging.info("HTML успешно получен прямым запросом.")
                return response.text
            else:
                logging.warning(f"Прямой запрос вернул статус {response.status_code}. Возможно, сработала защита Cloudflare.")
                return None
        except Exception as e:
            logging.error(f"Ошибка при прямом HTTP-запросе: {e}")
            return None

    def load_from_file(self, filepath: str) -> Optional[str]:
        """Загрузка HTML из локального файла (автономный режим)."""
        logging.info(f"Загрузка HTML из локального файла: {filepath}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logging.error(f"Ошибка чтения локального файла {filepath}: {e}")
            return None

    @staticmethod
    def _clean_price(price_str: Optional[str]) -> Optional[float]:
        """Преобразует строку цены ('$1,150.00', '$599') в float."""
        if not price_str:
            return None
        cleaned = re.sub(r'[^\d.]', '', price_str)
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _clean_battery(battery_str: Optional[str]) -> Optional[int]:
        """Извлекает число процентов батареи ('85%', '92%') в int."""
        if not battery_str:
            return None
        match = re.search(r'(\d+)\s*%', battery_str)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def _clean_storage(storage_str: Optional[str]) -> Optional[int]:
        """Преобразует объем памяти в ГБ ('128 GB' -> 128, '1 TB' -> 1024)."""
        if not storage_str:
            return None
        st = storage_str.upper()
        if 'TB' in st:
            m = re.search(r'(\d+)', st)
            return int(m.group(1)) * 1024 if m else 1024
        elif 'GB' in st:
            m = re.search(r'(\d+)', st)
            return int(m.group(1)) if m else None
        return None

    def _compute_deal_scores(self, items: List[Dict[str, Any]]) -> None:
        """
        Рассчитывает показатель выгоды (deal_score: от 1 до 100).
        Основан на сравнении цены объявления с медианной ценой для аналогичной памяти и состояния.
        """
        prices = [x['price_numeric'] for x in items if x.get('price_numeric')]
        if not prices:
            return

        median_price = sum(prices) / len(prices)

        for item in items:
            p = item.get('price_numeric')
            if p is None or median_price == 0:
                item['deal_score'] = 50.0
                continue

            # Коэффициент выгоды: если цена ниже медианы на 20%, оценка ~ 80+
            diff_ratio = (median_price - p) / median_price
            base_score = 50.0 + (diff_ratio * 100.0)

            # Бонус за хорошее состояние
            cond = (item.get('condition') or '').lower()
            if 'mint' in cond:
                base_score += 10.0
            elif 'good' in cond:
                base_score += 5.0

            # Бонус за высокую батарею
            b = item.get('battery_numeric')
            if b and b >= 90:
                base_score += 5.0
            elif b and b < 80:
                base_score -= 8.0

            score = max(1.0, min(99.0, base_score))
            item['deal_score'] = round(score, 1)

    def parse_html(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Разбирает HTML страницы и возвращает обогащенный список объявлений.
        """
        if not html_content:
            return []

        logging.info("Начинаем парсинг HTML-кода Swappa...")
        soup = BeautifulSoup(html_content, 'html.parser')

        listing_elements = soup.select("table#listings_table tbody tr")
        logging.info(f"Найдено строк в таблице объявлений: {len(listing_elements)}")

        if not listing_elements:
            return []

        results = []
        max_idx = max(self.column_mapping.values())

        for idx, row in enumerate(listing_elements, 1):
            cells = row.select("td")
            if len(cells) < max_idx + 1:
                continue

            try:
                item: Dict[str, Any] = {}
                for field_name, cell_index in self.column_mapping.items():
                    raw_text = cells[cell_index].text.strip()
                    if field_name == "seller":
                        item[field_name] = raw_text.split('\n')[0].strip()
                    else:
                        item[field_name] = raw_text

                # Числовая нормализация данных
                item['price_numeric'] = self._clean_price(item.get('price'))
                item['battery_numeric'] = self._clean_battery(item.get('battery'))
                item['storage_gb'] = self._clean_storage(item.get('storage'))

                results.append(item)
            except Exception as e:
                logging.warning(f"Ошибка при разборе строки #{idx}: {e}")
                continue

        # Расчет показателей выгоды
        self._compute_deal_scores(results)

        self.scraped_data = results
        self.statistics = calculate_statistics(results)
        return results

    def run(self, url: Optional[str] = None, html_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Главный запускающий метод скрапера.
        """
        html_content = None
        if html_file:
            html_content = self.load_from_file(html_file)
        elif url:
            html_content = self.fetch_html(url)
        else:
            raise ValueError("Необходимо передать либо 'url', либо 'html_file'.")

        if html_content:
            return self.parse_html(html_content)
        else:
            logging.error("Не удалось получить содержимое HTML.")
            return []


# --- Функции обратной совместимости (для совместимости со старыми вызовами) ---

def fetch_page_html(api_key: str, url: str) -> Optional[str]:
    scraper = SwappaScraper(api_key=api_key)
    return scraper.fetch_html(url)

def parse_html_data(html_content: str) -> List[Dict[str, Any]]:
    scraper = SwappaScraper()
    return scraper.parse_html(html_content)
