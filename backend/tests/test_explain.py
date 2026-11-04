import re

import pytest

from app.engine import explain


def row(**changes):
    base = {
        "district": "Galle",
        "label": "Tailoring & clothing",
        "n_categories": 12,
        "supply_share": 0.05,
        "demand_share": 0.11,
        "gap_score": 90,
        "saturated": False,
        "supply_visibility": "normal",
    }
    return {**base, **changes}


def numbers_in(text):
    return set(re.findall(r"\d[\d,]*(?:\.\d+)?", text))


def test_strong_gap():
    text = explain.explain_row(row())
    assert "only about 5% of mapped businesses" in text
    assert "about 11% of household spending across these 12 business types" in text
    assert "strongest gaps" in text
    assert numbers_in(text) == {"5", "11", "12"}


def test_moderate_gap():
    text = explain.explain_row(row(gap_score=50))
    assert "strongest" not in text
    assert "somewhat above" in text


def test_saturated_takes_priority_over_a_high_score():
    text = explain.explain_row(row(saturated=True, gap_score=90, supply_share=0.30, demand_share=0.20))
    assert "many businesses already serve this; the market may be crowded" in text
    assert "strongest" not in text
    assert "only" not in text


def test_low_visibility_says_so():
    text = explain.explain_row(row(supply_visibility="low", label="Tutoring & classes"))
    assert "rarely maps" in text
    assert "strongest" not in text


def test_low_visibility_and_saturated_mentions_both():
    text = explain.explain_row(row(supply_visibility="low", saturated=True))
    assert "rarely maps" in text
    assert "many businesses already serve this; the market may be crowded" in text


def test_share_that_rounds_to_zero_does_not_print_a_number():
    text = explain.explain_row(row(supply_share=0.002))
    assert "almost none of mapped businesses" in text
    assert numbers_in(text) == {"11", "12"}


def test_cost_pressure_warning():
    text = explain.cost_pressure_warning(0.153)
    assert text == "Input prices have risen about 15% over the last three months, so margins may shrink."


def test_insufficient_data_on_rate():
    text = explain.insufficient_data_reason("Monaragala", "per_10k", 1.18, 5, 60, 509_000)
    assert "Monaragala" in text
    assert numbers_in(text) == {"60", "509,000", "1.2", "5"}


def test_insufficient_data_on_total():
    text = explain.insufficient_data_reason("Mannar", "total_businesses", 6.0, 150, 66, 110_000)
    assert numbers_in(text) == {"66", "110,000", "150"}


def test_low_coverage_has_its_own_wording():
    args = ("Puttalam", "per_10k", 3.8, 5, 315, 830_000)
    low = explain.insufficient_data_reason(*args, coverage_flag="low")
    insufficient = explain.insufficient_data_reason(*args, coverage_flag="insufficient")
    assert "still incomplete" in low
    assert "still incomplete" not in insufficient
    assert numbers_in(low) == numbers_in(insufficient) == {"315", "830,000", "3.8", "5"}


def test_low_coverage_on_total_rule_has_its_own_wording():
    text = explain.insufficient_data_reason("Mannar", "total_businesses", 6.0, 150, 66, 110_000, coverage_flag="low")
    assert "still incomplete" in text
    assert numbers_in(text) == {"66", "110,000", "150"}


def test_stale_data_reason():
    text = explain.insufficient_data_reason("Galle", "stale_data", 9.0, None, 1000, 1_130_000, 75)
    assert numbers_in(text) == {"75"}


@pytest.mark.parametrize(
    "text",
    [
        explain.explain_row(row()),
        explain.explain_row(row(gap_score=50)),
        explain.explain_row(row(saturated=True)),
        explain.explain_row(row(supply_visibility="low")),
        explain.cost_pressure_warning(0.2),
        explain.insufficient_data_reason("Monaragala", "per_10k", 1.18, 5, 60, 509_000),
        explain.insufficient_data_reason("Mannar", "total_businesses", 6.0, 150, 66, 110_000),
        explain.insufficient_data_reason("Galle", "stale_data", 9.0, None, 1000, 1_130_000),
    ],
)
def test_no_promises(text):
    assert not re.search(r"profit|guarantee|succe", text, re.IGNORECASE)
