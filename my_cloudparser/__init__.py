# -*- coding: utf-8 -*-
"""
my_cloudparser — Продвинутый пакет для парсинга и мониторинга цен Swappa.com.
"""

from .scraper import SwappaScraper, fetch_page_html, parse_html_data, COLUMN_MAPPING
from .database import init_db, save_to_db, get_price_history
from .analytics import calculate_statistics, display_rich_dashboard
from .exporters import save_to_csv, save_to_xlsx, save_to_json, save_to_docx

__version__ = "6.0.0"

__all__ = [
    "SwappaScraper",
    "fetch_page_html",
    "parse_html_data",
    "COLUMN_MAPPING",
    "init_db",
    "save_to_db",
    "get_price_history",
    "calculate_statistics",
    "display_rich_dashboard",
    "save_to_csv",
    "save_to_xlsx",
    "save_to_json",
    "save_to_docx"
]
