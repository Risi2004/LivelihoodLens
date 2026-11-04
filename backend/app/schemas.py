"""Request and response models for the API."""
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator

from app import config

Skill = Literal["cooking", "sewing", "beauty", "electronics_repair", "tutoring", "handicrafts", "retail"]
Hours = Literal["under10", "10-20", "20-40", "40+"]
CoverageFlag = Literal["adequate", "low", "insufficient"]
Confidence = Literal["low", "medium", "high"]
BudgetFit = Literal["fits", "lower_end"]
FailedRule = Literal["per_10k", "total_businesses", "stale_data"]


class RecommendRequest(BaseModel):
    district: str
    budget_lkr: int
    skills: list[Skill]
    hours: Hours

    @field_validator("district")
    @classmethod
    def known_district(cls, value):
        if value not in config.DISTRICTS:
            raise ValueError(f"district must be one of the 25 official districts, not '{value}'")
        return value

    @field_validator("budget_lkr")
    @classmethod
    def budget_in_range(cls, value):
        if not config.BUDGET_MIN_LKR <= value <= config.BUDGET_MAX_LKR:
            raise ValueError(
                f"budget_lkr must be between {config.BUDGET_MIN_LKR:,} and {config.BUDGET_MAX_LKR:,}"
            )
        return value


class DatedSource(BaseModel):
    date: str | None
    age_days: int | None
    stale: bool


class HiesSource(BaseModel):
    year: int
    stale: bool
    over_age_limit: bool


class PopulationSource(BaseModel):
    year: int
    stale: bool


class Freshness(BaseModel):
    placeholder: bool
    osm: DatedSource
    prices: DatedSource
    hies: HiesSource
    population: PopulationSource


class Profile(BaseModel):
    budget_lkr: int
    skills: list[Skill]
    hours: Hours


class CostPressure(BaseModel):
    pct_change: float | None
    warning: bool
    items_used: list[str]
    stale: bool
    message: str | None


class ResultCard(BaseModel):
    category_id: str
    label: str
    gap_score: int
    cost_min_lkr: int
    cost_max_lkr: int
    budget_fit: BudgetFit
    budget_fit_label: str
    gap_ratio: float
    demand_share: float
    supply_share: float
    saturated: bool
    why: str
    cost_pressure: CostPressure
    confidence: Confidence


class OtherOption(BaseModel):
    category_id: str
    label: str
    gap_score: int
    cost_min_lkr: int
    cost_max_lkr: int
    budget_fit: BudgetFit
    budget_fit_label: str
    needs_skills: list[Skill]
    note: str


class RecommendOk(BaseModel):
    status: Literal["ok"]
    district: str
    profile: Profile
    confidence: Confidence | None  # None when no business type matched
    results: list[ResultCard]
    other_options: list[OtherOption]
    message: str | None
    freshness: Freshness
    disclaimer: str


class RecommendRefused(BaseModel):
    status: Literal["insufficient_data"]
    district: str
    reason: str
    per_10k: float
    failed_rule: FailedRule
    min_required: int | None
    suggestions: list[str]
    freshness: Freshness


RecommendResponse = Annotated[Union[RecommendOk, RecommendRefused], Field(discriminator="status")]


class HealthResponse(BaseModel):
    status: Literal["ok"]


class DistrictInfo(BaseModel):
    name: str
    coverage_flag: CoverageFlag
    per_10k: float
    total_businesses: int
    population: int
    is_pilot: bool


class CategoryInfo(BaseModel):
    id: str
    label: str
    skills: list[Skill]
    cost_min_lkr: int
    cost_max_lkr: int


class RankedGap(BaseModel):
    district: str
    gap_score: int
    gap_ratio: float


class NotRankedGap(BaseModel):
    district: str
    status: Literal["not ranked"]
    coverage_flag: CoverageFlag


class GapsResponse(BaseModel):
    category_id: str
    label: str
    ranked: list[RankedGap]
    not_ranked: list[NotRankedGap]
    freshness: Freshness
