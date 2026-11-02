"""Cost-pressure signal from prices. A separate warning, never added to the gap score."""
import pandas as pd

from app import config


def _input_items(category):
    return [item for item in category["price_inputs"].split("|") if item]


def no_pressure_signal(stale):
    return {"pct_change": None, "warning": False, "items_used": [], "stale": stale}


def _item_change(rows):
    """Change between window means, each market counting equally, or None if no market has both windows."""
    # days_ago 0 to 13 is the last 14 days
    recent_rows = rows[rows["days_ago"].between(0, config.PRESSURE_RECENT_DAYS - 1)]
    baseline_rows = rows[
        rows["days_ago"].between(config.PRESSURE_BASELINE_START_DAYS, config.PRESSURE_BASELINE_END_DAYS)
    ]
    recent = recent_rows.groupby("market")["price_lkr"].mean()
    baseline = baseline_rows.groupby("market")["price_lkr"].mean()
    # Only markets in both windows, so a market dropping out can't look like a price change.
    markets = recent.index.intersection(baseline.index)
    if markets.empty or baseline[markets].mean() <= 0:
        return None
    return recent[markets].mean() / baseline[markets].mean() - 1


def cost_pressure(category, prices, today):
    """category needs price_inputs (|-separated). Blank prices are treated as missing days."""
    items = _input_items(category)
    if not items:
        return no_pressure_signal(stale=False)

    rows = prices[prices["item"].isin(items)].dropna(subset=["price_lkr"]).copy()
    rows["days_ago"] = (pd.Timestamp(today) - pd.to_datetime(rows["date"])).dt.days
    rows = rows[rows["days_ago"] >= 0]
    if rows.empty or rows["days_ago"].min() > config.STALE_AFTER_DAYS:
        return no_pressure_signal(stale=True)

    changes = {}
    for item in items:
        change = _item_change(rows[rows["item"] == item])
        if change is not None:
            changes[item] = change
    if not changes:
        return no_pressure_signal(stale=False)

    # Rounded so a change of exactly the threshold isn't pushed over it by float error.
    pct_change = round(sum(changes.values()) / len(changes), 9)
    return {
        "pct_change": float(pct_change),
        "warning": bool(pct_change > config.PRESSURE_THRESHOLD),
        "items_used": list(changes),
        "stale": False,
    }
