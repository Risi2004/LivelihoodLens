from fastapi import APIRouter, HTTPException, Request

from app.engine.recommend import recommend as build_recommendation
from app.schemas import RecommendRequest, RecommendResponse

router = APIRouter()


@router.post("/recommend", response_model=RecommendResponse)
def post_recommend(body: RecommendRequest, request: Request):
    state = request.app.state
    try:
        return build_recommendation(
            state.store, body.district, body.budget_lkr, body.skills, body.hours, state.today()
        )
    except ValueError as error:
        # An official district with no row in the loaded data.
        raise HTTPException(422, detail=[{"field": "district", "message": str(error)}])
