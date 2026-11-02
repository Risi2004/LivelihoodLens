from fastapi import APIRouter, HTTPException, Request

from app.engine.confidence import data_too_stale, source_freshness
from app.engine.scoring import compute_gap_table, coverage_table
from app.schemas import GapsResponse

router = APIRouter()


@router.get("/gaps", response_model=GapsResponse)
def get_gaps(category_id: str, request: Request):
    state = request.app.state
    store = state.store
    categories = store.categories.set_index("category_id")
    if category_id not in categories.index:
        message = f"category_id must be one of: {', '.join(categories.index)}"
        raise HTTPException(422, detail=[{"field": "category_id", "message": message}])

    freshness = source_freshness(store.sources, state.today())
    coverage = coverage_table(store.district_totals, store.population)
    adequate = coverage.loc[coverage["coverage_flag"] == "adequate", "district"].tolist()
    ranked_districts = [] if data_too_stale(freshness) else adequate

    table = compute_gap_table(store.supply, store.demand, ranked_districts)
    rows = table[table["category_id"] == category_id].sort_values("gap_ratio", ascending=False)
    return {
        "category_id": category_id,
        "label": categories.loc[category_id, "label"],
        "ranked": rows[["district", "gap_score", "gap_ratio"]].to_dict("records"),
        "not_ranked": [
            {"district": row["district"], "status": "not ranked", "coverage_flag": row["coverage_flag"]}
            for row in coverage.to_dict("records")
            if row["district"] not in ranked_districts
        ],
        "freshness": freshness,
    }
