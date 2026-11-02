import os
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config
from app.data_loader import load_all
from app.routers import categories, districts, freshness, gaps, recommend
from app.schemas import HealthResponse


def allowed_origins():
    origins = [config.DEV_FRONTEND_ORIGIN]
    production_origin = os.environ.get("FRONTEND_ORIGIN")
    if production_origin:
        origins.append(production_origin)
    return origins


def readable_error(error):
    """Turns one pydantic error into {field, message} a person can read."""
    parts = [str(p) for p in error["loc"] if p not in ("body", "query")]
    field = parts[0] if parts else "request"
    kind = error["type"]
    if kind == "json_invalid":
        return {"field": "request", "message": "The request body is not valid JSON"}
    if kind == "missing":
        message = f"{field} is required"
    elif kind == "literal_error":
        message = f"{field} must be one of: {error['ctx']['expected']}"
    elif kind == "value_error":
        message = error["msg"].removeprefix("Value error, ")
    elif kind.startswith("int_"):
        message = f"{field} must be a whole number"
    elif kind.startswith("list_"):
        message = f"{field} must be a list"
    else:
        message = f"{field}: {error['msg']}"
    return {"field": field, "message": message}


async def validation_error_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": [readable_error(e) for e in exc.errors()]})


def create_app(load_store=load_all, today=date.today):
    """load_store and today are parameters so tests can use small tables and a fixed date."""

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = load_store()
        app.state.today = today
        yield

    app = FastAPI(title="Livelihood Lens API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    @app.get("/health", response_model=HealthResponse)
    def health():
        return {"status": "ok"}

    for module in (districts, categories, freshness, recommend, gaps):
        app.include_router(module.router)
    return app


app = create_app()
