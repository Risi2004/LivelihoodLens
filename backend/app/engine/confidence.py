"""Freshness of each source and confidence labels."""
from datetime import date

from app import config

LEVELS = ["low", "medium", "high"]


def _dated_source(date_text, today):
    if not date_text:
        return {"date": None, "age_days": None, "stale": True}
    age_days = (today - date.fromisoformat(date_text)).days
    return {"date": date_text, "age_days": age_days, "stale": age_days > config.STALE_AFTER_DAYS}


def source_freshness(sources, today):
    survey_year = sources["hies"]["survey_year"]
    return {
        "placeholder": bool(sources.get("placeholder", False)),
        "osm": _dated_source(sources["osm"].get("snapshot_date"), today),
        "prices": _dated_source(sources["prices"].get("last_date"), today),
        "hies": {
            "year": survey_year,
            "stale": False,
            "over_age_limit": today.year - survey_year > config.HIES_MAX_AGE_YEARS,
        },
        "population": {"year": sources["population"]["year"], "stale": False},
    }


def data_too_stale(freshness):
    """True when both refreshing sources are stale and OSM is past its refusal age."""
    osm, prices = freshness["osm"], freshness["prices"]
    osm_too_old = osm["age_days"] is None or osm["age_days"] > config.OSM_REFUSE_AFTER_DAYS
    return osm["stale"] and prices["stale"] and osm_too_old


def card_confidence(freshness, has_price_inputs, supply_visibility):
    level = LEVELS.index("high")
    if freshness["hies"]["over_age_limit"]:
        level = min(level, LEVELS.index("medium"))
    if freshness["osm"]["stale"]:
        level -= 1
    if freshness["prices"]["stale"] and has_price_inputs:
        level -= 1
    if supply_visibility == "low":
        level = LEVELS.index("low")
    return LEVELS[max(level, 0)]


def page_confidence(cards):
    """Lowest label among the cards (each a label or a dict with "confidence"). None if no cards."""
    labels = [card["confidence"] if isinstance(card, dict) else card for card in cards]
    if not labels:
        return None
    return min(labels, key=LEVELS.index)
