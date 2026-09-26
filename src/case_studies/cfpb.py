"""CFPB credit-card complaints: monthly counts by issue, and outcomes by issue.

Extract: the public complaint search API's aggregations, one request per month plus one per
issue. The committed snapshots are those counts, a few hundred rows.
"""

import csv
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import httpx

API = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
PRODUCT = "Credit card"
MONTHLY = Path("data/cfpb_card_issues_monthly.csv")
OUTCOMES = Path("data/cfpb_card_issue_outcomes.csv")


def _month_ends(first: str, last: str) -> list[tuple[str, str]]:
    start = date.fromisoformat(f"{first}-01")
    end = date.fromisoformat(f"{last}-01")
    months = []
    while start <= end:
        following = date(start.year + start.month // 12, start.month % 12 + 1, 1)
        months.append((start.isoformat(), date.fromordinal(following.toordinal() - 1).isoformat()))
        start = following
    return months


def _aggregations(client: httpx.Client, **params: str) -> dict[str, object]:
    query = {"size": "0", "product": PRODUCT, **params}
    for attempt in range(4):
        response = client.get(API, params=query, timeout=60)
        if response.status_code == 200:
            payload: dict[str, object] = response.json()
            return payload
        time.sleep(2**attempt)
    response.raise_for_status()
    raise RuntimeError("unreachable")


def _buckets(payload: dict[str, object], field: str) -> list[tuple[str, int]]:
    aggregations = payload["aggregations"]
    assert isinstance(aggregations, dict)
    buckets = aggregations[field][field]["buckets"]
    return [(bucket["key"], int(bucket["doc_count"])) for bucket in buckets]


def extract(first: str = "2024-01", last: str = "2026-06") -> tuple[Path, Path]:
    """Monthly issue counts and per-issue outcomes for credit cards (needs network)."""
    MONTHLY.parent.mkdir(parents=True, exist_ok=True)
    issues: set[str] = set()
    with httpx.Client(headers={"User-Agent": "case-studies (portfolio analysis)"}) as client:
        with MONTHLY.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["month", "issue", "complaints"])
            for start, end in _month_ends(first, last):
                payload = _aggregations(client, date_received_min=start, date_received_max=end)
                for issue, count in _buckets(payload, "issue"):
                    writer.writerow([start[:7], issue, count])
                    issues.add(issue)
        with OUTCOMES.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["issue", "company_response", "complaints"])
            window = {
                "date_received_min": f"{first}-01",
                "date_received_max": _month_ends(last, last)[0][1],
            }
            for issue in sorted(issues):
                payload = _aggregations(client, issue=issue, **window)
                for response, count in _buckets(payload, "company_response"):
                    writer.writerow([issue, response, count])
    return MONTHLY, OUTCOMES


# --- analysis -------------------------------------------------------------------------------

MONETARY = "Closed with monetary relief"


def load_monthly(path: Path = MONTHLY) -> dict[str, dict[str, int]]:
    """issue -> month -> complaints."""
    series: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            series.setdefault(row["issue"], {})[row["month"]] = int(row["complaints"])
    return series


def load_outcomes(path: Path = OUTCOMES) -> dict[str, dict[str, int]]:
    """issue -> company response -> complaints."""
    outcomes: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            outcomes.setdefault(row["issue"], {})[row["company_response"]] = int(row["complaints"])
    return outcomes


def period_total(counts: dict[str, int], first: str, last: str) -> int:
    return sum(n for month, n in counts.items() if first <= month <= last)


Growth = tuple[str, int, int, float | None]


def growth(
    series: dict[str, dict[str, int]], base: tuple[str, str], now: tuple[str, str]
) -> list[Growth]:
    """Rows of (issue, base count, current count, change) for the two periods, largest first."""
    rows: list[Growth] = []
    for issue, counts in series.items():
        before, after = period_total(counts, *base), period_total(counts, *now)
        rows.append((issue, before, after, (after - before) / before if before else None))
    return sorted(rows, key=lambda row: -row[2])


def monetary_relief_rate(outcomes: dict[str, dict[str, int]]) -> dict[str, float]:
    """Share of each issue's complaints closed with money back to the consumer."""
    return {
        issue: responses.get(MONETARY, 0) / total
        for issue, responses in outcomes.items()
        if (total := sum(responses.values()))
    }


@dataclass(frozen=True)
class Relabel:
    """Two issues where one's gain is mostly the other's loss: likely a change of label."""

    rising: str
    falling: str
    offset: float  # share of the rising issue's gain matched by the falling issue's loss
    switch_month: str  # month where the split between the two changed most
    combined_change: float  # growth of the two together, the safer figure to quote


def likely_relabels(
    series: dict[str, dict[str, int]],
    base: tuple[str, str],
    now: tuple[str, str],
    min_gain: int = 1000,
    min_step: float = 0.2,
) -> list[Relabel]:
    """Pairs where a large rise in one issue is matched by a similar fall in another, and the
    split between them jumps at one point in time rather than drifting."""
    months = sorted({month for counts in series.values() for month in counts})
    totals = {issue: (period_total(c, *base), period_total(c, *now)) for issue, c in series.items()}
    found = []
    for rising, (up_before, up_after) in totals.items():
        gain = up_after - up_before
        if gain < min_gain:
            continue
        for falling, (down_before, down_after) in totals.items():
            loss = down_before - down_after
            if falling == rising or not 0.5 <= loss / gain <= 1.5:
                continue
            switch, step = _switch(series[rising], series[falling], months)
            if step < min_step:
                continue
            combined_before, combined_after = up_before + down_before, up_after + down_after
            found.append(
                Relabel(
                    rising=rising,
                    falling=falling,
                    offset=round(min(loss / gain, 1.0), 2),
                    switch_month=switch,
                    combined_change=(combined_after - combined_before) / combined_before,
                )
            )
    return sorted(found, key=lambda relabel: -relabel.offset)


def _switch(
    rising: dict[str, int], falling: dict[str, int], months: list[str], window: int = 3
) -> tuple[str, float]:
    """Month where the rising issue's share of the pair jumps most, and the jump size.

    Compares the ``window`` months either side of each split, so a sudden relabel stands out
    while a slow drift (a real trend) does not.
    """
    shares = [
        rising.get(m, 0) / total if (total := rising.get(m, 0) + falling.get(m, 0)) else 0.0
        for m in months
    ]
    best, best_step = months[0], 0.0
    for split in range(window, len(months) - window + 1):
        before = sum(shares[split - window : split]) / window
        after = sum(shares[split : split + window]) / window
        if abs(after - before) > best_step:
            best, best_step = months[split], abs(after - before)
    return best, best_step
