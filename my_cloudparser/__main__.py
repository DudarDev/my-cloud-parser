# -*- coding: utf-8 -*-
"""
Главная точка входа в пакет my_cloudparser.
Обеспечивает запуск через CLI, интеграцию модулей экспорта, базы данных и аналитического дашборда.
"""

import os
import sys
import argparse
import logging
from typing import List
from dotenv import load_dotenv

if sys.platform.startswith("win"):
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

from rich.console import Console
from rich.table import Table

# Загрузка переменных окружения
load_dotenv()

from .scraper import SwappaScraper
from .database import init_db, save_to_db, get_price_history
from .exporters import save_to_csv, save_to_xlsx, save_to_json, save_to_docx
from .analytics import calculate_statistics, display_rich_dashboard

console = Console(force_terminal=True, soft_wrap=True)

SAVERS = {
    'csv': save_to_csv,
    'xlsx': save_to_xlsx,
    'json': save_to_json,
    'docx': save_to_docx
}

def main():
    """Главная функция выполнения CLI-интерфейса."""
    parser = argparse.ArgumentParser(
        description="🚀 Swappa Pro Cloud Parser (v6.0) — продвинутый парсер объявлений Swappa.com"
    )

    parser.add_argument('--api_key', '-k', type=str, default=None,
                        help='Ваш API ключ ScrapingBee (или задайте SCRAPINGBEE_API_KEY в .env)')
    parser.add_argument('--url', '-u', type=str,
                        default="https://swappa.com/listings/apple-iphone-13-pro-max",
                        help='URL страницы для парсинга на Swappa.com')
    parser.add_argument('--html_file', '-f', type=str, default=None,
                        help='Путь к локальному HTML-файлу для автономного парсинга без интернета')
    parser.add_argument('--direct', action='store_true',
                        help='Принудительно использовать прямой HTTP-запрос в обход ScrapingBee')
    parser.add_argument('--output', '-o', type=str, default="swappa_report",
                        help="Базовое имя выходных файлов отчетов (без расширения)")
    parser.add_argument('--formats', nargs='+', default=['csv', 'xlsx', 'json', 'docx'],
                        help="Форматы экспорта через пробел: csv xlsx json docx (по умолчанию все)")
    parser.add_argument('--save_db', action='store_true',
                        help='Сохранить объявления в локальную базу данных SQLite (swappa_listings.db)')
    parser.add_argument('--history', action='store_true',
                        help='Показать историю динамики изменения цен из базы данных')
    parser.add_argument('--no_stats', action='store_true',
                        help='Отключить отображение терминального дашборда аналитики')

    args = parser.parse_args()

    # Проверка режима просмотра истории цен
    if args.history:
        history = get_price_history()
        if not history:
            console.print("[yellow]В базе данных пока нет зафиксированных изменений цен.[/yellow]")
        else:
            table = Table(title="📉 История изменения цен на Swappa", border_style="cyan")
            table.add_column("Дата", style="dim")
            table.add_column("Код", style="bold white")
            table.add_column("Модель / Память", style="cyan")
            table.add_column("Старая цена", style="red")
            table.add_column("Новая цена", style="green")
            table.add_column("Изменение ($)", style="bold yellow", justify="right")

            for h in history:
                diff_str = f"{h['diff']:+.2f}"
                table.add_row(
                    str(h['changed_at']),
                    h['code'],
                    f"{h.get('model', '')} {h.get('storage', '')}".strip(),
                    f"${h['old_price']}",
                    f"${h['new_price']}",
                    diff_str
                )
            console.print(table)
        return

    console.print("[bold cyan]Запуск Swappa Pro Cloud Parser (v6.0)...[/bold cyan]")

    # Создание скрапера
    scraper = SwappaScraper(
        api_key=args.api_key,
        use_direct=args.direct
    )

    # Запуск сбора данных
    if args.html_file:
        data = scraper.run(html_file=args.html_file)
    else:
        data = scraper.run(url=args.url)

    if not data:
        console.print("[bold red]❌ Не удалось получить или распарсить данные.[/bold red]")
        console.print("[yellow]Подсказка: Проверьте правильность URL или наличие ScrapingBee API ключа при защите Cloudflare.[/yellow]")
        return

    console.print(f"[bold green]✅ Успешно получено {len(data)} объявлений![/bold green]")

    # Анализ и статистика
    stats = scraper.statistics or calculate_statistics(data)

    # Отображение дашборда
    if not args.no_stats:
        display_rich_dashboard(data, stats)

    # Сохранение в файлы отчетов
    for fmt in args.formats:
        fmt_clean = fmt.lower().strip()
        saver_func = SAVERS.get(fmt_clean)
        if saver_func:
            filepath = f"{args.output}.{fmt_clean}"
            saver_func(data, filepath, stats=stats)
        else:
            console.print(f"[yellow]⚠️ Предупреждение: Формат '{fmt_clean}' не поддерживается.[/yellow]")

    # Сохранение в базу данных
    auto_save = os.getenv("AUTO_SAVE_DB", "false").lower() in ("true", "1")
    if args.save_db or auto_save:
        init_db()
        db_res = save_to_db(data)
        console.print(
            f"[bold cyan]💾 База данных обновлена: "
            f"новых=[green]{db_res['inserted']}[/green], "
            f"обновлено=[blue]{db_res['updated']}[/blue], "
            f"изменений цен=[yellow]{db_res['price_changes']}[/yellow][/bold cyan]"
        )

    console.print(f"[bold green]🎉 Все операции успешно завершены. Результаты сохранены с префиксом '{args.output}'.[/bold green]")


if __name__ == "__main__":
    main()
