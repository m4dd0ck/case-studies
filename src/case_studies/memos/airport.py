"""Memo: when is an NYC yellow-cab driver better off waiting in the airport queue?"""

from typing import Any

from case_studies.charts import bar_list, line_chart
from case_studies.taxi import break_even_wait, load_hourly, select

AIRPORTS = ["JFK", "LaGuardia"]
UTILIZATIONS = [0.4, 0.5, 0.6]
CENTRAL = 0.5
AFTERNOON = range(12, 18)
NIGHT = range(2, 6)


def hour_label(hour: int) -> str:
    return f"{(hour - 1) % 12 + 1}{'am' if hour < 12 else 'pm'}"


def minutes(value: float) -> str:
    hours, rest = divmod(round(value), 60)
    return f"{hours}h {rest:02d}m" if hours else f"{rest}m"


def build() -> dict[str, Any]:
    rows = load_hourly()
    areas = {name: select(rows, name) for name in [*AIRPORTS, "Manhattan"]}
    waits = {
        (airport, day, u): [break_even_wait(rows, airport, day, h, u) for h in range(24)]
        for airport in AIRPORTS
        for day in ("weekday", "weekend")
        for u in UTILIZATIONS
    }

    def average(airport: str, day: str, hours: range, u: float = CENTRAL) -> float:
        return sum(waits[airport, day, u][h] for h in hours) / len(hours)

    table = [
        {
            "hour": hour_label(h),
            **{
                f"{a}_{d}": waits[a, d, CENTRAL][h]
                for a in AIRPORTS
                for d in ("weekday", "weekend")
            },
        }
        for h in range(24)
    ]
    return {
        "total_trips": sum(int(r["trips"]) for r in rows),
        "areas": areas,
        "rate_chart": bar_list(
            [
                (name, t.per_occupied_hour, f"${t.per_occupied_hour:,.0f}/hr")
                for name, t in areas.items()
            ],
            highlight=set(AIRPORTS),
        ),
        "wait_chart": line_chart(
            [hour_label(h) for h in range(24)],
            {f"{a} weekday": waits[a, "weekday", CENTRAL] for a in AIRPORTS},
            value_format="{:,.0f} min",
        ),
        "afternoon": {a: average(a, "weekday", AFTERNOON) for a in AIRPORTS},
        "night": {a: average(a, "weekday", NIGHT) for a in AIRPORTS},
        "afternoon_range": {
            a: (average(a, "weekday", AFTERNOON, 0.6), average(a, "weekday", AFTERNOON, 0.4))
            for a in AIRPORTS
        },
        "drive_back": {
            a: select(rows, "Manhattan", "weekday", AFTERNOON, to_area=a).minutes_per_trip
            for a in AIRPORTS
        },
        "table": table,
        "utilizations": UTILIZATIONS,
        "central": CENTRAL,
        "minutes": minutes,
    }
