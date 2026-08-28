import pytest

from case_studies.cfpb import growth, likely_relabels, monetary_relief_rate

MONTHS = [f"2025-{m:02d}" for m in range(1, 13)] + [f"2026-{m:02d}" for m in range(1, 7)]
BASE, NOW = ("2025-01", "2025-06"), ("2026-01", "2026-06")


def flat(value: int) -> dict[str, int]:
    return {month: value for month in MONTHS}


def test_a_label_switch_is_flagged_with_its_month() -> None:
    # Disputes move from "investigation" to "statement" in October 2025; total barely moves.
    statement = {m: (300 if m < "2025-10" else 900) for m in MONTHS}
    investigation = {m: (700 if m < "2025-10" else 120) for m in MONTHS}
    found = likely_relabels(
        {"statement": statement, "investigation": investigation, "fees": flat(400)}, BASE, NOW
    )
    assert len(found) == 1
    relabel = found[0]
    assert (relabel.rising, relabel.falling, relabel.switch_month) == (
        "statement",
        "investigation",
        "2025-10",
    )
    assert relabel.combined_change == pytest.approx(0.02)


def test_a_genuine_rise_is_not_called_a_relabel() -> None:
    rising = {m: 300 + 60 * i for i, m in enumerate(MONTHS)}
    falling = {m: 1500 - 40 * i for i, m in enumerate(MONTHS)}  # gradual drift, no step
    assert likely_relabels({"a": rising, "b": falling}, BASE, NOW) == []


def test_growth_and_relief_rates() -> None:
    rows = growth({"fees": {"2025-02": 10, "2026-02": 15}}, BASE, NOW)
    assert rows == [("fees", 10, 15, 0.5)]
    rates = monetary_relief_rate(
        {"fees": {"Closed with monetary relief": 3, "Closed with explanation": 7}}
    )
    assert rates == {"fees": 0.3}
