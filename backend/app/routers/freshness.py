from fastapi import APIRouter, Request

from app.engine.confidence import source_freshness
from app.schemas import Freshness

router = APIRouter()


@router.get("/freshness", response_model=Freshness)
def get_freshness(request: Request):
    state = request.app.state
    return source_freshness(state.store.sources, state.today())
