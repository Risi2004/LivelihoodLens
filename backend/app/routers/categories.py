from fastapi import APIRouter, Request

from app.schemas import CategoryInfo

router = APIRouter()


@router.get("/categories", response_model=list[CategoryInfo])
def list_categories(request: Request):
    store = request.app.state.store
    merged = store.categories.merge(store.startup_costs, on="category_id")
    return [
        {
            "id": row["category_id"],
            "label": row["label"],
            "skills": row["skills"].split("|"),
            "cost_min_lkr": row["cost_min_lkr"],
            "cost_max_lkr": row["cost_max_lkr"],
        }
        for row in merged.to_dict("records")
    ]
