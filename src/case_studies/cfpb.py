"""CFPB credit-card complaints: monthly counts by issue, and outcomes by issue.

Extract: the public complaint search API's aggregations, one request per month plus one per
issue. The committed snapshots are those counts, a few hundred rows.
"""

import csv
import time
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
        with MONTHLY.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["month", "issue", "complaints"])
            for start, end in _month_ends(first, last):
                payload = _aggregations(client, date_received_min=start, date_received_max=end)
                for issue, count in _buckets(payload, "issue"):
                    writer.writerow([start[:7], issue, count])
                    issues.add(issue)
        with OUTCOMES.open("w", newline="") as handle:
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
