import pytest

from case_studies.taxi import break_even_wait, select


def row(area: str, to_area: str, trips: int, earnings: float, minutes: float) -> dict[str, str]:
    return {
        "area": area, "to_area": to_area, "day_type": "weekday", "hour": "17",
        "trips": str(trips), "earnings": str(earnings), "trip_minutes": str(minutes), "miles": "0",
    }  # fmt: skip


ROWS = [
    # Airport fare: $70 over 40 minutes.
    row("JFK", "Manhattan", 10, 700.0, 400.0),
    # Manhattan: $1 per occupied minute; a fare out to JFK takes 50 minutes.
    row("Manhattan", "Manhattan", 90, 1350.0, 1350.0),
    row("Manhattan", "JFK", 10, 500.0, 500.0),
]


def test_select_sums_matching_rows() -> None:
    city = select(ROWS, "Manhattan", "weekday", [17])
    assert city.trips == 100
    assert city.per_occupied_hour == pytest.approx(60.0)


def test_select_with_no_match_raises() -> None:
    with pytest.raises(ValueError, match="No trips"):
        select(ROWS, "LaGuardia")


def test_break_even_wait_follows_formula() -> None:
    # r = $1/min x 0.5; W = 70 / 0.5 - 40 + 50
    assert break_even_wait(ROWS, "JFK", "weekday", 17, 0.5) == pytest.approx(150.0)


def test_busier_city_shortens_the_worthwhile_wait() -> None:
    slow = break_even_wait(ROWS, "JFK", "weekday", 17, 0.4)
    busy = break_even_wait(ROWS, "JFK", "weekday", 17, 0.6)
    assert busy < slow
