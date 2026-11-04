"""Small hand-made tables for engine tests. Independent of the placeholder files."""
from datetime import date, timedelta

import pandas as pd

from app.data_loader import DataStore

TODAY = date(2026, 11, 2)
FRESH_SOURCES = {
    "osm": {"snapshot_date": "2026-10-30"},
    "hies": {"survey_year": 2019},
    "prices": {"last_date": "2026-11-01"},
    "population": {"year": 2024},
}


def categories():
    return pd.DataFrame(
        [
            ("tailoring_clothing", "Tailoring & clothing", "sewing", "10-20", "", "normal"),
            ("beauty_salon", "Beauty & salon", "beauty", "10-20", "", "normal"),
            ("bakery_sweets", "Bakery & sweets", "cooking", "10-20", "wheat_flour|sugar", "normal"),
            ("grocery", "Grocery & convenience", "retail", "40+", "rice", "normal"),
            ("tutoring", "Tutoring & classes", "tutoring", "under10", "", "low"),
        ],
        columns=["category_id", "label", "skills", "min_hours", "price_inputs", "supply_visibility"],
    )


def costs():
    return pd.DataFrame(
        [
            ("tailoring_clothing", 40_000, 70_000, "test", ""),
            ("beauty_salon", 60_000, 120_000, "test", ""),
            ("bakery_sweets", 30_000, 60_000, "test", ""),
            ("grocery", 150_000, 300_000, "test", ""),
            ("tutoring", 25_000, 40_000, "test", ""),
        ],
        columns=["category_id", "cost_min_lkr", "cost_max_lkr", "source", "notes"],
    )


def _district_rows(district, supply_counts, spend):
    ids = categories()["category_id"].tolist()
    return (
        [(district, c, n, "2026-10-30") for c, n in zip(ids, supply_counts)],
        [(district, c, s, s / sum(spend), 100, 2019) for c, s in zip(ids, spend)],
    )


def price_rows(item, recent, baseline, today=TODAY):
    rows = []
    for days_ago in range(1, 15):
        rows.append(((today - timedelta(days=days_ago)).isoformat(), item, "Pettah", recent))
    for days_ago in range(76, 91):
        rows.append(((today - timedelta(days=days_ago)).isoformat(), item, "Pettah", baseline))
    return rows


def prices_frame(rows):
    return pd.DataFrame(rows, columns=["date", "item", "market", "price_lkr"])


def store(sources=None):
    """Galle and Badulla rank, Monaragala is insufficient, Kalutara is low."""
    #                                 tailor beauty bakery grocery tutor
    galle = _district_rows("Galle", [5, 5, 10, 70, 10], [11, 6, 8, 70, 5])
    badulla = _district_rows("Badulla", [20, 10, 10, 50, 10], [10, 5, 10, 70, 5])
    monaragala = _district_rows("Monaragala", [5, 5, 10, 35, 5], [10, 5, 10, 70, 5])
    kalutara = _district_rows("Kalutara", [20, 10, 20, 40, 10], [10, 5, 10, 70, 5])
    all_rows = [galle, badulla, monaragala, kalutara]
    return DataStore(
        categories=categories(),
        osm_category_map=pd.DataFrame(columns=["osm_key", "osm_value", "category_id"]),
        startup_costs=costs(),
        hies_item_map=None,
        district_neighbours=pd.DataFrame(
            [("Monaragala", "Badulla"), ("Monaragala", "Kalutara"), ("Badulla", "Monaragala"), ("Kalutara", "Monaragala")],
            columns=["district", "neighbour"],
        ),
        supply=pd.DataFrame(
            [r for d in all_rows for r in d[0]],
            columns=["district", "category_id", "n_businesses", "snapshot_date"],
        ),
        district_totals=pd.DataFrame(
            [
                ("Galle", 1000, 170, "2026-10-30"),
                ("Badulla", 500, 85, "2026-10-30"),
                ("Monaragala", 60, 10, "2026-10-30"),
                ("Kalutara", 400, 68, "2026-10-30"),
            ],
            columns=["district", "total_businesses", "untyped_excluded", "snapshot_date"],
        ),
        population=pd.DataFrame(
            [("Galle", 1_130_000, 2024), ("Badulla", 870_000, 2024), ("Monaragala", 509_000, 2024), ("Kalutara", 1_000_000, 2024)],
            columns=["district", "population", "year"],
        ),
        demand=pd.DataFrame(
            [r for d in all_rows for r in d[1]],
            columns=["district", "category_id", "monthly_spend_lkr", "demand_share", "n_households", "survey_year"],
        ),
        prices=prices_frame(price_rows("rice", 100, 100) + price_rows("wheat_flour", 115, 100) + price_rows("sugar", 115, 100)),
        sources=sources or FRESH_SOURCES,
    )
