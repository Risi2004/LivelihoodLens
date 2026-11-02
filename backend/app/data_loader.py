"""Reads the reference and processed tables into one DataStore."""
import json
from dataclasses import dataclass

import pandas as pd

from app import config

REQUIRED_COLUMNS = {
    "categories": ["category_id", "label", "skills", "min_hours", "price_inputs", "supply_visibility"],
    "osm_category_map": ["osm_key", "osm_value", "category_id"],
    "startup_costs": ["category_id", "cost_min_lkr", "cost_max_lkr", "source", "notes"],
    "hies_item_map": ["item_code", "item_description", "module", "category_id", "checked"],
    "district_neighbours": ["district", "neighbour"],
    "supply": ["district", "category_id", "n_businesses", "snapshot_date"],
    "district_totals": ["district", "total_businesses", "untyped_excluded", "snapshot_date"],
    "population": ["district", "population", "year"],
    "demand": ["district", "category_id", "monthly_spend_lkr", "demand_share", "n_households", "survey_year"],
    "prices": ["date", "item", "market", "price_lkr"],
}
REQUIRED_SOURCES = ["osm", "hies", "prices", "population"]
NUMERIC_COLUMNS = {
    "startup_costs": ["cost_min_lkr", "cost_max_lkr"],
    "supply": ["n_businesses"],
    "district_totals": ["total_businesses", "untyped_excluded"],
    "population": ["population", "year"],
    "demand": ["monthly_spend_lkr", "demand_share", "n_households", "survey_year"],
    "prices": ["price_lkr"],
}
# A missing day's price may stay blank. Every other number must be present.
BLANK_ALLOWED = {("prices", "price_lkr")}


@dataclass
class DataStore:
    categories: pd.DataFrame
    osm_category_map: pd.DataFrame
    startup_costs: pd.DataFrame
    hies_item_map: pd.DataFrame | None  # None until the HIES item mapping is written
    district_neighbours: pd.DataFrame
    supply: pd.DataFrame
    district_totals: pd.DataFrame
    population: pd.DataFrame
    demand: pd.DataFrame
    prices: pd.DataFrame
    sources: dict


class DataValidationError(ValueError):
    pass


def validate_columns(df, name, source):
    missing = [c for c in REQUIRED_COLUMNS[name] if c not in df.columns]
    if missing:
        raise DataValidationError(f"{source} is missing column(s): {', '.join(missing)}")


def convert_numeric_columns(df, name, source):
    """Numeric columns become numbers, or a clear error names the file, column and line."""
    for column in NUMERIC_COLUMNS.get(name, []):
        values = pd.to_numeric(df[column], errors="coerce")
        bad = values.isna()
        if (name, column) in BLANK_ALLOWED:
            bad = bad & (df[column].astype(str).str.strip() != "")
        if bad.any():
            line = bad.idxmax() + 2  # header is line 1
            raise DataValidationError(
                f"{source} line {line}: {column} must be a number, not '{df.loc[bad.idxmax(), column]}'"
            )
        df[column] = values
    return df


def read_table(path, name):
    if not path.exists():
        raise DataValidationError(f"Required data file not found: {path}")
    # keep_default_na=False keeps empty price_inputs as "" rather than NaN
    df = pd.read_csv(path, keep_default_na=False)
    validate_columns(df, name, path.name)
    return convert_numeric_columns(df, name, path.name)


def read_sources(path):
    if not path.exists():
        raise DataValidationError(f"Required data file not found: {path}")
    sources = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_SOURCES if key not in sources]
    if missing:
        raise DataValidationError(f"{path.name} is missing field(s): {', '.join(missing)}")
    return sources


def validate_contents(store):
    """Catches values that would silently distort scores, such as a misspelt district."""
    official = set(config.DISTRICTS)
    tables = {
        "supply.csv": store.supply["district"],
        "district_totals.csv": store.district_totals["district"],
        "population.csv": store.population["district"],
        "demand.csv": store.demand["district"],
        "district_neighbours.csv": pd.concat(
            [store.district_neighbours["district"], store.district_neighbours["neighbour"]]
        ),
    }
    for source, districts in tables.items():
        unknown = sorted(set(districts) - official)
        if unknown:
            raise DataValidationError(f"{source} has unknown district(s): {', '.join(unknown)}")
    for source in ["district_totals.csv", "population.csv"]:
        missing = sorted(official - set(tables[source]))
        if missing:
            raise DataValidationError(f"{source} is missing district(s): {', '.join(missing)}")

    known_categories = set(store.categories["category_id"])
    for source, table in [("supply.csv", store.supply), ("demand.csv", store.demand)]:
        unknown = sorted(set(table["category_id"]) - known_categories)
        if unknown:
            raise DataValidationError(f"{source} has unknown category(s): {', '.join(unknown)}")

    supply_sums = store.supply.groupby("district")["n_businesses"].sum()
    for row in store.district_totals.itertuples(index=False):
        if row.total_businesses != supply_sums.get(row.district, 0):
            raise DataValidationError(
                f"district_totals.csv: {row.district} has total_businesses {row.total_businesses}, "
                f"but supply.csv sums to {supply_sums.get(row.district, 0)}"
            )

    # Freshness reads this date and cost pressure reads the table, so they must agree.
    last_date = store.sources["prices"].get("last_date")
    priced = store.prices.dropna(subset=["price_lkr"])
    if last_date and not priced.empty and priced["date"].max() != last_date:
        raise DataValidationError(
            f"sources.json prices.last_date is {last_date}, but prices.csv ends on {priced['date'].max()}"
        )


def load_all(reference_dir=config.REFERENCE_DIR, processed_dir=config.PROCESSED_DIR):
    hies_path = reference_dir / config.HIES_ITEM_MAP_CSV.name
    store = DataStore(
        categories=read_table(reference_dir / config.CATEGORIES_CSV.name, "categories"),
        osm_category_map=read_table(reference_dir / config.OSM_CATEGORY_MAP_CSV.name, "osm_category_map"),
        startup_costs=read_table(reference_dir / config.STARTUP_COSTS_CSV.name, "startup_costs"),
        hies_item_map=read_table(hies_path, "hies_item_map") if hies_path.exists() else None,
        district_neighbours=read_table(reference_dir / config.DISTRICT_NEIGHBOURS_CSV.name, "district_neighbours"),
        supply=read_table(processed_dir / config.SUPPLY_CSV.name, "supply"),
        district_totals=read_table(processed_dir / config.DISTRICT_TOTALS_CSV.name, "district_totals"),
        population=read_table(processed_dir / config.POPULATION_CSV.name, "population"),
        demand=read_table(processed_dir / config.DEMAND_CSV.name, "demand"),
        prices=read_table(processed_dir / config.PRICES_CSV.name, "prices"),
        sources=read_sources(processed_dir / config.SOURCES_JSON.name),
    )
    validate_contents(store)
    return store
