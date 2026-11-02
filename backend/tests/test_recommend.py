import re

import pytest

from app import config
from app.engine.recommend import recommend
from tests.fixtures import FRESH_SOURCES, TODAY, store


def run(district="Galle", budget=75_000, skills=("sewing",), hours="10-20", data=None, today=TODAY):
    return recommend(data or store(), district, budget, list(skills), hours, today)


def numbers_in(text):
    return set(re.findall(r"\d[\d,]*(?:\.\d+)?", text))


def test_galle_sewing_returns_tailoring_first():
    response = run()
    assert response["status"] == "ok"
    assert response["results"][0]["category_id"] == "tailoring_clothing"
    assert response["profile"] == {"budget_lkr": 75_000, "skills": ["sewing"], "hours": "10-20"}
    assert response["disclaimer"] == config.DISCLAIMER
    assert "osm" in response["freshness"]


def test_results_are_ordered_by_gap_and_capped_at_three():
    response = run(budget=300_000, skills=("sewing", "beauty", "cooking", "retail", "tutoring"), hours="40+")
    ratios = [card["gap_ratio"] for card in response["results"]]
    assert len(ratios) == 3
    assert ratios == sorted(ratios, reverse=True)
    assert response["other_options"] == []
    assert response["message"] is None


def test_other_options_only_hold_skill_excluded_categories():
    response = run()
    result_ids = {card["category_id"] for card in response["results"]}
    other_ids = {option["category_id"] for option in response["other_options"]}
    assert not result_ids & other_ids
    assert other_ids  # grocery fails budget and hours, so it can never be here
    assert "grocery" not in other_ids
    for option in response["other_options"]:
        assert "sewing" not in option["needs_skills"]
        assert option["note"] == "Needs a skill you didn't select"
        assert option["cost_min_lkr"] <= 75_000


def test_other_options_fill_only_the_remaining_places():
    response = run()
    assert len(response["results"]) + len(response["other_options"]) == config.TOP_N_RESULTS


def test_lower_end_budget_flag_reaches_other_options():
    beauty = next(o for o in run()["other_options"] if o["category_id"] == "beauty_salon")
    assert beauty["budget_fit"] == "lower_end"
    assert beauty["budget_fit_label"] == "Lower end fits your budget"


def test_monaragala_refuses_with_adequate_neighbour_suggestions():
    response = run(district="Monaragala")
    assert response["status"] == "insufficient_data"
    assert response["failed_rule"] == "per_10k"
    assert response["min_required"] == config.COVERAGE_ADEQUATE
    assert response["per_10k"] == pytest.approx(1.18)
    assert response["suggestions"] == ["Badulla"]  # Kalutara is a neighbour but only low coverage
    assert "results" not in response
    assert numbers_in(response["reason"]) == {"60", "509,000", "1.2", "5"}


def test_low_coverage_district_also_refuses_with_its_own_reason():
    response = run(district="Kalutara")
    assert response["status"] == "insufficient_data"
    assert response["failed_rule"] == "per_10k"
    assert "still incomplete" in response["reason"]
    assert "still incomplete" not in run(district="Monaragala")["reason"]


def test_stale_prices_in_sources_never_warn_even_if_the_table_looks_fresh():
    sources = {**FRESH_SOURCES, "prices": {"last_date": "2026-10-01"}}
    response = run(skills=("sewing", "cooking"), data=store(sources))
    cards = {card["category_id"]: card for card in response["results"]}
    assert response["freshness"]["prices"]["stale"] is True
    assert cards["bakery_sweets"]["cost_pressure"]["warning"] is False
    assert cards["bakery_sweets"]["cost_pressure"]["stale"] is True
    assert cards["bakery_sweets"]["cost_pressure"]["message"] is None
    assert cards["bakery_sweets"]["confidence"] == "low"
    # No price inputs, so stale prices change nothing on this card.
    assert cards["tailoring_clothing"]["cost_pressure"]["stale"] is False
    assert cards["tailoring_clothing"]["confidence"] == "medium"


def test_unknown_district_raises():
    with pytest.raises(ValueError, match="Unknown district"):
        run(district="Atlantis")


def test_zero_matches_gives_helpful_empty_state():
    # Tutoring is the only category this budget reaches, and it needs a skill the user lacks.
    response = run(budget=25_000, skills=("retail",), hours="10-20")
    assert response["status"] == "ok"
    assert response["results"] == []
    assert response["confidence"] is None
    assert [o["category_id"] for o in response["other_options"]] == ["tutoring"]
    assert "need a skill" in response["message"]


def test_nothing_at_all_suggests_changing_answers():
    data = store()
    data.startup_costs = data.startup_costs.assign(cost_min_lkr=100_000)
    response = run(budget=25_000, data=data)
    assert response["results"] == [] and response["other_options"] == []
    assert "adding skills" in response["message"]


def test_explanation_numbers_all_come_from_the_card():
    response = run(budget=300_000, skills=("sewing", "beauty", "cooking", "retail", "tutoring"), hours="40+")
    for card in response["results"]:
        allowed = {
            str(round(card["supply_share"] * 100)),
            str(round(card["demand_share"] * 100)),
            "5",  # the fixture has 5 categories
        }
        assert numbers_in(card["why"]) <= allowed


def test_cost_pressure_appears_only_on_categories_with_rising_inputs():
    response = run(skills=("sewing", "cooking"))
    cards = {card["category_id"]: card for card in response["results"]}
    assert cards["bakery_sweets"]["cost_pressure"]["warning"] is True
    assert cards["bakery_sweets"]["cost_pressure"]["message"].startswith("Input prices have risen about 15%")
    assert cards["tailoring_clothing"]["cost_pressure"]["warning"] is False
    assert cards["tailoring_clothing"]["cost_pressure"]["message"] is None


def test_page_confidence_is_lowest_card():
    response = run(skills=("sewing", "tutoring"), hours="10-20")
    labels = {card["category_id"]: card["confidence"] for card in response["results"]}
    assert labels["tailoring_clothing"] == "medium"
    assert labels["tutoring"] == "low"
    assert response["confidence"] == "low"


def test_too_stale_refuses_every_district():
    old = {**FRESH_SOURCES, "osm": {"snapshot_date": "2026-08-01"}, "prices": {"last_date": "2026-08-01"}}
    response = run(data=store(old))
    assert response["status"] == "insufficient_data"
    assert response["failed_rule"] == "stale_data"
    assert response["min_required"] is None
    assert response["suggestions"] == []
