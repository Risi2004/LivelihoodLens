# Livelihood Lens — project context for Claude Code

ModelX 2.0 (IEEE CIS Student Chapter, IIT) entry by team HyperNova. Domain: cost of living and everyday economics.
Built solo by the project lead in ~2 days, so keep everything simple, readable and tested. Prefer plain functions over abstractions.

## What the product does
A first-time micro-entrepreneur in Sri Lanka enters **district, budget (LKR 25,000–300,000), skills, hours per week**.
The system returns the **top 3 business types that the district is missing**, filtered to what the user can afford and has the skills for.
Each result shows: gap score (0–100), start-up cost range, a plain-language "why this ranks here", any cost-pressure warning, and a confidence + freshness label.
If the district's data is too thin, it **refuses to rank** and explains why ("We can't rank Monaragala yet").
Secondary user: microfinance / livelihood loan officer who prints or saves the result.

It is a **demand indicator, not financial advice**. Never promise profit or success in any text, UI or API message.

## Stack
- `backend/` — Python 3.11+, FastAPI, pandas, pydantic. Data tables are CSV files in `backend/data/processed/` (loaded once at startup). No database needed.
- `backend/pipeline/` — offline data scripts: pyrosm + geopandas (OpenStreetMap), pandas / pyreadstat (HIES), pdfplumber (population PDF).
- `backend/tests/` — pytest.
- `frontend/` — React + Vite (JavaScript), Tailwind CSS v4 (`@tailwindcss/vite`), react-router-dom. API base URL from `VITE_API_URL`.
- Hosting: Render (API), Vercel (frontend).

## Folder layout (target)
```
backend/
  app/
    main.py            FastAPI app, CORS, routers, loads data at startup
    config.py          all thresholds and paths (single source of truth)
    schemas.py         pydantic request/response models
    data_loader.py     reads processed CSVs + sources.json into one DataStore object
    routers/           districts.py, recommend.py, freshness.py, categories.py
    engine/
      scoring.py       shares, gap ratio, gap score, coverage gate
      filters.py       budget / skills / hours filters
      pressure.py      cost-pressure signal from prices.csv
      confidence.py    freshness + confidence labels
      explain.py       template-based plain-language reasons
      recommend.py     orchestrates the above into the final response
  pipeline/
    osm_supply.py, population.py, hies_inspect.py, hies_demand.py, backtest.py, hand_check.py
  data/
    raw/               .pbf, geojson, HIES files, PDFs  (gitignored — NEVER commit HIES)
    reference/         hand-maintained CSVs (categories, osm map, start-up costs, hies item map)
    processed/         pipeline outputs consumed by the API
  tests/
frontend/src/
  api.js, App.jsx, main.jsx, index.css
  pages/ Profile.jsx, Results.jsx, NoData.jsx, AboutData.jsx
  components/ Navbar.jsx, ResultCard.jsx, FreshnessPanel.jsx, ConfidenceBadge.jsx, Disclaimer.jsx
```

## Pilot scope
Pilot districts (must work end-to-end): **Colombo, Gampaha, Galle, Matara, Kandy**.
All 25 districts still get a coverage flag, so non-pilot or poorly-mapped districts show the refusal screen instead of an error.
District names must match the official 25-district list (e.g. "Nuwara Eliya", "Monaragala", "Mullaitivu").

## The 12 business categories (reference/categories.csv)
| category_id | label | skills (any of) | min_hours | price_inputs | supply_visibility |
|---|---|---|---|---|---|
| prepared_food | Prepared food & takeaway | cooking | 20-40 | rice, coconut, onion, dhal | normal |
| bakery_sweets | Bakery & sweets | cooking | 10-20 | wheat_flour, sugar, egg | normal |
| grocery | Grocery & convenience | retail | 40+ | rice, sugar, dhal | normal |
| fruit_veg | Fruit & vegetables | retail | 20-40 | carrot, beans, tomato | normal |
| fish_meat | Fish & meat | retail | 20-40 | fish, chicken | normal |
| tailoring_clothing | Tailoring & clothing | sewing | 10-20 | | normal |
| beauty_salon | Beauty & salon | beauty | 10-20 | | normal |
| electronics_repair | Phone & electronics repair | electronics_repair | 10-20 | | normal |
| tutoring | Tutoring & classes | tutoring | under10 | | low |
| handicrafts_gifts | Handicrafts & gifts | handicrafts | under10 | | normal |
| household_hardware | Hardware & household goods | retail | 40+ | | normal |
| stationery_books | Stationery, books & printing | retail | 20-40 | | normal |

Skills ids (UI chips): cooking, sewing, beauty, electronics_repair, tutoring, handicrafts, retail.
Hours buckets: `under10` < `10-20` < `20-40` < `40+`. A category is kept if the user's bucket ≥ its min_hours.
`supply_visibility = low` means OSM rarely maps this kind of business (home tuition), so its confidence is always capped at **low** and the reason text says so.

## Data contracts (backend/data)
reference/ (hand-maintained, committed):
- `categories.csv` — category_id,label,skills,min_hours,price_inputs,supply_visibility  (skills and price_inputs are `|`-separated)
- `osm_category_map.csv` — osm_key,osm_value,category_id   (e.g. shop,bakery,bakery_sweets ; amenity,fast_food,prepared_food ; craft,tailor,tailoring_clothing)
- `startup_costs.csv` — category_id,cost_min_lkr,cost_max_lkr,source,notes
- `hies_item_map.csv` — item_code,item_description,module(food|nonfood),category_id,checked(y/n)

processed/ (generated by pipeline, committed — aggregates only):
- `supply.csv` — district,category_id,n_businesses,snapshot_date
- `district_totals.csv` — district,total_businesses,untyped_excluded,snapshot_date
- `population.csv` — district,population,year
- `demand.csv` — district,category_id,monthly_spend_lkr,demand_share,n_households,survey_year
- `prices.csv` — date,item,market,price_lkr
- `sources.json` — {"osm":{"snapshot_date":"YYYY-MM-DD"},"hies":{"survey_year":2019},"prices":{"last_date":"YYYY-MM-DD"},"population":{"year":2024}}

## Scoring rules (engine) — implement exactly, all constants in config.py
For each district d and category c:
1. `demand_share[d,c]` = weighted monthly spending on c ÷ weighted spending on all 12 categories (HIES).
2. `supply_share[d,c]` = n_businesses[d,c] ÷ Σ_c n_businesses[d,c]  (only the 12 categories, untyped excluded).
3. `gap_ratio = demand_share / (supply_share + SMOOTHING)` with `SMOOTHING = 0.01`.
4. `gap_score` = percentile rank (0–100, rounded int) of `ln(gap_ratio)` across **all district×category pairs in ranked districts**, so scores are comparable between districts (needed for "Highest gaps for tailoring: Galle 82, Matara 74"). Ordering inside a district uses gap_ratio.
5. `saturated = gap_ratio < 1` → reason text includes "many businesses already serve this; the market may be crowded".
6. **Coverage gate** — `per_10k = total_businesses / population * 10000`:
   - `adequate` if per_10k ≥ `COVERAGE_ADEQUATE = 5` and total_businesses ≥ `MIN_TOTAL_BUSINESSES = 150`
   - `low` if per_10k ≥ `COVERAGE_MIN = 3`
   - `insufficient` otherwise
   Only `adequate` districts are ranked. Thresholds are placeholders — tune once real numbers are in, then never change them silently.
7. **Cost pressure** (separate warning, never added to the score): for each price_input of the category, % change between the mean price of the last 14 days and the mean price 76–90 days earlier. If the mean change across inputs > `PRESSURE_THRESHOLD = 0.10` → warning "Input prices have risen about X% over the last three months, so margins may shrink." If prices are stale or missing → no warning, freshness shows it.
8. **User filters**: drop categories whose cost_min_lkr > budget; drop categories none of whose skills the user has; drop categories whose min_hours > user hours. If cost_max_lkr > budget, keep but flag `budget_fit = "lower_end"` ("Lower end fits your budget"), else `"fits"`.
9. Return the top 3 by gap_ratio. If fewer than 3 survive, return what's left plus a message. If zero, return a helpful empty state (suggest more skills/budget).

## Confidence and freshness
- Each source has an age. `STALE_AFTER_DAYS = 14` for OSM and prices (refreshing sources). HIES and population are fixed and always shown with their year.
- Confidence starts at `high`; HIES older than 5 years caps it at `medium`; each stale refreshing source lowers it one level; `supply_visibility = low` caps that card at `low`.
- If the district is not `adequate`, or both OSM and prices are stale and OSM is > 60 days old → refuse with reason.
- Every recommendation response includes a `freshness` block with each source's date/year and stale flag.

## Explanations
Template-based only (no LLM). Every number in a sentence must come from computed values passed in — never invent figures.
Example: "In Galle, clothing and tailoring businesses make up only about 4–5% of mapped businesses, while households spend about 11% of their budget in this category. That puts it among the strongest gaps in your area."
Always attach the disclaimer: "Demand indicator only. A gap can also exist for reasons the data cannot see, such as high rent or a business that closed there before."

## API
- `GET /health`
- `GET /districts` → name, coverage_flag, per_10k, total_businesses, population, is_pilot
- `GET /categories` → id, label, skills, cost range
- `GET /freshness` → sources with dates and stale flags
- `POST /recommend` body `{district, budget_lkr, skills[], hours}` → either `{status:"ok", district, profile, confidence, results[3], freshness, disclaimer}` or `{status:"insufficient_data", district, reason, per_10k, min_required, suggestions[neighbouring adequate districts], freshness}`
- `GET /gaps?category_id=` → per-district gap scores for one category (for the "highest gaps" list)
Validate inputs with pydantic (budget 25,000–300,000; known district; known skills; known hours bucket) and return 422 with clear messages.

## Frontend design (match the proposal mock-ups)
Light stone/off-white background (`bg-stone-100`), white rounded cards, dark green primary (`emerald-800`/`#1f5c45`), amber for warnings, monospace chips for data dates ("Spending · 2019", "Shops · 19 Oct").
Navbar: logo "Livelihood Lens" + links Find opportunities / About the data.
Pages: Profile (step 1 of 2) → Results (top 3 cards) or NoData (refusal). Results has "Print / save PDF" (window.print with print CSS).
Wording everywhere: "demand indicator", never "profit", "guaranteed", or "you will succeed". Must work on a phone-width screen.

## Hard rules
- Never commit `backend/data/raw/` or any HIES microdata. Only aggregated tables go to `processed/`.
- Keep raw files unchanged; every cleaning step lives in a script and logs what it dropped.
- All thresholds live in `config.py`.
- Write/extend pytest tests for every engine function. Run `pytest` before saying a task is done.
- After each task: summarise what changed, how to run it, and anything I must check by hand.

## Commands
- Backend: `cd backend && venv\Scripts\activate` (Windows) or `source venv/bin/activate`, then `uvicorn app.main:app --reload` → http://127.0.0.1:8000/docs
- Tests: `cd backend && pytest -q`
- Frontend: `cd frontend && npm run dev` → http://localhost:5173
