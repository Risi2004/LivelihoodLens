from fastapi import APIRouter, Request

from app import config
from app.engine.scoring import coverage_table
from app.schemas import DistrictInfo

router = APIRouter()


@router.get("/districts", response_model=list[DistrictInfo])
def list_districts(request: Request):
    store = request.app.state.store
    coverage = coverage_table(store.district_totals, store.population)
    return [
        {
            "name": row["district"],
            "coverage_flag": row["coverage_flag"],
            "per_10k": round(row["per_10k"], 2),
            "total_businesses": row["total_businesses"],
            "population": row["population"],
            "is_pilot": row["district"] in config.PILOT_DISTRICTS,
        }
        for row in coverage.to_dict("records")
    ]
