# -*- coding: utf-8 -*-
"""
Модуль аналитики и визуализации данных для Swappa парсера.
Вычисляет рыночные показатели, медианные цены, распределения и выводит интерактивный дашборд.
"""

import sys
from typing import List, Dict, Any, Optional
import statistics

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
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

console = Console(force_terminal=True, soft_wrap=True)

def calculate_statistics(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Вычисляет сводную статистику по спарсенным объявлениям.
    """
    if not data:
        return {}

    prices = [item['price_numeric'] for item in data if item.get('price_numeric') is not None]
    batteries = [item['battery_numeric'] for item in data if item.get('battery_numeric') is not None]

    stats: Dict[str, Any] = {
        'total_listings': len(data),
        'price_stats': {},
        'battery_stats': {},
        'by_condition': {},
        'by_storage': {},
        'by_carrier': {},
        'best_deals': []
    }

    # Статистика цен
    if prices:
        stats['price_stats'] = {
            'min': min(prices),
            'max': max(prices),
            'mean': round(statistics.mean(prices), 2),
            'median': round(statistics.median(prices), 2)
        }

    # Статистика батарей
    if batteries:
        stats['battery_stats'] = {
            'average': round(statistics.mean(batteries), 1),
            'min': min(batteries),
            'max': max(batteries),
            'below_80': sum(1 for b in batteries if b < 80)
        }

    # Группировка по состоянию
    for item in data:
        cond = item.get('condition') or 'Unknown'
        stats['by_condition'][cond] = stats['by_condition'].get(cond, 0) + 1

    # Группировка по памяти
    for item in data:
        st = item.get('storage') or 'Unknown'
        stats['by_storage'][st] = stats['by_storage'].get(st, 0) + 1

    # Группировка по оператору
    for item in data:
        c = item.get('carrier') or 'Unknown'
        stats['by_carrier'][c] = stats['by_carrier'].get(c, 0) + 1

    # Лучшие предложения (сортировка по deal_score или по цене)
    valid_deals = [item for item in data if item.get('price_numeric') is not None]
    sorted_deals = sorted(valid_deals, key=lambda x: (-(x.get('deal_score') or 0), x.get('price_numeric', 999999)))
    stats['best_deals'] = sorted_deals[:5]

    return stats


def display_rich_dashboard(data: List[Dict[str, Any]], stats: Optional[Dict[str, Any]] = None):
    """
    Отображает красивый терминальный дашборд с ключевыми метриками и лучшими предложениями.
    """
    if not data:
        console.print("[yellow]Нет данных для отображения статистики.[/yellow]")
        return

    if not stats:
        stats = calculate_statistics(data)

    console.print("\n")
    console.rule("[bold cyan]📊 СВОДНЫЙ АНАЛИТИЧЕСКИЙ ДАШБОРД SWAPPA[/bold cyan]")

    p_stats = stats.get('price_stats', {})
    b_stats = stats.get('battery_stats', {})

    # 1. Карточки с ключевыми метриками
    summary_text = (
        f"[bold white]Всего предложений:[/bold white] [bold cyan]{stats['total_listings']}[/bold cyan]\n"
        f"[bold white]Медианная цена:[/bold white] [bold green]${p_stats.get('median', 'N/A')}[/bold green]\n"
        f"[bold white]Диапазон цен:[/bold white] [bold yellow]${p_stats.get('min', 'N/A')} - ${p_stats.get('max', 'N/A')}[/bold yellow]\n"
        f"[bold white]Средняя цена:[/bold white] [bold green]${p_stats.get('mean', 'N/A')}[/bold green]"
    )
    metric_panel = Panel(summary_text, title="💰 Ценовые метрики", border_style="cyan")

    battery_text = (
        f"[bold white]Средняя батарея:[/bold white] [bold green]{b_stats.get('average', 'N/A')}%[/bold green]\n"
        f"[bold white]Диапазон ёмкости:[/bold white] {b_stats.get('min', 'N/A')}% - {b_stats.get('max', 'N/A')}%\n"
        f"[bold white]Батарея <80% (сервис):[/bold white] [bold red]{b_stats.get('below_80', 0)} шт.[/bold red]"
    )
    battery_panel = Panel(battery_text, title="🔋 Состояние батарей", border_style="green")

    cond_text = "\n".join([f"• {k}: [bold cyan]{v}[/bold cyan] шт." for k, v in stats.get('by_condition', {}).items()])
    cond_panel = Panel(cond_text or "Нет данных", title="📦 Состояние устройств", border_style="magenta")

    console.print(Columns([metric_panel, battery_panel, cond_panel]))

    # 2. Таблица топ-5 лучших предложений
    deals = stats.get('best_deals', [])
    if deals:
        table = Table(title="🔥 Топ-5 лучших предложений (по выгодности / цене)", border_style="bright_blue", show_header=True)
        table.add_column("Код", style="dim", width=12)
        table.add_column("Модель / Память", style="bold white")
        table.add_column("Цвет", style="cyan")
        table.add_column("Состояние", style="magenta")
        table.add_column("Батарея", style="green")
        table.add_column("Оператор", style="yellow")
        table.add_column("Цена", style="bold green", justify="right")
        table.add_column("Выгода", style="bold red", justify="right")

        for d in deals:
            storage_str = f"{d.get('storage', '')}".strip()
            score_str = f"{d.get('deal_score', 0)}/100" if d.get('deal_score') else "N/A"
            table.add_row(
                d.get('code', 'N/A'),
                f"{d.get('model', '')} {storage_str}".strip(),
                d.get('color', 'N/A'),
                d.get('condition', 'N/A'),
                d.get('battery', 'N/A'),
                d.get('carrier', 'N/A'),
                d.get('price', 'N/A'),
                score_str
            )
        console.print(table)
        console.print("\n")
