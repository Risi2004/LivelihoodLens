import pandas as pd
import pytest

from app import config
from app.engine.scoring import compute_gap_table, compute_shares, coverage_table


def supply_frame(rows):
    return pd.DataFrame(rows, columns=["district", "category_id", "n_businesses"])


def demand_frame(rows):
    return pd.DataFrame(rows, columns=["district", "category_id", "monthly_spend_lkr"])


def one_row(table, district, category):
    return table[(table["district"] == district) & (table["category_id"] == category)].iloc[0]


def test_shares_divide_within_each_district():
    supply = supply_frame([("A", "x", 1), ("A", "y", 3), ("B", "x", 5), ("B", "y", 5)])
    demand = demand_frame([("A", "x", 60), ("A", "y", 40), ("B", "x", 10), ("B", "y", 30)])
    shares = compute_shares(supply, demand)
    assert one_row(shares, "A", "x")["supply_share"] == pytest.approx(0.25)
    assert one_row(shares, "A", "x")["demand_share"] == pytest.approx(0.6)
    assert one_row(shares, "B", "y")["supply_share"] == pytest.approx(0.5)
    assert one_row(shares, "B", "y")["demand_share"] == pytest.approx(0.75)


def test_pair_missing_from_supply_counts_as_zero():
    supply = supply_frame([("A", "x", 4)])
    demand = demand_frame([("A", "x", 50), ("A", "y", 50)])
    row = one_row(compute_shares(supply, demand), "A", "y")
    assert row["n_businesses"] == 0
    assert row["supply_share"] == 0


def test_district_with_no_businesses_has_zero_shares_not_nan():
    supply = supply_frame([("A", "x", 0)])
    demand = demand_frame([("A", "x", 10)])
    assert one_row(compute_shares(supply, demand), "A", "x")["supply_share"] == 0


def test_gap_ratio_uses_smoothing_when_supply_is_zero():
    supply = supply_frame([("A", "x", 0), ("A", "y", 10)])
    demand = demand_frame([("A", "x", 20), ("A", "y", 80)])
    table = compute_gap_table(supply, demand)
    assert config.SMOOTHING == 0.01
    assert one_row(table, "A", "x")["gap_ratio"] == pytest.approx(0.2 / 0.01)
    assert one_row(table, "A", "y")["gap_ratio"] == pytest.approx(0.8 / 1.01)


def test_gap_score_scales_from_0_to_100():
    supply = supply_frame([("A", c, 25) for c in "wxyz"])
    demand = demand_frame([("A", "w", 10), ("A", "x", 20), ("A", "y", 30), ("A", "z", 40)])
    table = compute_gap_table(supply, demand)
    scores = {c: one_row(table, "A", c)["gap_score"] for c in "wxyz"}
    assert scores == {"w": 0, "x": 33, "y": 67, "z": 100}


def test_ties_share_an_average_rank():
    supply = supply_frame([("A", c, 25) for c in "wxyz"])
    demand = demand_frame([("A", "w", 10), ("A", "x", 20), ("A", "y", 20), ("A", "z", 50)])
    table = compute_gap_table(supply, demand)
    assert one_row(table, "A", "x")["gap_score"] == 50
    assert one_row(table, "A", "y")["gap_score"] == 50


def test_zero_demand_ranks_lowest_without_error():
    supply = supply_frame([("A", "x", 5), ("A", "y", 5)])
    demand = demand_frame([("A", "x", 0), ("A", "y", 10)])
    table = compute_gap_table(supply, demand)
    assert one_row(table, "A", "x")["gap_score"] == 0


def test_scores_compare_across_ranked_districts_only():
    supply = supply_frame([("A", "x", 5), ("A", "y", 5), ("B", "x", 5), ("B", "y", 5), ("C", "x", 1), ("C", "y", 99)])
    demand = demand_frame([("A", "x", 60), ("A", "y", 40), ("B", "x", 90), ("B", "y", 10), ("C", "x", 99), ("C", "y", 1)])
    table = compute_gap_table(supply, demand, ["A", "B"])
    assert set(table["district"]) == {"A", "B"}
    assert one_row(table, "B", "x")["gap_score"] == 100
    assert one_row(table, "B", "y")["gap_score"] == 0


def test_saturated_only_below_ratio_one():
    # supply 0.49 + 0.01 = 0.5 exactly equals demand, so x has ratio 1 and isn't saturated.
    supply = supply_frame([("A", "x", 49), ("A", "y", 51)])
    demand = demand_frame([("A", "x", 50), ("A", "y", 50)])
    table = compute_gap_table(supply, demand)
    assert not one_row(table, "A", "x")["saturated"]
    assert one_row(table, "A", "y")["saturated"]


def coverage_for(total, population):
    totals = pd.DataFrame([("A", total)], columns=["district", "total_businesses"])
    people = pd.DataFrame([("A", population)], columns=["district", "population"])
    return coverage_table(totals, people).iloc[0]


def test_adequate_at_both_exact_boundaries():
    row = coverage_for(150, 300_000)
    assert row["per_10k"] == 5
    assert row["coverage_flag"] == "adequate"
    assert row["failed_rule"] is None and row["threshold"] is None


def test_low_when_rate_passes_but_total_is_below_minimum():
    row = coverage_for(149, 100_000)
    assert row["coverage_flag"] == "low"
    assert row["failed_rule"] == "total_businesses"
    assert row["threshold"] == config.MIN_TOTAL_BUSINESSES


def test_low_just_below_adequate_rate():
    row = coverage_for(499, 1_000_000)
    assert row["coverage_flag"] == "low"
    assert row["failed_rule"] == "per_10k"
    assert row["threshold"] == config.COVERAGE_ADEQUATE


def test_low_at_exact_minimum_rate():
    row = coverage_for(300, 1_000_000)
    assert row["per_10k"] == 3
    assert row["coverage_flag"] == "low"


def test_insufficient_just_below_minimum_rate():
    row = coverage_for(299, 1_000_000)
    assert row["coverage_flag"] == "insufficient"
    assert row["failed_rule"] == "per_10k"
    assert row["threshold"] == config.COVERAGE_ADEQUATE


def test_missing_population_is_insufficient():
    totals = pd.DataFrame([("A", 500)], columns=["district", "total_businesses"])
    people = pd.DataFrame(columns=["district", "population"]).astype({"district": str, "population": float})
    assert coverage_table(totals, people).iloc[0]["coverage_flag"] == "insufficient"
