"""The figures each memo quotes, pinned against the committed snapshots."""

from typing import Any

import pytest

from case_studies.memos import airport, complaints


@pytest.fixture(scope="module")
def airport_facts() -> dict[str, Any]:
    return airport.build()


@pytest.fixture(scope="module")
def complaint_facts() -> dict[str, Any]:
    return complaints.build()


def test_airport_fares_pay_more_per_occupied_hour(airport_facts: dict[str, Any]) -> None:
    areas = airport_facts["areas"]
    assert areas["JFK"].per_trip == pytest.approx(72.83, abs=0.01)
    assert areas["JFK"].per_occupied_hour > areas["Manhattan"].per_occupied_hour
    assert areas["LaGuardia"].per_occupied_hour > areas["Manhattan"].per_occupied_hour


def test_airport_thresholds_quoted_in_recommendation(airport_facts: dict[str, Any]) -> None:
    minutes = airport_facts["minutes"]
    assert minutes(airport_facts["afternoon"]["JFK"]) == "2h 18m"
    assert minutes(airport_facts["afternoon"]["LaGuardia"]) == "1h 37m"
    assert minutes(airport_facts["night"]["JFK"]) == "1h 18m"
    assert minutes(airport_facts["night"]["LaGuardia"]) == "57m"


def test_busier_drivers_should_wait_less(airport_facts: dict[str, Any]) -> None:
    busy, slow = airport_facts["afternoon_range"]["JFK"]
    assert busy < airport_facts["afternoon"]["JFK"] < slow


def test_complaint_recommendation_names_statement_and_fees(complaint_facts: dict[str, Any]) -> None:
    top = [p.issue for p in complaint_facts["top"]]
    assert top == ["Problem with a purchase shown on your statement", "Fees or interest"]
    assert all(p.change > 0 for p in complaint_facts["top"])
    assert round(complaint_facts["top_share"], 2) == 0.48
    assert round(complaint_facts["top_money_share"], 2) == 0.74


def test_one_relabel_quoted_by_combined_change(complaint_facts: dict[str, Any]) -> None:
    (relabel,) = complaint_facts["relabels"]
    assert relabel.switch_month == "2025-10"
    assert round(relabel.combined_change, 2) == 0.25
    listed = {p.issue for p in complaint_facts["priorities"]}
    assert relabel.falling not in listed


def test_total_complaints_rose_13_percent(complaint_facts: dict[str, Any]) -> None:
    assert complaint_facts["now_total"] == 48_860
    assert complaint_facts["base_total"] == 43_317
