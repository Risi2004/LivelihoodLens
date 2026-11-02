import pandas as pd
from fastapi.testclient import TestClient

from app import config
from app.main import app


def read_reference(path):
    # keep_default_na=False so empty price_inputs stay "" rather than NaN
    return pd.read_csv(path, keep_default_na=False)


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_districts():
    assert len(config.DISTRICTS) == 25
    assert len(set(config.DISTRICTS)) == 25
    assert set(config.PILOT_DISTRICTS) <= set(config.DISTRICTS)


def test_categories_csv():
    categories = read_reference(config.CATEGORIES_CSV)
    assert len(categories) == 12
    assert categories["category_id"].is_unique
    assert categories["min_hours"].isin(config.HOURS_BUCKETS).all()
    assert categories["supply_visibility"].isin(["normal", "low"]).all()
    for skills in categories["skills"]:
        assert set(skills.split("|")) <= set(config.SKILLS)
    # The comma in this label must survive CSV quoting.
    label = categories.set_index("category_id").loc["stationery_books", "label"]
    assert label == "Stationery, books & printing"


def test_osm_category_map_csv():
    categories = read_reference(config.CATEGORIES_CSV)
    osm_map = read_reference(config.OSM_CATEGORY_MAP_CSV)
    assert not osm_map.duplicated(["osm_key", "osm_value"]).any()
    assert osm_map["osm_key"].isin(["shop", "amenity", "craft"]).all()
    assert set(osm_map["category_id"]) == set(categories["category_id"])


def test_startup_costs_csv():
    categories = read_reference(config.CATEGORIES_CSV)
    costs = read_reference(config.STARTUP_COSTS_CSV)
    assert sorted(costs["category_id"]) == sorted(categories["category_id"])
    assert (costs["cost_min_lkr"] < costs["cost_max_lkr"]).all()
    assert (costs["cost_min_lkr"] >= config.BUDGET_MIN_LKR).all()
    assert (costs["cost_min_lkr"] <= config.BUDGET_MAX_LKR).all()
    assert (costs["source"] != "").all()

    ranges = costs.set_index("category_id")
    assert tuple(ranges.loc["tailoring_clothing", ["cost_min_lkr", "cost_max_lkr"]]) == (40000, 70000)
    assert tuple(ranges.loc["beauty_salon", ["cost_min_lkr", "cost_max_lkr"]]) == (60000, 120000)
    assert tuple(ranges.loc["bakery_sweets", ["cost_min_lkr", "cost_max_lkr"]]) == (30000, 60000)


def test_district_neighbours_csv():
    neighbours = read_reference(config.DISTRICT_NEIGHBOURS_CSV)
    assert set(neighbours["district"]) == set(config.DISTRICTS)
    assert set(neighbours["neighbour"]) == set(config.DISTRICTS)
    assert not neighbours.duplicated().any()
    assert (neighbours["district"] != neighbours["neighbour"]).all()
    pairs = set(zip(neighbours["district"], neighbours["neighbour"]))
    assert all((b, a) in pairs for a, b in pairs)
