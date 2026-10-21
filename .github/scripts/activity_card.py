import os
import re
import urllib.request
from collections import defaultdict
from datetime import date

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "text": "#e6edf3",
        "muted": "#8b949e",
        "empty": "#21262d",
        "bar_from": "#58a6ff",
        "bar_to": "#8957e5",
    },
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "text": "#1f2328",
        "muted": "#656d76",
        "empty": "#eaeef2",
        "bar_from": "#0969da",
        "bar_to": "#8250df",
    },
}

WIDTH = 840
HEIGHT = 210
PAD = 28
BARS_TOP = 98
BARS_HEIGHT = 80
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"

CELL = re.compile(r'<td[^>]*?data-ix="(\d+)"[^>]*?data-date="([\d-]+)"[^>]*?id="([^"]+)"')
TIP = re.compile(r'<tool-tip[^>]*?for="([^"]+)"[^>]*>([^<]*)</tool-tip>')
COUNT = re.compile(r"(\d+)\s+contribution")


def fetch_days(login):
    request = urllib.request.Request(
        f"https://github.com/users/{login}/contributions",
        headers={"User-Agent": "profile-activity-card"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
    counts = {}
    for cell_id, text in TIP.findall(html):
        match = COUNT.search(text)
        counts[cell_id] = int(match.group(1)) if match else 0
    return [
        (int(ix), date.fromisoformat(day), counts.get(cell_id, 0))
        for ix, day, cell_id in CELL.findall(html)
    ]


def summarize(days):
    by_week = defaultdict(list)
    for ix, day, count in days:
        by_week[ix].append((day, count))
    weeks = [
        {"start": min(d for d, _ in entries), "total": sum(c for _, c in entries)}
        for _, entries in sorted(by_week.items())
    ]
    counts = [count for _, _, count in days]
    return {
        "weeks": weeks,
        "total": sum(counts),
        "active_days": sum(1 for c in counts if c > 0),
        "best_day": max(counts),
    }


def render(stats, theme):
    t = THEMES[theme]
    weeks = stats["weeks"]
    step = (WIDTH - 2 * PAD) / len(weeks)
    bar_w = step * 0.74
    peak = max(w["total"] for w in weeks) or 1

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Contribution activity over the last year">',
        "<defs>",
        '<linearGradient id="bar" x1="0" y1="1" x2="0" y2="0">',
        f'<stop offset="0" stop-color="{t["bar_to"]}"/>',
        f'<stop offset="1" stop-color="{t["bar_from"]}"/>',
        "</linearGradient>",
        "</defs>",
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>',
    ]

    columns = [
        (stats["total"], "contributions in the last year"),
        (stats["active_days"], "active days"),
        (stats["best_day"], "best day"),
    ]
    col_x = [PAD, PAD + 300, PAD + 520]
    for (value, label), x in zip(columns, col_x):
        parts.append(
            f'<text x="{x}" y="50" font-family="{FONT}" font-size="30" font-weight="700" fill="{t["text"]}">{value:,}</text>'
        )
        parts.append(
            f'<text x="{x}" y="70" font-family="{FONT}" font-size="12" fill="{t["muted"]}">{label}</text>'
        )

    last_month = None
    for i, week in enumerate(weeks):
        x = PAD + i * step
        if week["total"] == 0:
            h = 2
            fill = t["empty"]
        else:
            h = max(4, BARS_HEIGHT * week["total"] / peak)
            fill = "url(#bar)"
        y = BARS_TOP + BARS_HEIGHT - h
        parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" rx="2.5" fill="{fill}"/>'
        )
        month = week["start"].month
        if month != last_month:
            if last_month is not None:
                parts.append(
                    f'<text x="{x:.2f}" y="{BARS_TOP + BARS_HEIGHT + 18}" font-family="{FONT}" font-size="11" fill="{t["muted"]}">{week["start"].strftime("%b")}</text>'
                )
            last_month = month

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    login = os.environ["GH_USER"]
    out_dir = os.environ.get("OUT_DIR", "dist")
    stats = summarize(fetch_days(login))
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"activity-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(stats, theme))
    print(f"total={stats['total']} active_days={stats['active_days']} best_day={stats['best_day']}")


if __name__ == "__main__":
    main()
