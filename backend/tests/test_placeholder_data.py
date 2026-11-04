"""Checks the generated placeholder files. Skipped once real pipeline output replaces them."""
import json

import pandas as pd
import pytest

from app import config

sources = json.loads(config.SOURCES_JSON.read_text()) if config.SOURCES_JSON.exists() else {}
pytestmark = pytest.mark.skipif(not sources.get("placeholder"), reason="no placeholder data")


def coverage_flags():
    totals = pd.read_csv(config.DISTRICT_TOTALS_CSV).merge(pd.read_csv(config.POPULATION_CSV), on="district")
    totals["per_10k"] = totals["total_businesses"] / totals["population"] * 10_000

    def flag(row):
        if row["per_10k"] >= config.COVERAGE_ADEQUATE and row["total_businesses"] >= config.MIN_TOTAL_BUSINESSES:
            return "adequate"
        return "low" if row["per_10k"] >= config.COVERAGE_MIN else "insufficient"

    totals["flag"] = totals.apply(flag, axis=1)
    return totals.set_index("district")


def gap_ratios():
    supply = pd.read_csv(config.SUPPLY_CSV)
    supply["supply_share"] = supply["n_businesses"] / supply.groupby("district")["n_businesses"].transform("sum")
    merged = supply.merge(pd.read_csv(config.DEMAND_CSV), on=["district", "category_id"])
    merged["gap_ratio"] = merged["demand_share"] / (merged["supply_share"] + config.SMOOTHING)
    return merged


def price_change(prices, item, last_date):
    rows = prices[prices["item"] == item]
    days_ago = (pd.Timestamp(last_date) - pd.to_datetime(rows["date"])).dt.days
    recent = rows[days_ago < config.PRESSURE_RECENT_DAYS]["price_lkr"].mean()
    baseline = rows[
        days_ago.between(config.PRESSURE_BASELINE_START_DAYS, config.PRESSURE_BASELINE_END_DAYS)
    ]["price_lkr"].mean()
    return recent / baseline - 1


def test_every_file_is_marked_placeholder():
    assert sources["placeholder"] is True
    for path in [config.SUPPLY_CSV, config.DISTRICT_TOTALS_CSV, config.POPULATION_CSV, config.DEMAND_CSV, config.PRICES_CSV]:
        assert pd.read_csv(path)["placeholder"].all()


def test_contract_columns():
    expected = {
        config.SUPPLY_CSV: "district,category_id,n_businesses,snapshot_date",
        config.DISTRICT_TOTALS_CSV: "district,total_businesses,untyped_excluded,snapshot_date",
        config.POPULATION_CSV: "district,population,year",
        config.DEMAND_CSV: "district,category_id,monthly_spend_lkr,demand_share,n_households,survey_year",
        config.PRICES_CSV: "date,item,market,price_lkr",
    }
    for path, columns in expected.items():
        assert list(pd.read_csv(path).columns) == columns.split(",") + ["placeholder"]
    assert {"osm", "hies", "prices", "population"} <= set(sources)


def test_coverage_split():
    flags = coverage_flags()
    assert set(flags.index) == set(config.DISTRICTS)
    assert flags["flag"].value_counts().to_dict() == {"adequate": 17, "low": 4, "insufficient": 4}
    assert (flags.loc[config.PILOT_DISTRICTS, "flag"] == "adequate").all()


def test_named_districts():
    flags = coverage_flags()
    assert flags.loc["Colombo", "per_10k"] == pytest.approx(20, abs=0.5)
    assert flags.loc["Kurunegala", "per_10k"] == pytest.approx(1, abs=0.1)
    assert flags.loc["Monaragala", "total_businesses"] == 60
    assert flags.loc["Monaragala", "population"] == 509_000
    assert flags.loc["Monaragala", "flag"] == "insufficient"


def test_total_counts_only_the_12_categories():
    supply = pd.read_csv(config.SUPPLY_CSV)
    assert (supply.groupby("district")["category_id"].nunique() == 12).all()
    summed = supply.groupby("district")["n_businesses"].sum()
    totals = pd.read_csv(config.DISTRICT_TOTALS_CSV).set_index("district")["total_businesses"]
    assert summed.sort_index().tolist() == totals.sort_index().tolist()


def test_demand_shares_sum_to_one():
    demand = pd.read_csv(config.DEMAND_CSV)
    assert demand.groupby("district")["demand_share"].sum().between(0.999, 1.001).all()


def test_galle_tailoring_is_the_top_gap():
    ratios = gap_ratios()
    galle = ratios[ratios["district"] == "Galle"].set_index("category_id")
    assert galle.loc["tailoring_clothing", "supply_share"] == pytest.approx(0.05, abs=0.005)
    assert galle.loc["tailoring_clothing", "demand_share"] == pytest.approx(0.11, abs=0.005)
    assert galle["gap_ratio"].idxmax() == "tailoring_clothing"


def test_prices_cover_every_item_for_120_days():
    prices = pd.read_csv(config.PRICES_CSV)
    categories = pd.read_csv(config.CATEGORIES_CSV, keep_default_na=False)
    items = {i for inputs in categories["price_inputs"] for i in inputs.split("|") if i}
    assert set(prices["item"]) == items
    assert (prices.groupby(["item", "market"])["date"].nunique() == 120).all()
    assert prices["date"].max() == sources["prices"]["last_date"]


def test_flour_and_sugar_rise_about_15_percent():
    prices = pd.read_csv(config.PRICES_CSV)
    last = sources["prices"]["last_date"]
    assert price_change(prices, "wheat_flour", last) == pytest.approx(0.15, abs=0.02)
    assert price_change(prices, "sugar", last) == pytest.approx(0.15, abs=0.02)
    assert abs(price_change(prices, "rice", last)) < 0.03


# On day 14 the last-14-days window holds no prices, so there is nothing to compare (rule 7).
@pytest.mark.parametrize("days_after_last_price", range(config.PRESSURE_RECENT_DAYS))
def test_bakery_warning_holds_while_recent_prices_exist(days_after_last_price):
    from datetime import date, timedelta

    from app.engine.pressure import cost_pressure

    today = date.fromisoformat(sources["prices"]["last_date"]) + timedelta(days=days_after_last_price)
    result = cost_pressure({"price_inputs": "wheat_flour|sugar|egg"}, pd.read_csv(config.PRICES_CSV), today)
    assert result["warning"] is True
    assert result["pct_change"] == pytest.approx(0.10, abs=0.06)
