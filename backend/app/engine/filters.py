"""Budget, skills and hours filters."""
import numpy as np

from app import config


def _hours_rank(bucket):
    return config.HOURS_BUCKETS.index(bucket)


def _has_skill(category_skills, user_skills):
    return bool(set(category_skills.split("|")) & set(user_skills))


def _passing_budget_and_hours(gap_rows, categories, costs, budget, hours):
    rows = gap_rows.merge(categories, on="category_id").merge(
        costs[["category_id", "cost_min_lkr", "cost_max_lkr"]], on="category_id"
    )
    user_hours = _hours_rank(hours)
    fits_hours = rows["min_hours"].map(_hours_rank) <= user_hours
    rows = rows[(rows["cost_min_lkr"] <= budget) & fits_hours].copy()
    rows["budget_fit"] = np.where(rows["cost_max_lkr"] > budget, "lower_end", "fits")
    return rows


def _sorted_by_gap(rows):
    return rows.sort_values("gap_ratio", ascending=False, kind="stable").reset_index(drop=True)


def apply_user_filters(gap_rows, categories, costs, budget, skills, hours):
    """Rows the user can afford, has a skill for and has the hours for, highest gap first."""
    rows = _passing_budget_and_hours(gap_rows, categories, costs, budget, hours)
    keep = np.array([_has_skill(s, skills) for s in rows["skills"]], dtype=bool)
    return _sorted_by_gap(rows[keep])


def skill_excluded_rows(gap_rows, categories, costs, budget, skills, hours):
    """Rows that pass budget and hours and fail only the skills filter, highest gap first."""
    rows = _passing_budget_and_hours(gap_rows, categories, costs, budget, hours)
    keep = np.array([not _has_skill(s, skills) for s in rows["skills"]], dtype=bool)
    rows = rows[keep].copy()
    rows["needs_skills"] = [s.split("|") for s in rows["skills"]]
    return _sorted_by_gap(rows)
