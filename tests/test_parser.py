# -*- coding: utf-8 -*-
"""
Автоматизированный набор тестов для my_cloudparser.
"""

import os
import tempfile
import pytest
import sqlite3
import pandas as pd
from docx import Document

from my_cloudparser.scraper import SwappaScraper
from my_cloudparser.analytics import calculate_statistics
from my_cloudparser.database import init_db, save_to_db, get_price_history
from my_cloudparser.exporters import save_to_csv, save_to_xlsx, save_to_json, save_to_docx

MOCK_HTML = """
<html>
<body>
<table id="listings_table">
  <tbody>
    <tr>
      <td>Image</td>
      <td>$750.00</td>
      <td>Extra</td>
      <td>Unlocked</td>
      <td>Sierra Blue</td>
      <td>256 GB</td>
      <td>A2484</td>
      <td>Mint</td>
      <td>96%</td>
      <td>ProSeller\n5.0 rating</td>
      <td>Seattle, WA</td>
      <td>Badge</td>
      <td>Free 2-day</td>
      <td>SWP_A1</td>
    </tr>
    <tr>
      <td>Image</td>
      <td>$620.00</td>
      <td>Extra</td>
      <td>Verizon</td>
      <td>Graphite</td>
      <td>128 GB</td>
      <td>A2484</td>
      <td>Good</td>
      <td>84%</td>
      <td>BestTech\n4.9 rating</td>
      <td>Miami, FL</td>
      <td>Badge</td>
      <td>$15 Standard</td>
      <td>SWP_A2</td>
    </tr>
    <tr>
      <td>Image</td>
      <td>$590.00</td>
      <td>Extra</td>
      <td>AT&T</td>
      <td>Gold</td>
      <td>128 GB</td>
      <td>A2484</td>
      <td>Fair</td>
      <td>78%</td>
      <td>DealHunter</td>
      <td>Dallas, TX</td>
      <td>Badge</td>
      <td>Free</td>
      <td>SWP_A3</td>
    </tr>
  </tbody>
</table>
</body>
</html>
"""

def test_data_cleaning_helpers():
    scraper = SwappaScraper()
    assert scraper._clean_price("$1,249.99") == 1249.99
    assert scraper._clean_price("$550") == 550.0
    assert scraper._clean_price(None) is None

    assert scraper._clean_battery("95%") == 95
    assert scraper._clean_battery("100% capacity") == 100
    assert scraper._clean_battery("N/A") is None

    assert scraper._clean_storage("128 GB") == 128
    assert scraper._clean_storage("1 TB") == 1024
    assert scraper._clean_storage("512GB") == 512


def test_html_parsing_and_scoring():
    scraper = SwappaScraper()
    items = scraper.parse_html(MOCK_HTML)

    assert len(items) == 3

    item1 = items[0]
    assert item1['code'] == 'SWP_A1'
    assert item1['price'] == '$750.00'
    assert item1['price_numeric'] == 750.0
    assert item1['storage'] == '256 GB'
    assert item1['storage_gb'] == 256
    assert item1['seller'] == 'ProSeller'
    assert item1['battery_numeric'] == 96
    assert item1['deal_score'] > 0

    item3 = items[2]
    assert item3['battery_numeric'] == 78


def test_statistics_calculation():
    scraper = SwappaScraper()
    items = scraper.parse_html(MOCK_HTML)
    stats = calculate_statistics(items)

    assert stats['total_listings'] == 3
    assert stats['price_stats']['min'] == 590.0
    assert stats['price_stats']['max'] == 750.0
    assert stats['battery_stats']['average'] > 80
    assert stats['battery_stats']['below_80'] == 1
    assert 'Mint' in stats['by_condition']
    assert '128 GB' in stats['by_storage']
    assert len(stats['best_deals']) == 3


def test_database_and_price_history():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        init_db(db_path)

        data = [
            {
                'code': 'ITEM_1',
                'model': 'iPhone 13 Pro',
                'storage': '128 GB',
                'storage_gb': 128,
                'color': 'Blue',
                'condition': 'Mint',
                'price': '$600',
                'price_numeric': 600.0,
                'carrier': 'Unlocked',
                'battery': '90%',
                'battery_numeric': 90,
                'seller': 'Alice',
                'location': 'NY',
                'shipping': 'Free',
                'deal_score': 85.0
            }
        ]

        # Первая вставка
        res1 = save_to_db(data, db_path)
        assert res1['inserted'] == 1
        assert res1['updated'] == 0
        assert res1['price_changes'] == 0

        # Повторная вставка с ТОЙ ЖЕ ценой
        res2 = save_to_db(data, db_path)
        assert res2['inserted'] == 0
        assert res2['updated'] == 1
        assert res2['price_changes'] == 0

        # Вставка со СНИЖЕННОЙ ценой
        data[0]['price'] = '$550'
        data[0]['price_numeric'] = 550.0
        res3 = save_to_db(data, db_path)
        assert res3['updated'] == 1
        assert res3['price_changes'] == 1

        # Проверка истории цен
        history = get_price_history(db_path)
        assert len(history) == 1
        assert history[0]['old_price'] == 600.0
        assert history[0]['new_price'] == 550.0
        assert history[0]['diff'] == -50.0
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_exporters():
    scraper = SwappaScraper()
    items = scraper.parse_html(MOCK_HTML)
    stats = calculate_statistics(items)

    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_file = os.path.join(tmp_dir, "test.csv")
        xlsx_file = os.path.join(tmp_dir, "test.xlsx")
        json_file = os.path.join(tmp_dir, "test.json")
        docx_file = os.path.join(tmp_dir, "test.docx")

        save_to_csv(items, csv_file, stats)
        save_to_xlsx(items, xlsx_file, stats)
        save_to_json(items, json_file, stats)
        save_to_docx(items, docx_file, stats)

        assert os.path.exists(csv_file)
        assert os.path.exists(xlsx_file)
        assert os.path.exists(json_file)
        assert os.path.exists(docx_file)

        # Проверка содержимого CSV
        df = pd.read_csv(csv_file)
        assert len(df) == 3

        # Проверка Word
        doc = Document(docx_file)
        assert len(doc.tables) > 0


def test_offline_file_mode():
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as tmp:
        tmp.write(MOCK_HTML)
        tmp_html_path = tmp.name

    try:
        scraper = SwappaScraper()
        results = scraper.run(html_file=tmp_html_path)
        assert len(results) == 3
        assert results[0]['code'] == 'SWP_A1'
    finally:
        if os.path.exists(tmp_html_path):
            os.remove(tmp_html_path)
