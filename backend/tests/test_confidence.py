from datetime import date

from app.engine.confidence import card_confidence, data_too_stale, page_confidence, source_freshness

TODAY = date(2026, 11, 2)


def freshness(osm="2026-10-30", prices="2026-11-01", survey_year=2023):
    return source_freshness(
        {
            "osm": {"snapshot_date": osm},
            "hies": {"survey_year": survey_year},
            "prices": {"last_date": prices},
            "population": {"year": 2024},
        },
        TODAY,
    )


def test_stale_boundary_is_after_14_days():
    assert freshness(osm="2026-10-19")["osm"]["stale"] is False  # exactly 14 days old
    assert freshness(osm="2026-10-18")["osm"]["stale"] is True


def test_missing_date_is_stale():
    assert freshness(prices=None)["prices"] == {"date": None, "age_days": None, "stale": True}


def test_freshness_reports_years_and_placeholder():
    result = freshness(survey_year=2019)
    assert result["hies"]["year"] == 2019
    assert result["population"]["year"] == 2024
    assert result["placeholder"] is False


def test_high_when_everything_is_current():
    assert card_confidence(freshness(), True, "normal") == "high"


def test_old_hies_caps_at_medium():
    assert card_confidence(freshness(survey_year=2019), True, "normal") == "medium"


def test_hies_exactly_five_years_old_is_not_capped():
    assert card_confidence(freshness(survey_year=2021), True, "normal") == "high"


def test_stale_osm_lowers_every_card():
    stale = freshness(osm="2026-10-01")
    assert card_confidence(stale, False, "normal") == "medium"
    assert card_confidence(stale, True, "normal") == "medium"


def test_stale_prices_lower_only_cards_with_price_inputs():
    stale = freshness(prices="2026-10-01")
    assert card_confidence(stale, True, "normal") == "medium"
    assert card_confidence(stale, False, "normal") == "high"


def test_floor_is_low():
    stale = freshness(osm="2026-10-01", prices="2026-10-01", survey_year=2019)
    assert card_confidence(stale, True, "normal") == "low"


def test_low_supply_visibility_caps_at_low():
    assert card_confidence(freshness(), False, "low") == "low"


def test_page_confidence_is_lowest_card():
    assert page_confidence(["high", "low", "medium"]) == "low"
    assert page_confidence([{"confidence": "high"}, {"confidence": "medium"}]) == "medium"
    assert page_confidence([]) is None


def test_refuse_only_when_both_stale_and_osm_past_60_days():
    assert data_too_stale(freshness(osm="2026-09-03", prices="2026-10-01")) is False  # exactly 60 days
    assert data_too_stale(freshness(osm="2026-09-02", prices="2026-10-01")) is True
    assert data_too_stale(freshness(osm="2026-09-02")) is False  # prices are current
