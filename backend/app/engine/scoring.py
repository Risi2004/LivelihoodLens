"""Shares, gap ratio, gap score and the coverage gate. Pure functions over DataFrames."""
import numpy as np
import pandas as pd

from app import config

KEYS = ["district", "category_id"]


def _share_within_district(df, column):
    total = df.groupby("district")[column].transform("sum")
    return (df[column] / total.where(total > 0)).fillna(0.0)


def compute_shares(supply, demand):
    """One row per district x category. A pair missing from either table counts as 0."""
    merged = supply[KEYS + ["n_businesses"]].merge(
        demand[KEYS + ["monthly_spend_lkr"]], on=KEYS, how="outer"
    )
    merged = merged.fillna({"n_businesses": 0, "monthly_spend_lkr": 0})
    merged["supply_share"] = _share_within_district(merged, "n_businesses")
    merged["demand_share"] = _share_within_district(merged, "monthly_spend_lkr")
    return merged


def _percentile_scores(values):
    """Percentile rank scaled so the lowest value is 0 and the highest 100. Ties share an average rank."""
    if len(values) <= 1:
        return pd.Series(100, index=values.index, dtype=int)
    ranks = values.rank(method="average")
    return ((ranks - 1) / (len(values) - 1) * 100).round().astype(int)


def compute_gap_table(supply, demand, ranked_districts=None):
    """Gap table for ranked_districts (all districts if None). Scores compare only rows returned."""
    table = compute_shares(supply, demand)
    if ranked_districts is not None:
        table = table[table["district"].isin(ranked_districts)].reset_index(drop=True)
    table["gap_ratio"] = table["demand_share"] / (table["supply_share"] + config.SMOOTHING)
    with np.errstate(divide="ignore"):  # zero demand gives -inf, which ranks lowest
        log_ratio = np.log(table["gap_ratio"])
    table["gap_score"] = _percentile_scores(log_ratio)
    table["saturated"] = table["gap_ratio"] < config.SATURATED_BELOW_RATIO
    return table


def _coverage_row(total, per_10k):
    """Returns (coverage_flag, failed_rule, threshold)."""
    if per_10k >= config.COVERAGE_ADEQUATE and total >= config.MIN_TOTAL_BUSINESSES:
        return "adequate", None, None
    flag = "low" if per_10k >= config.COVERAGE_MIN else "insufficient"
    if per_10k < config.COVERAGE_ADEQUATE:
        return flag, "per_10k", config.COVERAGE_ADEQUATE
    return flag, "total_businesses", config.MIN_TOTAL_BUSINESSES


def coverage_table(district_totals, population):
    merged = district_totals[["district", "total_businesses"]].merge(
        population[["district", "population"]], on="district", how="left"
    )
    merged["population"] = merged["population"].fillna(0).astype(int)
    rows = []
    for row in merged.itertuples(index=False):
        # Multiply first so exact boundaries such as 150 / 300,000 aren't lost to rounding.
        per_10k = row.total_businesses * 10_000 / row.population if row.population > 0 else 0.0
        flag, failed_rule, threshold = _coverage_row(row.total_businesses, per_10k)
        rows.append({
            "district": row.district,
            "total_businesses": row.total_businesses,
            "population": row.population,
            "per_10k": per_10k,
            "coverage_flag": flag,
            "failed_rule": failed_rule,
            "threshold": threshold,
        })
    table = pd.DataFrame(rows)
    # object dtype keeps None as None and whole-number thresholds as ints.
    table["failed_rule"] = pd.Series([r["failed_rule"] for r in rows], dtype=object)
    table["threshold"] = pd.Series([r["threshold"] for r in rows], dtype=object)
    return table
