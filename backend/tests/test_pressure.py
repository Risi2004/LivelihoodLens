from datetime import timedelta

import pytest

from app.engine.pressure import cost_pressure
from tests.fixtures import TODAY, price_rows, prices_frame

BAKERY = {"price_inputs": "wheat_flour|sugar"}


def test_above_threshold_warns():
    prices = prices_frame(price_rows("wheat_flour", 120, 100) + price_rows("sugar", 110, 100))
    result = cost_pressure(BAKERY, prices, TODAY)
    assert result["pct_change"] == pytest.approx(0.15)
    assert result["warning"] is True
    assert result["items_used"] == ["wheat_flour", "sugar"]
    assert result["stale"] is False


def test_below_threshold_does_not_warn():
    prices = prices_frame(price_rows("wheat_flour", 105, 100) + price_rows("sugar", 105, 100))
    result = cost_pressure(BAKERY, prices, TODAY)
    assert result["pct_change"] == pytest.approx(0.05)
    assert result["warning"] is False


def test_exactly_at_threshold_does_not_warn():
    prices = prices_frame(price_rows("wheat_flour", 110, 100) + price_rows("sugar", 110, 100))
    assert cost_pressure(BAKERY, prices, TODAY)["warning"] is False


def test_stale_prices_give_no_warning():
    old_today = TODAY - timedelta(days=30)
    prices = prices_frame(price_rows("wheat_flour", 150, 100, old_today) + price_rows("sugar", 150, 100, old_today))
    result = cost_pressure(BAKERY, prices, TODAY)
    assert result == {"pct_change": None, "warning": False, "items_used": [], "stale": True}


def test_no_prices_at_all_count_as_stale():
    assert cost_pressure(BAKERY, prices_frame([]), TODAY)["stale"] is True


def test_item_missing_a_window_is_skipped():
    recent_only = [r for r in price_rows("sugar", 500, 100) if r[3] == 500]
    prices = prices_frame(price_rows("wheat_flour", 120, 100) + recent_only)
    result = cost_pressure(BAKERY, prices, TODAY)
    assert result["items_used"] == ["wheat_flour"]
    assert result["pct_change"] == pytest.approx(0.20)


def test_category_without_price_inputs():
    result = cost_pressure({"price_inputs": ""}, prices_frame([]), TODAY)
    assert result == {"pct_change": None, "warning": False, "items_used": [], "stale": False}


def dated_rows(days_and_prices, market="Pettah"):
    return [((TODAY - timedelta(days=d)).isoformat(), "x", market, p) for d, p in days_and_prices]


X = {"price_inputs": "x"}


@pytest.mark.parametrize("excluded_day", [14, 15])
def test_recent_window_is_exactly_the_last_14_days(excluded_day):
    rows = dated_rows([(0, 100), (13, 100), (excluded_day, 999), (80, 100)])
    assert cost_pressure(X, prices_frame(rows), TODAY)["pct_change"] == pytest.approx(0)


def test_baseline_window_includes_days_76_and_90_only():
    rows = dated_rows([(1, 100), (75, 999), (76, 100), (90, 100), (91, 999)])
    assert cost_pressure(X, prices_frame(rows), TODAY)["pct_change"] == pytest.approx(0)


def test_market_with_more_rows_does_not_count_for_more():
    # Prices never change, but B reports only one recent day. Pooling rows would show -29%.
    recent_a = [(d, 100) for d in range(14)]
    baseline_days = range(76, 91)
    rows = (
        dated_rows(recent_a + [(d, 100) for d in baseline_days], "A")
        + dated_rows([(1, 200)] + [(d, 200) for d in baseline_days], "B")
    )
    assert cost_pressure(X, prices_frame(rows), TODAY)["pct_change"] == pytest.approx(0)


def test_market_in_only_one_window_is_ignored():
    rows = dated_rows([(1, 100), (80, 100)], "A") + dated_rows([(1, 500)], "B")
    assert cost_pressure(X, prices_frame(rows), TODAY)["pct_change"] == pytest.approx(0)


def test_blank_prices_are_missing_days():
    rows = dated_rows([(1, 100), (2, float("nan")), (80, 100)])
    assert cost_pressure(X, prices_frame(rows), TODAY)["pct_change"] == pytest.approx(0)


def test_only_blank_recent_prices_count_as_stale():
    rows = dated_rows([(1, float("nan")), (80, 100)])
    assert cost_pressure(X, prices_frame(rows), TODAY)["stale"] is True


def test_markets_are_averaged():
    rows = price_rows("wheat_flour", 120, 100) + [
        (d, i, "Dambulla", p + 20) for d, i, _, p in price_rows("wheat_flour", 120, 100)
    ]
    result = cost_pressure({"price_inputs": "wheat_flour"}, prices_frame(rows), TODAY)
    assert result["pct_change"] == pytest.approx(130 / 110 - 1)
