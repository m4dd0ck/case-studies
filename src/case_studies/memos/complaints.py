"""Memo: which credit-card complaint issues a card issuer should prioritise.

Priority = complaints this period x the share that end with money back to the consumer, a
simple proxy for what each issue costs an issuer. Pairs flagged as likely relabels are quoted
by their combined change, never separately.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from case_studies.cfpb import (
    growth,
    likely_relabels,
    load_monthly,
    load_outcomes,
    monetary_relief_rate,
    period_total,
)
from case_studies.charts import bar_list, line_chart

BASE = ("2025-01", "2025-06")
NOW = ("2026-01", "2026-06")
SHORT = {
    "Problem with a purchase shown on your statement": "Disputed purchases on the statement",
    "Problem with a company's investigation into an existing problem": "Company's investigation",
    "Incorrect information on your report": "Incorrect credit report information",
    "Other features, terms, or problems": "Other features or terms",
    "Advertising and marketing, including promotional offers": "Advertising and promotions",
}


def short(issue: str) -> str:
    return SHORT.get(issue, issue)


@dataclass(frozen=True)
class Priority:
    issue: str
    complaints: int
    relief_rate: float
    change: float | None

    @property
    def money_back(self) -> float:
        """Expected complaints closed with monetary relief."""
        return self.complaints * self.relief_rate


def month_label(month: str) -> str:
    return date.fromisoformat(f"{month}-01").strftime("%b %y")


def build() -> dict[str, Any]:
    series = load_monthly()
    rates = monetary_relief_rate(load_outcomes())
    months = sorted({m for counts in series.values() for m in counts})
    totals = [sum(counts.get(m, 0) for counts in series.values()) for m in months]
    base_total = sum(period_total(c, *BASE) for c in series.values())
    now_total = sum(period_total(c, *NOW) for c in series.values())
    relabels = likely_relabels(series, BASE, NOW)
    merged = {r.rising: r for r in relabels} | {r.falling: r for r in relabels}

    priorities = []
    for issue, before, after, change in growth(series, BASE, NOW):
        if issue in merged and issue == merged[issue].falling:
            continue  # quoted together with its partner
        if issue in merged:
            relabel = merged[issue]
            partner = series[relabel.falling]
            after += period_total(partner, *NOW)
            change = relabel.combined_change
            rate = (
                rates[issue] * period_total(series[issue], *NOW)
                + rates[relabel.falling] * period_total(partner, *NOW)
            ) / after
        else:
            rate = rates.get(issue, 0.0)
        priorities.append(Priority(issue, after, rate, change))
    priorities.sort(key=lambda p: -p.money_back)
    top = priorities[:2]

    pair_chart = ""
    if relabels:
        r = relabels[0]
        rising = [series[r.rising].get(m, 0) for m in months]
        falling = [series[r.falling].get(m, 0) for m in months]
        pair_chart = line_chart(
            [month_label(m) for m in months],
            {
                "Combined": [a + b for a, b in zip(rising, falling, strict=True)],
                "Statement": rising,
                "Investigation": falling,
            },
        )
    return {
        "base_label": "January-June 2025",
        "now_label": "January-June 2026",
        "base_total": base_total,
        "now_total": now_total,
        "total_change": (now_total - base_total) / base_total,
        "months": len(months),
        "first_month": month_label(months[0]),
        "last_month": month_label(months[-1]),
        "trend_chart": line_chart(
            [month_label(m) for m in months], {"All card complaints": totals}
        ),
        "relabels": relabels,
        "pair_chart": pair_chart,
        "priorities": priorities,
        "top": top,
        "top_share": sum(p.complaints for p in top) / now_total,
        "top_money_share": sum(p.money_back for p in top) / sum(p.money_back for p in priorities),
        "priority_chart": bar_list(
            [(short(p.issue), p.money_back, f"{p.money_back:,.0f}") for p in priorities[:8]],
            highlight={short(p.issue) for p in top},
        ),
        "short": short,
        "month_name": lambda month: date.fromisoformat(f"{month}-01").strftime("%B %Y"),
    }
