from datetime import datetime, timedelta
from typing import List

from .logistics import RouteStats, ActivityPattern
from .predictor import Prediction, PatternAnalyzer
from .clustering import Cluster
from .temporal import TemporalPattern

DIRECTIONS = [
    'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
    'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
]


def _bearing_label(deg: float) -> str:
    return DIRECTIONS[round(deg / 22.5) % 16]


def _fmt_td(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    h, rem = divmod(td.seconds, 3600)
    m = rem // 60
    if td.days:
        return f"{td.days}д {h:02d}:{m:02d}"
    return f"{h:02d}:{m:02d}"


def _priority_label(p: Prediction) -> str:
    width_hours = (p.latest - p.earliest).total_seconds() / 3600
    if p.confidence == 'high' and width_hours < 2:
        return "!!! ПРІОРИТЕТ"
    if p.confidence in ('high', 'medium') and width_hours < 4:
        return "!! Важливо"
    return "  Можливо"


def generate_report(
    analyzer: PatternAnalyzer,
    route_stats: List[RouteStats],
    activity: ActivityPattern,
    predictions: List[Prediction],
    as_of: datetime,
) -> str:
    lines = []

    lines.append("=" * 60)
    lines.append("  АНАЛІЗ ЛОГІСТИКИ ТА ПРОГНОЗ АКТИВНОСТІ")
    lines.append(f"  Станом на: {as_of.strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("=" * 60)

    # --- База даних ---
    lines.append(f"\n[ БАЗА ДАНИХ ]")
    lines.append(f"  Подій всього : {len(analyzer.events)}")
    lines.append(f"  Кластерів    : {len(analyzer.clusters)}")
    lines.append(f"  Маршрутів    : {len(route_stats)}")

    # --- Кластери (гарячі точки) ---
    lines.append(f"\n[ ГАРЯЧІ ТОЧКИ ]")
    tp_by_id = {t.cluster_id: t for t in analyzer.temporal}
    for c in sorted(analyzer.clusters, key=lambda x: x.size, reverse=True):
        tp = tp_by_id.get(c.id)
        interval_str = ""
        if tp and tp.avg_interval:
            h = int(tp.avg_interval.total_seconds() // 3600)
            interval_str = f"  повторення ~{h}год"
        lines.append(
            f"  #{c.id}  ({c.center_lat:.4f}, {c.center_lon:.4f})"
            f"  — {c.size} уражень{interval_str}"
        )

    # --- Маршрути ---
    lines.append(f"\n[ ЛОГІСТИЧНІ МАРШРУТИ ]")
    if not route_stats:
        lines.append("  Недостатньо даних для визначення маршрутів.")
    for r in route_stats:
        direction = _bearing_label(r.bearing_deg)
        hours_str = (
            ", ".join(f"{h:02d}:xx" for h in r.peak_hours)
            if r.peak_hours else "невизначено"
        )
        lines.append(
            f"  Маршрут #{r.from_cluster}→#{r.to_cluster}"
            f"  {r.distance_km:.1f} км {direction}"
            f"  |  {r.transit_count} транзитів"
            f"  |  швидкість ~{r.avg_speed_kmh:.0f} км/год [{r.vehicle_class}]"
            f"  |  транзит ~{_fmt_td(r.avg_speed_kmh and r.distance_km / r.avg_speed_kmh * 3600 or 0)}"
            f"  |  пік активності: {hours_str}"
            f"  |  надійність: {r.reliability:.0%}"
        )

    # --- Активність по часу ---
    lines.append(f"\n[ АКТИВНІСТЬ ПО ЧАСУ ДОБИ ]")
    if activity.hour_counts:
        max_count = max(activity.hour_counts.values())
        bar_width = 20
        for h in range(24):
            count = activity.hour_counts.get(h, 0)
            bar = "█" * int(count / max_count * bar_width)
            marker = " ◄ ПІКОВА" if h in activity.peak_hours else ""
            lines.append(f"  {h:02d}:00  {bar:<{bar_width}} ({count}){marker}")

    if activity.peak_days:
        lines.append(f"\n  Найактивніші дні тижня: {', '.join(activity.peak_days)}")

    # --- Прогнози / вікна полювання ---
    lines.append(f"\n[ ВІКНА ПОЛЮВАННЯ ]")
    if not predictions:
        lines.append("  Недостатньо даних для прогнозу.")
    for p in predictions:
        priority = _priority_label(p)
        window_h = (p.latest - p.earliest).total_seconds() / 3600
        lines.append(
            f"\n  {priority}"
            f"\n  Точка #{p.cluster_id}  ({p.lat:.4f}, {p.lon:.4f})"
            f"\n  Час : {p.earliest.strftime('%d.%m %H:%M')} – {p.latest.strftime('%H:%M')}"
            f"  (вікно {window_h:.1f}год)"
            f"\n  Впевненість : {p.confidence}"
            f"\n  Причина : {p.reason}"
        )

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)
