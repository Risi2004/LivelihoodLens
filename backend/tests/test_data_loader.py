import json

import pandas as pd
import pytest

from app import config
from app.data_loader import REQUIRED_COLUMNS, DataValidationError, load_all

FILES = {
    "categories": config.CATEGORIES_CSV,
    "osm_category_map": config.OSM_CATEGORY_MAP_CSV,
    "startup_costs": config.STARTUP_COSTS_CSV,
    "district_neighbours": config.DISTRICT_NEIGHBOURS_CSV,
    "supply": config.SUPPLY_CSV,
    "district_totals": config.DISTRICT_TOTALS_CSV,
    "population": config.POPULATION_CSV,
    "demand": config.DEMAND_CSV,
    "prices": config.PRICES_CSV,
}


@pytest.fixture
def data_dir(tmp_path):
    """The smallest valid data set: one category, one business in each official district."""
    for name, path in FILES.items():
        pd.DataFrame(columns=REQUIRED_COLUMNS[name]).to_csv(tmp_path / path.name, index=False)
    (tmp_path / config.CATEGORIES_CSV.name).write_text(
        "category_id,label,skills,min_hours,price_inputs,supply_visibility\n"
        "tutoring,Tutoring,tutoring,under10,,low\n"
    )
    districts = config.DISTRICTS
    pd.DataFrame(
        [(d, "tutoring", 1, "2026-10-30") for d in districts],
        columns=REQUIRED_COLUMNS["supply"],
    ).to_csv(tmp_path / config.SUPPLY_CSV.name, index=False)
    pd.DataFrame(
        [(d, 1, 0, "2026-10-30") for d in districts],
        columns=REQUIRED_COLUMNS["district_totals"],
    ).to_csv(tmp_path / config.DISTRICT_TOTALS_CSV.name, index=False)
    pd.DataFrame(
        [(d, 1000, 2024) for d in districts],
        columns=REQUIRED_COLUMNS["population"],
    ).to_csv(tmp_path / config.POPULATION_CSV.name, index=False)
    (tmp_path / config.PRICES_CSV.name).write_text(
        "date,item,market,price_lkr\n2026-10-31,rice,Pettah,100\n2026-11-01,rice,Pettah,\n"
    )
    sources = {
        "placeholder": True,
        "osm": {},
        "hies": {},
        "prices": {"last_date": "2026-10-31"},
        "population": {},
    }
    (tmp_path / config.SOURCES_JSON.name).write_text(json.dumps(sources))
    return tmp_path


def replace_in_file(path, old, new):
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_load_all_builds_store(data_dir):
    store = load_all(data_dir, data_dir)
    assert store.sources["placeholder"] is True
    assert store.hies_item_map is None
    assert store.categories.loc[0, "price_inputs"] == ""


def test_real_reference_and_placeholder_files_load():
    store = load_all()
    assert len(store.categories) == 12
    assert store.prices["price_lkr"].dtype == float


def test_missing_column_names_file_and_column(data_dir):
    path = data_dir / config.SUPPLY_CSV.name
    path.write_text("district,category_id,snapshot_date\n")
    with pytest.raises(DataValidationError, match=r"supply\.csv is missing column\(s\): n_businesses"):
        load_all(data_dir, data_dir)


def test_extra_placeholder_column_is_allowed(data_dir):
    path = data_dir / config.POPULATION_CSV.name
    pd.read_csv(path).assign(placeholder=True).to_csv(path, index=False)
    assert list(load_all(data_dir, data_dir).population.columns)[-1] == "placeholder"


def test_missing_file_is_a_clear_error(data_dir):
    (data_dir / config.DEMAND_CSV.name).unlink()
    with pytest.raises(DataValidationError, match="demand.csv"):
        load_all(data_dir, data_dir)


def test_missing_sources_field(data_dir):
    (data_dir / config.SOURCES_JSON.name).write_text(json.dumps({"osm": {}}))
    with pytest.raises(DataValidationError, match="hies"):
        load_all(data_dir, data_dir)


def test_blank_price_loads_as_a_missing_number(data_dir):
    prices = load_all(data_dir, data_dir).prices
    assert prices["price_lkr"].dtype == float
    assert prices["price_lkr"].isna().sum() == 1


def test_text_in_a_price_names_file_and_line(data_dir):
    replace_in_file(data_dir / config.PRICES_CSV.name, "Pettah,100", "Pettah,n/a")
    with pytest.raises(DataValidationError, match=r"prices\.csv line 2: price_lkr must be a number, not 'n/a'"):
        load_all(data_dir, data_dir)


def test_blank_outside_prices_is_an_error(data_dir):
    replace_in_file(data_dir / config.POPULATION_CSV.name, "Galle,1000,", "Galle,,")
    with pytest.raises(DataValidationError, match=r"population\.csv line \d+: population must be a number"):
        load_all(data_dir, data_dir)


def test_misspelt_district_is_rejected(data_dir):
    replace_in_file(data_dir / config.SUPPLY_CSV.name, "Galle,", "Gaalle,")
    with pytest.raises(DataValidationError, match=r"supply\.csv has unknown district\(s\): Gaalle"):
        load_all(data_dir, data_dir)


def test_misspelt_neighbour_is_rejected(data_dir):
    (data_dir / config.DISTRICT_NEIGHBOURS_CSV.name).write_text("district,neighbour\nGalle,Matarra\n")
    with pytest.raises(DataValidationError, match="Matarra"):
        load_all(data_dir, data_dir)


def test_missing_district_is_rejected(data_dir):
    path = data_dir / config.POPULATION_CSV.name
    frame = pd.read_csv(path)
    frame[frame["district"] != "Galle"].to_csv(path, index=False)
    with pytest.raises(DataValidationError, match=r"population\.csv is missing district\(s\): Galle"):
        load_all(data_dir, data_dir)


def test_unknown_category_is_rejected(data_dir):
    replace_in_file(data_dir / config.SUPPLY_CSV.name, "Galle,tutoring", "Galle,tutorin")
    with pytest.raises(DataValidationError, match="tutorin"):
        load_all(data_dir, data_dir)


def test_total_must_equal_supply_sum(data_dir):
    replace_in_file(data_dir / config.DISTRICT_TOTALS_CSV.name, "Galle,1,", "Galle,5,")
    with pytest.raises(DataValidationError, match="Galle has total_businesses 5, but supply.csv sums to 1"):
        load_all(data_dir, data_dir)


def test_price_date_must_match_sources(data_dir):
    sources = json.loads((data_dir / config.SOURCES_JSON.name).read_text())
    sources["prices"]["last_date"] = "2026-11-01"  # that day's price is blank
    (data_dir / config.SOURCES_JSON.name).write_text(json.dumps(sources))
    with pytest.raises(DataValidationError, match="prices.csv ends on 2026-10-31"):
        load_all(data_dir, data_dir)
