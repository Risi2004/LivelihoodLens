"""Generate PLACEHOLDER versions of every file in data/processed/.

All figures here are made up so the API and UI can be built before the real
pipeline runs. Every file is marked as placeholder. Never present them as findings.

Run from backend/:  python -m pipeline.make_placeholder_data
Re-run to refresh dates: OSM and prices go stale after STALE_AFTER_DAYS.
It refuses to overwrite a file that isn't marked as placeholder (real pipeline output).
"""
import json
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app import config

SEED = 42
PLACEHOLDER_COLUMN = "placeholder"
OSM_AGE_DAYS = 3
PRICE_AGE_DAYS = 1
PRICE_HISTORY_DAYS = 120
PRICE_MARKETS = ["Pettah", "Dambulla", "Narahenpita"]
SURVEY_YEAR = 2019
POPULATION_YEAR = 2024

# Share of untyped shops relative to typed businesses, from the proposal's 2,653 / 15,798.
UNTYPED_RATIO = 0.17
PEOPLE_PER_HOUSEHOLD = 3.7
PEOPLE_PER_SURVEY_HOUSEHOLD = 880
MONTHLY_SPEND_PER_HOUSEHOLD_LKR = 35_000
DISTRICT_NOISE = 0.15

# district: (population, businesses per 10k people)
DISTRICT_TARGETS = {
    # adequate (17)
    "Colombo": (2_500_000, 20.0),
    "Gampaha": (2_450_000, 9.0),
    "Kalutara": (1_290_000, 7.0),
    "Kandy": (1_480_000, 9.0),
    "Matale": (540_000, 6.0),
    "Nuwara Eliya": (770_000, 5.5),
    "Galle": (1_130_000, 9.0),
    "Matara": (870_000, 8.0),
    "Hambantota": (680_000, 6.0),
    "Jaffna": (620_000, 7.0),
    "Vavuniya": (185_000, 8.5),
    "Batticaloa": (580_000, 6.0),
    "Ampara": (720_000, 5.5),
    "Trincomalee": (430_000, 6.0),
    "Anuradhapura": (930_000, 6.0),
    "Badulla": (870_000, 5.6),
    "Kegalle": (870_000, 5.5),
    # low (4): Mannar passes the rate but not MIN_TOTAL_BUSINESSES
    "Mannar": (110_000, 6.0),
    "Kilinochchi": (135_000, 4.0),
    "Puttalam": (830_000, 3.8),
    "Polonnaruwa": (440_000, 4.0),
    # insufficient (4)
    "Kurunegala": (1_730_000, 1.0),
    "Monaragala": (509_000, 1.18),
    "Ratnapura": (1_180_000, 1.8),
    "Mullaitivu": (100_000, 2.5),
}

BASE_SUPPLY_MIX = {
    "prepared_food": 22, "bakery_sweets": 7, "grocery": 23, "fruit_veg": 7,
    "fish_meat": 8, "tailoring_clothing": 9, "beauty_salon": 6, "electronics_repair": 6,
    "tutoring": 2, "handicrafts_gifts": 1, "household_hardware": 6, "stationery_books": 3,
}
BASE_DEMAND_MIX = {
    "prepared_food": 14, "bakery_sweets": 7, "grocery": 30, "fruit_veg": 10,
    "fish_meat": 13, "tailoring_clothing": 8, "beauty_salon": 4, "electronics_repair": 3,
    "tutoring": 4, "handicrafts_gifts": 1, "household_hardware": 4, "stationery_books": 2,
}

# Galle is fixed, without noise, so tailoring is its top gap, as in the proposal's example.
GALLE_SUPPLY_MIX = {
    "prepared_food": 24, "bakery_sweets": 6, "grocery": 24, "fruit_veg": 8,
    "fish_meat": 10, "tailoring_clothing": 5, "beauty_salon": 4, "electronics_repair": 6,
    "tutoring": 3, "handicrafts_gifts": 1, "household_hardware": 6, "stationery_books": 3,
}
GALLE_DEMAND_MIX = {
    "prepared_food": 13, "bakery_sweets": 8, "grocery": 27, "fruit_veg": 9,
    "fish_meat": 12, "tailoring_clothing": 11, "beauty_salon": 6, "electronics_repair": 3,
    "tutoring": 3, "handicrafts_gifts": 1, "household_hardware": 5, "stationery_books": 2,
}

BASE_PRICES_LKR = {
    "rice": 230, "coconut": 150, "onion": 320, "dhal": 310, "wheat_flour": 190, "sugar": 260,
    "egg": 40, "carrot": 340, "beans": 420, "tomato": 280, "fish": 1400, "chicken": 1150,
}
# Linear rise over the last 90 days. 0.18 gives about +15% between the two pressure windows.
PRICE_RISE = {"wheat_flour": 0.18, "sugar": 0.18}
DEFAULT_PRICE_RISE = 0.01
PRICE_NOISE = 0.01


def noisy_mix(mix, rng):
    """Vary a mix by district, returning shares that sum to 1."""
    shares = {c: value * rng.lognormal(0, DISTRICT_NOISE) for c, value in mix.items()}
    total = sum(shares.values())
    return {c: value / total for c, value in shares.items()}


def exact_mix(mix):
    total = sum(mix.values())
    return {c: value / total for c, value in mix.items()}


def split_total(total, shares):
    """Split a whole number by shares (largest remainder), so counts sum exactly to total."""
    exact = {c: total * share for c, share in shares.items()}
    counts = {c: int(value) for c, value in exact.items()}
    left_over = total - sum(counts.values())
    by_remainder = sorted(exact, key=lambda c: exact[c] - counts[c], reverse=True)
    for c in by_remainder[:left_over]:
        counts[c] += 1
    return counts


def make_population():
    rows = [
        {"district": d, "population": DISTRICT_TARGETS[d][0], "year": POPULATION_YEAR}
        for d in config.DISTRICTS
    ]
    return pd.DataFrame(rows)


def make_supply(snapshot_date, rng):
    rows = []
    for d in config.DISTRICTS:
        population, per_10k = DISTRICT_TARGETS[d]
        total = round(population * per_10k / 10_000)
        shares = exact_mix(GALLE_SUPPLY_MIX) if d == "Galle" else noisy_mix(BASE_SUPPLY_MIX, rng)
        for c, n in split_total(total, shares).items():
            rows.append({"district": d, "category_id": c, "n_businesses": n, "snapshot_date": snapshot_date})
    return pd.DataFrame(rows)


def make_district_totals(supply, snapshot_date):
    totals = supply.groupby("district", sort=False)["n_businesses"].sum().reset_index(name="total_businesses")
    totals["untyped_excluded"] = (totals["total_businesses"] * UNTYPED_RATIO).round().astype(int)
    totals["snapshot_date"] = snapshot_date
    return totals


def make_demand(rng):
    rows = []
    for d in config.DISTRICTS:
        population = DISTRICT_TARGETS[d][0]
        households = population / PEOPLE_PER_HOUSEHOLD
        total_spend = households * MONTHLY_SPEND_PER_HOUSEHOLD_LKR
        shares = exact_mix(GALLE_DEMAND_MIX) if d == "Galle" else noisy_mix(BASE_DEMAND_MIX, rng)
        spend = {c: round(total_spend * share) for c, share in shares.items()}
        spend_sum = sum(spend.values())
        for c, value in spend.items():
            rows.append({
                "district": d,
                "category_id": c,
                "monthly_spend_lkr": value,
                "demand_share": round(value / spend_sum, 6),
                "n_households": round(population / PEOPLE_PER_SURVEY_HOUSEHOLD),
                "survey_year": SURVEY_YEAR,
            })
    return pd.DataFrame(rows)


def price_items():
    categories = pd.read_csv(config.CATEGORIES_CSV, keep_default_na=False)
    items = set()
    for price_inputs in categories["price_inputs"]:
        items.update(item for item in price_inputs.split("|") if item)
    return sorted(items)


def make_prices(last_date, rng):
    rows = []
    for item in price_items():
        rise = PRICE_RISE.get(item, DEFAULT_PRICE_RISE)
        for market in PRICE_MARKETS:
            market_level = rng.normal(1, 0.02)
            for days_ago in range(PRICE_HISTORY_DAYS - 1, -1, -1):
                progress = max(0, 90 - days_ago) / 90
                noise = rng.normal(1, PRICE_NOISE)
                price = BASE_PRICES_LKR[item] * market_level * (1 + rise * progress) * noise
                rows.append({
                    "date": (last_date - timedelta(days=days_ago)).isoformat(),
                    "item": item,
                    "market": market,
                    "price_lkr": round(price, 2),
                })
    return pd.DataFrame(rows)


def make_sources(osm_date, price_date):
    return {
        "placeholder": True,
        "osm": {"snapshot_date": osm_date},
        "hies": {"survey_year": SURVEY_YEAR},
        "prices": {"last_date": price_date},
        "population": {"year": POPULATION_YEAR},
    }


def holds_real_data(path):
    if not path.exists():
        return False
    if path.suffix == ".json":
        return not json.loads(path.read_text(encoding="utf-8")).get("placeholder")
    header = path.read_text(encoding="utf-8").split("\n", 1)[0]
    return PLACEHOLDER_COLUMN not in header.split(",")


def write_csv(df, path):
    df = df.assign(**{PLACEHOLDER_COLUMN: True})
    df.to_csv(path, index=False, lineterminator="\n", encoding="utf-8")
    print(f"wrote {path.name}: {len(df)} rows (placeholder)")


def main():
    csv_paths = [
        config.SUPPLY_CSV, config.DISTRICT_TOTALS_CSV, config.POPULATION_CSV,
        config.DEMAND_CSV, config.PRICES_CSV,
    ]
    real = [p.name for p in csv_paths + [config.SOURCES_JSON] if holds_real_data(p)]
    if real:
        sys.exit(f"Refusing to overwrite real data: {', '.join(real)}")

    today = date.today()
    osm_date = (today - timedelta(days=OSM_AGE_DAYS)).isoformat()
    price_last = today - timedelta(days=PRICE_AGE_DAYS)
    rng = np.random.default_rng(SEED)

    supply = make_supply(osm_date, rng)
    write_csv(supply, config.SUPPLY_CSV)
    write_csv(make_district_totals(supply, osm_date), config.DISTRICT_TOTALS_CSV)
    write_csv(make_population(), config.POPULATION_CSV)
    write_csv(make_demand(rng), config.DEMAND_CSV)
    write_csv(make_prices(price_last, rng), config.PRICES_CSV)

    sources = make_sources(osm_date, price_last.isoformat())
    config.SOURCES_JSON.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {config.SOURCES_JSON.name} (placeholder)")


if __name__ == "__main__":
    main()
