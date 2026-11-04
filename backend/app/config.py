"""All thresholds and paths. Single source of truth (see CLAUDE.md)."""
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
REFERENCE_DIR = DATA_DIR / "reference"
PROCESSED_DIR = DATA_DIR / "processed"

CATEGORIES_CSV = REFERENCE_DIR / "categories.csv"
OSM_CATEGORY_MAP_CSV = REFERENCE_DIR / "osm_category_map.csv"
STARTUP_COSTS_CSV = REFERENCE_DIR / "startup_costs.csv"
HIES_ITEM_MAP_CSV = REFERENCE_DIR / "hies_item_map.csv"
DISTRICT_NEIGHBOURS_CSV = REFERENCE_DIR / "district_neighbours.csv"

SUPPLY_CSV = PROCESSED_DIR / "supply.csv"
DISTRICT_TOTALS_CSV = PROCESSED_DIR / "district_totals.csv"
POPULATION_CSV = PROCESSED_DIR / "population.csv"
DEMAND_CSV = PROCESSED_DIR / "demand.csv"
PRICES_CSV = PROCESSED_DIR / "prices.csv"
BACKTEST_RESULTS_CSV = PROCESSED_DIR / "backtest_results.csv"
SOURCES_JSON = PROCESSED_DIR / "sources.json"

# API
DEV_FRONTEND_ORIGIN = "http://localhost:5173"

# Scoring
SMOOTHING = 0.01
SATURATED_BELOW_RATIO = 1.0
TOP_N_RESULTS = 3
STRONG_GAP_SCORE = 75  # explanation wording only, never affects ranking

# Coverage gate (placeholders: tune once real numbers are in, never silently)
COVERAGE_ADEQUATE = 5
COVERAGE_MIN = 3
MIN_TOTAL_BUSINESSES = 150

# Cost pressure
PRESSURE_THRESHOLD = 0.10
PRESSURE_RECENT_DAYS = 14
PRESSURE_BASELINE_START_DAYS = 76
PRESSURE_BASELINE_END_DAYS = 90

# Confidence and freshness
STALE_AFTER_DAYS = 14
OSM_REFUSE_AFTER_DAYS = 60
HIES_MAX_AGE_YEARS = 5

# User input limits
BUDGET_MIN_LKR = 25_000
BUDGET_MAX_LKR = 300_000

SKILLS = {
    "cooking": "Cooking & baking",
    "sewing": "Sewing",
    "beauty": "Beauty & hair",
    "electronics_repair": "Phone & electronics repair",
    "tutoring": "Tutoring",
    "handicrafts": "Handicrafts",
    "retail": "Retail",
}

# Ordered smallest to largest, so list position can be compared.
HOURS_BUCKETS = ["under10", "10-20", "20-40", "40+"]

PILOT_DISTRICTS = ["Colombo", "Gampaha", "Galle", "Matara", "Kandy"]

DISTRICTS = [
    "Ampara",
    "Anuradhapura",
    "Badulla",
    "Batticaloa",
    "Colombo",
    "Galle",
    "Gampaha",
    "Hambantota",
    "Jaffna",
    "Kalutara",
    "Kandy",
    "Kegalle",
    "Kilinochchi",
    "Kurunegala",
    "Mannar",
    "Matale",
    "Matara",
    "Monaragala",
    "Mullaitivu",
    "Nuwara Eliya",
    "Polonnaruwa",
    "Puttalam",
    "Ratnapura",
    "Trincomalee",
    "Vavuniya",
]

DISCLAIMER = (
    "Demand indicator only. A gap can also exist for reasons the data cannot see, "
    "such as high rent or a business that closed there before."
)
