"""Inline SVG charts for the memos: no scripts, readable in print and in email."""

from collections.abc import Mapping, Sequence
from html import escape

WIDTH = 680
PALETTE = ["#2e5e4e", "#c2410c", "#6b6b70", "#1f5f9a"]


def line_chart(
    labels: list[str],
    series: Mapping[str, Sequence[float]],
    label_every: int = 3,
    value_format: str = "{:,.0f}",
) -> str:
    """Lines over a shared x axis, with the last value of each series labelled."""
    ends = {name: f"{name} {value_format.format(values[-1])}" for name, values in series.items()}
    # Reason: end labels sit to the right of the plot, so the margin grows with the longest one.
    height, left, top, bottom = 240, 28, 14, 28
    right = max(len(text) for text in ends.values()) * 7 + 16
    peak = max(max(values) for values in series.values()) * 1.1 or 1.0
    step = (WIDTH - left - right) / max(len(labels) - 1, 1)

    def point(index: int, value: float) -> tuple[float, float]:
        return left + index * step, top + (1 - value / peak) * (height - top - bottom)

    parts = [f'<svg viewBox="0 0 {WIDTH} {height}" class="chart" role="img">']
    base = height - bottom
    parts.append(f'<line x1="{left}" x2="{WIDTH - right}" y1="{base}" y2="{base}" class="axis"/>')
    for index, label in enumerate(labels):
        # Counted back from the last label so the latest period always has a tick.
        if (len(labels) - 1 - index) % label_every == 0:
            x = point(index, 0)[0]
            parts.append(
                f'<text x="{x:.1f}" y="{height - 8}" text-anchor="middle">{escape(label)}</text>'
            )
    labels_at: list[tuple[float, str, str]] = []
    for colour, (name, values) in zip(PALETTE, series.items(), strict=False):
        coords = " ".join(
            f"{x:.1f},{y:.1f}" for x, y in (point(i, v) for i, v in enumerate(values))
        )
        parts.append(
            f'<polyline points="{coords}" fill="none" stroke="{colour}" stroke-width="2.5"/>'
        )
        labels_at.append((point(len(values) - 1, values[-1])[1], colour, ends[name]))
    end_x = WIDTH - right + 8
    last_y = -1e9
    for y, colour, text in sorted(labels_at):
        y = max(y, last_y + 14)  # push down so end labels never overlap
        last_y = y
        parts.append(
            f'<text x="{end_x:.1f}" y="{y + 4:.1f}" class="label" fill="{colour}">'
            f"{escape(text)}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def bar_list(rows: list[tuple[str, float, str]], highlight: set[str] | None = None) -> str:
    """Horizontal bars (label, value, shown); highlighted labels drawn in the accent colour."""
    row_height, label_width, value_width = 28, 300, 90
    height = row_height * len(rows) + 4
    largest = max((value for _, value, _ in rows), default=1.0) or 1.0
    span = WIDTH - label_width - value_width - 8
    parts = [f'<svg viewBox="0 0 {WIDTH} {height}" class="chart" role="img">']
    for index, (label, value, shown) in enumerate(rows):
        y = index * row_height + 4
        colour = PALETTE[1] if highlight and label in highlight else PALETTE[0]
        short = label if len(label) <= 44 else label[:42] + "…"
        parts += [
            f'<text x="0" y="{y + 16}">{escape(short)}</text>',
            f'<rect x="{label_width}" y="{y + 3}" width="{max(value, 0) / largest * span:.1f}" '
            f'height="18" rx="3" fill="{colour}"/>',
            f'<text x="{WIDTH}" y="{y + 16}" text-anchor="end" class="label">'
            f"{escape(shown)}</text>",
        ]
    parts.append("</svg>")
    return "".join(parts)
