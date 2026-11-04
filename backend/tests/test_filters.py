import pandas as pd

from app.engine.filters import apply_user_filters, skill_excluded_rows
from tests.fixtures import categories, costs

ALL_SKILLS = ["sewing", "beauty", "cooking", "retail", "tutoring"]


def gap_rows():
    ratios = {"tailoring_clothing": 1.8, "beauty_salon": 1.2, "bakery_sweets": 1.1, "grocery": 1.0, "tutoring": 0.5}
    return pd.DataFrame({"category_id": list(ratios), "gap_ratio": list(ratios.values())})


def ids(rows):
    return rows["category_id"].tolist()


def filtered(budget=300_000, skills=ALL_SKILLS, hours="40+"):
    return apply_user_filters(gap_rows(), categories(), costs(), budget, skills, hours)


def test_everything_passes_and_is_sorted_by_gap():
    assert ids(filtered()) == ["tailoring_clothing", "beauty_salon", "bakery_sweets", "grocery", "tutoring"]


def test_budget_drops_when_minimum_cost_is_above_budget():
    assert "grocery" not in ids(filtered(budget=149_999))
    assert "grocery" in ids(filtered(budget=150_000))


def test_budget_fit_flags_lower_end():
    fit = filtered(budget=70_000).set_index("category_id")["budget_fit"]
    assert fit["tailoring_clothing"] == "fits"  # max equals budget
    assert fit["beauty_salon"] == "lower_end"  # 60,000 fits but 120,000 doesn't
    assert fit["bakery_sweets"] == "fits"


def test_skills_filter():
    assert ids(filtered(skills=["sewing"])) == ["tailoring_clothing"]
    assert ids(filtered(skills=[])) == []


def test_any_one_skill_is_enough():
    rows = gap_rows().head(1)
    multi = categories().assign(skills="sewing|retail")
    kept = apply_user_filters(rows, multi, costs(), 300_000, ["retail"], "40+")
    assert ids(kept) == ["tailoring_clothing"]


def test_hours_filter_uses_bucket_order():
    assert ids(filtered(hours="under10")) == ["tutoring"]
    assert "tailoring_clothing" in ids(filtered(hours="10-20"))
    assert "grocery" not in ids(filtered(hours="20-40"))
    assert "grocery" in ids(filtered(hours="40+"))


def test_skill_excluded_rows_fail_only_the_skills_filter():
    rows = skill_excluded_rows(gap_rows(), categories(), costs(), 75_000, ["sewing"], "10-20")
    # grocery fails budget and hours, so it's out. tailoring passes skills, so it's out.
    assert ids(rows) == ["beauty_salon", "bakery_sweets", "tutoring"]
    assert rows.loc[0, "needs_skills"] == ["beauty"]
